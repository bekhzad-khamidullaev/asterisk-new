<?php
/** @var CView $this */
/** @var array $data */

$this->addJsFile('layout.mode.js');

$rows_html = '';
foreach ($data['users'] as $user) {
	$uid = (string) $user['userid'];
	$acl = $data['acl'][$uid] ?? ['can_ack1' => false, 'can_ack2' => false];
	$full_name = trim($user['name'].' '.$user['surname']);
	if ($full_name === '') {
		$full_name = '-';
	}

	$rows_html .= '<tr>'
		.'<td>'.htmlspecialchars($user['username']).'</td>'
		.'<td>'.htmlspecialchars($full_name).'</td>'
		.'<td style="text-align:center;"><input type="checkbox" name="acl['.$uid.'][ack1]" value="1"'.($acl['can_ack1'] ? ' checked' : '').'></td>'
		.'<td style="text-align:center;"><input type="checkbox" name="acl['.$uid.'][ack2]" value="1"'.($acl['can_ack2'] ? ' checked' : '').'></td>'
		.'</tr>';
}

$html = <<<HTML
<style>
.dispatch-acl-wrap { max-width: 1100px; margin: 0 auto; }
.dispatch-acl-card { background:#fff; border:1px solid #dbe4ef; border-radius:12px; padding:16px; }
.dispatch-acl-title { margin:0 0 12px; font-size:22px; font-weight:700; color:#20324a; }
.dispatch-acl-note { margin:0 0 14px; color:#5b6d86; }
.dispatch-acl-table { width:100%; border-collapse:collapse; }
.dispatch-acl-table th, .dispatch-acl-table td { border-bottom:1px solid #edf2f8; padding:10px; }
.dispatch-acl-table th { text-align:left; font-weight:700; background:#f8fbff; }
.dispatch-acl-actions { margin-top:14px; display:flex; gap:10px; }
.dispatch-acl-btn { border:1px solid #2d78c4; background:#2d78c4; color:#fff; border-radius:10px; padding:9px 14px; font-weight:600; cursor:pointer; }
.dispatch-acl-link { border:1px solid #d2deec; background:#fff; color:#2b3d57; border-radius:10px; padding:9px 14px; text-decoration:none; font-weight:600; }
</style>

<div class="dispatch-acl-wrap">
	<div class="dispatch-acl-card">
		<h2 class="dispatch-acl-title">Dispatch Access Control</h2>
		<p class="dispatch-acl-note">Grant button permissions per user. These rights are enforced server-side for Dispatcher 1/2 acknowledge.</p>
		<form method="post" action="zabbix.php?action=report.dispatch.acl">
			<table class="dispatch-acl-table">
				<thead>
					<tr>
						<th>Username</th>
						<th>Full name</th>
						<th>Dispatcher 1</th>
						<th>Dispatcher 2</th>
					</tr>
				</thead>
				<tbody>
					$rows_html
				</tbody>
			</table>
			<div class="dispatch-acl-actions">
				<button type="submit" class="dispatch-acl-btn">Save ACL</button>
				<a href="zabbix.php?action=problem.dispatch.view" class="dispatch-acl-link">Back to Dispatch</a>
			</div>
		</form>
	</div>
</div>
HTML;

$html_page = (new CHtmlPage())
	->setTitle(_('Dispatch ACL'))
	->setWebLayoutMode($this->getLayoutMode())
	// Render as raw HTML block, otherwise CHtmlPage escapes string content.
	->addItem(new CJsScript($html));

$html_page->show();
