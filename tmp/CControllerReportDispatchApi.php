<?php declare(strict_types = 0);

class CControllerReportDispatchApi extends CController {
	private const DISP1_MARK = '[DISP1_ACK]';
	private const DISP2_MARK = '[DISP2_ACK]';
	private const RCA_MARK = '[RCA]';
	private const DISPATCHER_USERGROUPS = ['Роль диспетчера', 'Dispatcher 1', 'Dispatcher 2'];

	protected function init(): void {
		$this->disableCsrfValidation();
	}

	protected function checkInput(): bool {
		$fields = [
			'eventid' => 'int32',
			'eventids' => 'string',
			'op' => 'in ack1,ack2,rca',
			'rca_text' => 'string',
			'with_history' => 'int32',
			'with_comments' => 'int32'
		];

		return $this->validateInput($fields);
	}

	protected function checkPermissions(): bool {
		return CWebUser::isLoggedIn() && CWebUser::checkAccess(CRoleHelper::UI_MONITORING_PROBLEMS);
	}

	private function jsonMain(array $payload): void {
		$this->setResponse(new CControllerResponseData([
			'main_block' => json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES)
		]));
	}

	private function getSystemPermissions(): array {
		return [
			// Делать кнопки доступными всем залогиненным пользователям; контроль прав переносим на аудит.
			'can_ack1' => true,
			'can_ack2' => true,
			'can_comment' => true
		];
	}

	private function buildUserDisplayMap(array $userids): array {
		$userids = array_values(array_unique(array_filter(array_map('strval', $userids), static function($id) {
			return $id !== '' && $id !== '0';
		})));

		if (!$userids) {
			return [];
		}

		$users = API::User()->get([
			'output' => ['userid', 'username', 'name', 'surname'],
			'userids' => $userids,
			'preservekeys' => true
		]);

		$result = [];
		foreach ($users as $user) {
			$fullname = trim((string) ($user['name'] ?? '').' '.(string) ($user['surname'] ?? ''));
			$result[(string) $user['userid']] = ($fullname !== '')
				? $fullname
				: (string) ($user['username'] ?? ('user#'.$user['userid']));
		}

		return $result;
	}

	private function buildDispatchHistory(int $eventid, bool $with_history = true): array {
		$result = [
			'd1' => false,
			'd2' => false,
			'has_rca' => false,
			'rca_text' => '',
			'rca_time' => '',
			'rca_author' => '',
			'comment_history' => []
		];

		$events = API::Event()->get([
			'output' => ['eventid'],
			'eventids' => [$eventid],
			'source' => EVENT_SOURCE_TRIGGERS,
			'object' => EVENT_OBJECT_TRIGGER,
			'selectAcknowledges' => ['acknowledgeid', 'userid', 'clock', 'message', 'action'],
			'preservekeys' => true
		]);

		if (!$events) {
			return $result;
		}

		$event = reset($events);
		$acks = $event['acknowledges'] ?? [];
		if (!$acks) {
			return $result;
		}

		usort($acks, static function(array $a, array $b): int {
			return ((int) ($b['clock'] ?? 0)) <=> ((int) ($a['clock'] ?? 0));
		});

		$user_map = $this->buildUserDisplayMap(array_column($acks, 'userid'));
		$history = [];
		$latest_free_comment = [
			'text' => '',
			'clock' => '',
			'author' => ''
		];

		foreach ($acks as $ack) {
			$message = trim((string) ($ack['message'] ?? ''));
			$clock = (int) ($ack['clock'] ?? 0);
			$userid = (string) ($ack['userid'] ?? '');
			$user = $user_map[$userid] ?? ($userid !== '' ? ('user#'.$userid) : 'System');
			$action = 'Comment';
			$is_disp1 = (strpos($message, self::DISP1_MARK) !== false);
			$is_disp2 = (strpos($message, self::DISP2_MARK) !== false);
			$is_rca = (strpos($message, self::RCA_MARK) !== false);

			if ($is_disp1) {
				$result['d1'] = true;
				$action = 'Dispatcher 1';
			}
			if ($is_disp2) {
				$result['d2'] = true;
				$action = 'Dispatcher 2';
			}
			if ($is_rca) {
				$result['has_rca'] = true;
				$action = 'RCA';
				$rca_text = trim(str_replace(self::RCA_MARK, '', $message));
				if ($rca_text !== '') {
					$result['rca_text'] = $rca_text;
					$result['rca_time'] = (string) $clock;
					$result['rca_author'] = $user;
				}
			}
			elseif (!$is_disp1 && !$is_disp2 && $message !== '' && $latest_free_comment['text'] === '') {
				$latest_free_comment = [
					'text' => $message,
					'clock' => (string) $clock,
					'author' => $user
				];
			}

			if ($with_history && $message !== '') {
				$history[] = [
					'id' => (string) ($ack['acknowledgeid'] ?? ''),
					'user' => $user,
					'clock' => (string) $clock,
					'action' => $action,
					'comment' => $message
				];
			}
		}

		if ($with_history) {
			usort($history, static function(array $a, array $b): int {
				return ((int) $b['clock']) <=> ((int) $a['clock']);
			});
			$result['comment_history'] = $history;
		}

		// SSOT fallback: if no explicit [RCA], use latest plain comment as RCA reason.
		if (!$result['has_rca'] && $latest_free_comment['text'] !== '') {
			$result['has_rca'] = true;
			$result['rca_text'] = $latest_free_comment['text'];
			$result['rca_time'] = $latest_free_comment['clock'];
			$result['rca_author'] = $latest_free_comment['author'];
		}

		return $result;
	}

	private function parseEventidsCsv(string $raw): array {
		$ids = [];
		foreach (explode(',', $raw) as $part) {
			$part = trim($part);
			if ($part === '' || !ctype_digit($part)) {
				continue;
			}
			$id = (int) $part;
			if ($id > 0) {
				$ids[$id] = $id;
			}
		}

		$ids = array_values($ids);
		if (count($ids) > 500) {
			$ids = array_slice($ids, 0, 500);
		}

		return $ids;
	}

	private function getStatesBatch(array $eventids, array $permissions): array {
		$states = [];
		if (!$eventids) {
			return [
				'ok' => true,
				'states' => []
			];
		}

		$events = API::Event()->get([
			'output' => ['eventid', 'name', 'r_eventid'],
			'eventids' => $eventids,
			'source' => EVENT_SOURCE_TRIGGERS,
			'object' => EVENT_OBJECT_TRIGGER,
			'selectAcknowledges' => ['clock', 'message'],
			'preservekeys' => true
		]);

		if (!$events) {
			return [
				'ok' => true,
				'states' => []
			];
		}

		foreach ($events as $event) {
			$eventid = (int) ($event['eventid'] ?? 0);
			if ($eventid <= 0) {
				continue;
			}

			$d1 = false;
			$d2 = false;
			$has_rca = false;

			foreach ($event['acknowledges'] ?? [] as $ack) {
				$message = trim((string) ($ack['message'] ?? ''));
				if ($message === '') {
					continue;
				}
				$is_disp1 = (strpos($message, self::DISP1_MARK) !== false);
				$is_disp2 = (strpos($message, self::DISP2_MARK) !== false);
				$is_rca = (strpos($message, self::RCA_MARK) !== false);

				if ($is_disp1) {
					$d1 = true;
				}
				if ($is_disp2) {
					$d2 = true;
				}
				if ($is_rca) {
					$has_rca = true;
				}
				// SSOT fallback: any non-dispatch comment counts as RCA reason.
				if (!$is_disp1 && !$is_disp2) {
					$has_rca = true;
				}
			}

			$recovered = ((int) ($event['r_eventid'] ?? 0) > 0);
			$lock_reason_ack1 = $d1
				? 'Dispatcher 1 already confirmed'
				: (!$permissions['can_ack1'] ? 'Недостаточно системных прав Zabbix: Actions -> Acknowledge problems' : '');
			$lock_reason_ack2 = $d2
				? 'Dispatcher 2 already confirmed'
				: (!$permissions['can_ack2'] ? 'Недостаточно системных прав Zabbix: Actions -> Acknowledge problems' : '');

			$states[(string) $eventid] = [
				'ok' => true,
				'eventid' => $eventid,
				'name' => (string) ($event['name'] ?? ''),
				'd1' => $d1,
				'd2' => $d2,
				'has_rca' => $has_rca,
				'recovered' => $recovered,
				'can_ack1' => !$d1 && $permissions['can_ack1'],
				'can_ack2' => !$d2 && $permissions['can_ack2'],
				'dispatch_group_1' => 'Dispatcher 1 (Acknowledge problems)',
				'dispatch_group_2' => 'Dispatcher 2 (Acknowledge problems)',
				'lock_reason_ack1' => $lock_reason_ack1,
				'lock_reason_ack2' => $lock_reason_ack2,
				'comment_history' => [],
				'rca_text' => '',
				'rca_time' => '',
				'rca_author' => ''
			];
		}

		return [
			'ok' => true,
			'states' => $states
		];
	}

	private function getState(int $eventid, array $permissions, bool $with_history = true): array {
		$event = API::Event()->get([
			'output' => ['eventid', 'name', 'r_eventid'],
			'eventids' => [$eventid],
			'source' => EVENT_SOURCE_TRIGGERS,
			'object' => EVENT_OBJECT_TRIGGER,
			'preservekeys' => true
		]);

		if (!$event) {
			return ['ok' => false, 'error' => 'Event not found or access denied'];
		}

		$event_row = reset($event);
		$name = (string) ($event_row['name'] ?? '');
		$recovered = ((int) ($event_row['r_eventid'] ?? 0) > 0);

		$history_data = $this->buildDispatchHistory($eventid, $with_history);

		$lock_reason_ack1 = '';
		if ($history_data['d1']) {
			$lock_reason_ack1 = 'Dispatcher 1 already confirmed';
		}
		elseif (!$permissions['can_ack1']) {
			$lock_reason_ack1 = 'Недостаточно системных прав Zabbix: Actions -> Acknowledge problems';
		}

		$lock_reason_ack2 = '';
		if ($history_data['d2']) {
			$lock_reason_ack2 = 'Dispatcher 2 already confirmed';
		}
		elseif (!$permissions['can_ack2']) {
			$lock_reason_ack2 = 'Недостаточно системных прав Zabbix: Actions -> Acknowledge problems';
		}

		return [
			'ok' => true,
			'eventid' => $eventid,
			'name' => $name,
			'd1' => $history_data['d1'],
			'd2' => $history_data['d2'],
			'has_rca' => $history_data['has_rca'],
			'recovered' => $recovered,
			'can_ack1' => !$history_data['d1'] && $permissions['can_ack1'],
			'can_ack2' => !$history_data['d2'] && $permissions['can_ack2'],
			'dispatch_group_1' => 'Dispatcher 1 (Acknowledge problems)',
			'dispatch_group_2' => 'Dispatcher 2 (Acknowledge problems)',
			'lock_reason_ack1' => $lock_reason_ack1,
			'lock_reason_ack2' => $lock_reason_ack2,
			'comment_history' => $history_data['comment_history'],
			'rca_text' => $history_data['rca_text'],
			'rca_time' => $history_data['rca_time'],
			'rca_author' => $history_data['rca_author']
		];
	}

	protected function doAction(): void {
		$eventid = (int) $this->getInput('eventid');
		$eventids_csv = (string) $this->getInput('eventids', '');
		$op = (string) $this->getInput('op', '');
		$permissions = $this->getSystemPermissions();

		if ($_SERVER['REQUEST_METHOD'] === 'GET' || $op === '') {
			if ($eventids_csv !== '') {
				$eventids = $this->parseEventidsCsv($eventids_csv);
				if (!$eventids) {
					$this->jsonMain(['ok' => false, 'error' => 'Invalid eventids']);
					return;
				}
				$this->jsonMain($this->getStatesBatch($eventids, $permissions));
				return;
			}

			if ($eventid <= 0) {
				$this->jsonMain(['ok' => false, 'error' => 'Invalid eventid']);
				return;
			}

			$with_history = (string) ($this->getInput('with_history', $this->getInput('with_comments', 1))) !== '0';
			$this->jsonMain($this->getState($eventid, $permissions, $with_history));
			return;
		}

		if ($eventid <= 0) {
			$this->jsonMain(['ok' => false, 'error' => 'Invalid eventid']);
			return;
		}

		if (!in_array($op, ['ack1', 'ack2', 'rca'], true)) {
			$this->jsonMain(['ok' => false, 'error' => 'Invalid action']);
			return;
		}

		$state_before = $this->getState($eventid, $permissions, false);
		if (!$state_before['ok']) {
			$this->jsonMain($state_before);
			return;
		}

		$username = CWebUser::$data['username'] ?? 'unknown';
		$now = date('Y-m-d H:i:s');

		if ($op === 'ack1' || $op === 'ack2') {
			if (($op === 'ack1' && !$permissions['can_ack1']) || ($op === 'ack2' && !$permissions['can_ack2'])) {
				$this->jsonMain([
					'ok' => false,
					'error' => 'Недостаточно системных прав Zabbix: Actions -> Acknowledge problems'
				]);
				return;
			}

			if ($op === 'ack1' && $state_before['d1']) {
				$this->jsonMain(['ok' => false, 'error' => 'Dispatcher 1 already confirmed']);
				return;
			}
			if ($op === 'ack2' && $state_before['d2']) {
				$this->jsonMain(['ok' => false, 'error' => 'Dispatcher 2 already confirmed']);
				return;
			}

			$mark = ($op === 'ack1') ? self::DISP1_MARK : self::DISP2_MARK;
			$label = ($op === 'ack1') ? 'Dispatcher 1' : 'Dispatcher 2';
			$res = API::Event()->acknowledge([
				'eventids' => [$eventid],
				'action' => ZBX_PROBLEM_UPDATE_ACKNOWLEDGE | ZBX_PROBLEM_UPDATE_MESSAGE,
				'message' => $mark.' '.$label.' confirmed by '.$username.' at '.$now
			]);

			$this->jsonMain($res
				? $this->getState($eventid, $permissions, true)
				: ['ok' => false, 'error' => 'Acknowledge failed']
			);
			return;
		}

		$rca = trim((string) $this->getInput('rca_text', ''));
		if (!$permissions['can_comment']) {
			$this->jsonMain([
				'ok' => false,
				'error' => 'Недостаточно системных прав Zabbix: Actions -> Add problem comments'
			]);
			return;
		}
		if ($state_before['recovered'] && mb_strlen($rca) < 10) {
			$this->jsonMain(['ok' => false, 'error' => 'RCA is required for recovered incident (min 10 chars)']);
			return;
		}
		if ($rca === '') {
			$this->jsonMain(['ok' => false, 'error' => 'RCA text is empty']);
			return;
		}

		$res = API::Event()->acknowledge([
			'eventids' => [$eventid],
			'action' => ZBX_PROBLEM_UPDATE_MESSAGE,
			'message' => self::RCA_MARK.' '.$rca.' (by '.$username.' at '.$now.')'
		]);

		$this->jsonMain($res
			? $this->getState($eventid, $permissions, true)
			: ['ok' => false, 'error' => 'RCA save failed']
		);
	}
}
