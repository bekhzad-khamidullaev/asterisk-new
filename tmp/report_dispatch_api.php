<?php
declare(strict_types = 0);

require_once dirname(__FILE__).'/include/config.inc.php';

header('Content-Type: application/json; charset=UTF-8');

const DISP1_MARK = '[DISP1_ACK]';
const DISP2_MARK = '[DISP2_ACK]';
const RCA_MARK = '[RCA]';
const DISP1_ROLE_LABEL = 'Dispatcher 1';
const DISP2_ROLE_LABEL = 'Dispatcher 2';

function json_out(array $payload, int $code = 200): void {
	http_response_code($code);
	echo json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
	exit;
}

function build_user_display_map(array $userids): array {
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

function build_dispatch_history(int $eventid, bool $with_history = true): array {
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

	$user_map = build_user_display_map(array_column($acks, 'userid'));
	$history = [];
	foreach ($acks as $ack) {
		$message = trim((string) ($ack['message'] ?? ''));
		$clock = (int) ($ack['clock'] ?? 0);
		$userid = (string) ($ack['userid'] ?? '');
		$user = $user_map[$userid] ?? ($userid !== '' ? ('user#'.$userid) : 'System');
		$action = 'Comment';

		if (strpos($message, DISP1_MARK) !== false) {
			$result['d1'] = true;
			$action = 'Dispatcher 1';
		}
		if (strpos($message, DISP2_MARK) !== false) {
			$result['d2'] = true;
			$action = 'Dispatcher 2';
		}
		if (strpos($message, RCA_MARK) !== false) {
			$result['has_rca'] = true;
			$action = 'RCA';
			$rca_text = trim(str_replace(RCA_MARK, '', $message));
			if ($rca_text !== '') {
				$result['rca_text'] = $rca_text;
				$result['rca_time'] = (string) $clock;
				$result['rca_author'] = $user;
			}
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

	return $result;
}

function get_state(int $eventid, array $permissions, bool $with_history = true): array {
	$recovered = false;
	$name = '';

	$event = API::Event()->get([
		'output' => ['eventid', 'name'],
		'eventids' => [$eventid],
		'source' => EVENT_SOURCE_TRIGGERS,
		'object' => EVENT_OBJECT_TRIGGER,
		'preservekeys' => true
	]);

	if (!$event) {
		return ['ok' => false, 'error' => 'Event not found or access denied'];
	}

	$name = reset($event)['name'];

	$p = DBfetch(DBselect('SELECT r_eventid FROM problem WHERE eventid='.zbx_dbstr($eventid)));
	if ($p && (int) $p['r_eventid'] > 0) {
		$recovered = true;
	}

	$history_data = build_dispatch_history($eventid, $with_history);

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
		'dispatch_group_1' => DISP1_ROLE_LABEL.' (Acknowledge problems)',
		'dispatch_group_2' => DISP2_ROLE_LABEL.' (Acknowledge problems)',
		'lock_reason_ack1' => $lock_reason_ack1,
		'lock_reason_ack2' => $lock_reason_ack2,
		'comment_history' => $history_data['comment_history'],
		'rca_text' => $history_data['rca_text'],
		'rca_time' => $history_data['rca_time'],
		'rca_author' => $history_data['rca_author']
	];
}

function get_dispatch_permissions(): array {
	$can_acknowledge = CWebUser::checkAccess(CRoleHelper::ACTIONS_ACKNOWLEDGE_PROBLEMS);
	$can_comment = CWebUser::checkAccess(CRoleHelper::ACTIONS_ADD_PROBLEM_COMMENTS);

	return [
		'can_ack1' => $can_acknowledge,
		'can_ack2' => $can_acknowledge,
		'can_comment' => $can_comment
	];
}

if (!CWebUser::isLoggedIn() || !CWebUser::checkAccess(CRoleHelper::UI_MONITORING_PROBLEMS)) {
	json_out(['ok' => false, 'error' => 'Access denied'], 403);
}

$eventid = (int) ($_REQUEST['eventid'] ?? 0);
if ($eventid <= 0) {
	json_out(['ok' => false, 'error' => 'Invalid eventid'], 400);
}

$permissions = get_dispatch_permissions();

if ($_SERVER['REQUEST_METHOD'] === 'GET') {
	$with_history = (string) ($_REQUEST['with_history'] ?? $_REQUEST['with_comments'] ?? '1') !== '0';
	$state = get_state($eventid, $permissions, $with_history);
	json_out($state);
}

$action = (string) ($_POST['op'] ?? '');
$username = CWebUser::$data['username'] ?? 'unknown';
$now = date('Y-m-d H:i:s');

if (!in_array($action, ['ack1', 'ack2', 'rca'], true)) {
	json_out(['ok' => false, 'error' => 'Invalid action'], 400);
}

$state_before = get_state($eventid, $permissions, false);
if (!$state_before['ok']) {
	json_out($state_before, 400);
}

if ($action === 'ack1' || $action === 'ack2') {
	if ($action === 'ack1' && !$permissions['can_ack1']) {
		json_out(['ok' => false, 'error' => 'Недостаточно системных прав Zabbix: Actions -> Acknowledge problems'], 403);
	}

	if ($action === 'ack2' && !$permissions['can_ack2']) {
		json_out(['ok' => false, 'error' => 'Недостаточно системных прав Zabbix: Actions -> Acknowledge problems'], 403);
	}
	if ($action === 'ack1' && $state_before['d1']) {
		json_out(['ok' => false, 'error' => 'Dispatcher 1 already confirmed'], 400);
	}

	if ($action === 'ack2' && $state_before['d2']) {
		json_out(['ok' => false, 'error' => 'Dispatcher 2 already confirmed'], 400);
	}

	$mark = ($action === 'ack1') ? DISP1_MARK : DISP2_MARK;
	$label = ($action === 'ack1') ? 'Dispatcher 1' : 'Dispatcher 2';
	$res = API::Event()->acknowledge([
		'eventids' => [$eventid],
		'action' => ZBX_PROBLEM_UPDATE_ACKNOWLEDGE | ZBX_PROBLEM_UPDATE_MESSAGE,
		'message' => $mark.' '.$label.' confirmed by '.$username.' at '.$now
	]);

	if (!$res) {
		json_out(['ok' => false, 'error' => 'Acknowledge failed'], 500);
	}

	json_out(get_state($eventid, $permissions, true));
}

$rca = trim((string) ($_POST['rca_text'] ?? ''));
if (!$permissions['can_comment']) {
	json_out(['ok' => false, 'error' => 'Недостаточно системных прав Zabbix: Actions -> Add problem comments'], 403);
}
if ($state_before['recovered'] && mb_strlen($rca) < 10) {
	json_out(['ok' => false, 'error' => 'RCA is required for recovered incident (min 10 chars)'], 400);
}

if ($rca === '') {
	json_out(['ok' => false, 'error' => 'RCA text is empty'], 400);
}

$res = API::Event()->acknowledge([
	'eventids' => [$eventid],
	'action' => ZBX_PROBLEM_UPDATE_MESSAGE,
	'message' => RCA_MARK.' '.$rca.' (by '.$username.' at '.$now.')'
]);

if (!$res) {
	json_out(['ok' => false, 'error' => 'RCA save failed'], 500);
}

json_out(get_state($eventid, $permissions, true));
