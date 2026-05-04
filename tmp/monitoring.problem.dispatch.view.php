<?php
/** @var CView $this */
/** @var array $data */

if ($data['action'] === 'problem.dispatch.view') {
	$is_embedded = (string) getRequest('embedded', '0') === '1';

	if (!$is_embedded) {
		$this->addJsFile('common.js');
		$this->addJsFile('layout.mode.js');
		$this->addJsFile('items.js');
		$this->addJsFile('multilineinput.js');
		$this->enableLayoutModes();
	}

	// Keep dispatch page in standard layout for direct open (no forced kiosk/fullscreen).
	$web_layout_mode = ZBX_LAYOUT_NORMAL;

	if ($data['uncheck']) {
		uncheckTableRows('problem');
	}

	$topbar_overview = (new CDiv())
		->addClass('dc-topbar')
		->addItem((new CTag('span', true, _('Visible').': '))->addClass('dc-kpi')
			->addItem((new CSpan('0'))->setId('dc-kpi-total')))
		->addItem((new CTag('span', true, _('Recovered').': '))->addClass('dc-kpi dc-kpi-good')
			->addItem((new CSpan('0'))->setId('dc-kpi-recovered')))
		->addItem((new CTag('span', true, _('Active').': '))->addClass('dc-kpi')
			->addItem((new CSpan('0'))->setId('dc-kpi-open')))
		->addItem((new CTag('span', true, _('RCA debt').': '))->addClass('dc-kpi dc-kpi-warn')
			->addItem((new CSpan('0'))->setId('dc-kpi-debt')))
		->addItem((new CSpan(_('Waiting for initial scan...')))->setId('dc-kpi-meta')->addClass('dc-kpi-meta'));

	$screen_data = array_intersect_key($data, array_flip(['page', 'action', 'sort', 'sortorder', 'filter', 'tabfilter_idx']));
	$screen_data['action'] = 'problem.view';

	$page_style_css = <<<'CSS'
.dc-topbar {
	display: inline-flex;
	align-items: center;
	gap: 8px;
	margin-left: 6px;
}
.dc-kpi {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	padding: 2px 8px;
	border: 1px solid #c4cdd6;
	border-radius: 3px;
	background: #f4f6f8;
	color: #596270;
	font-size: 11px;
	white-space: nowrap;
}
.dc-kpi > span {
	font-weight: 700;
	font-size: 12px;
	color: #2e3642;
}
.dc-kpi-good > span { color: #1a6f32; }
.dc-kpi-warn > span { color: #b45309; }
.dc-kpi-meta {
	font-size: 11px;
	color: #6f7885;
	white-space: nowrap;
}
@media (max-width: 1100px) {
	.dc-topbar { display: none; }
}
CSS;

	if ($is_embedded) {
		echo (new CPartial('monitoring.problem.view.html', $screen_data))->getOutput();
	}
	else {
		$controls = (new CList())
			->addItem((new CLink(_('Open classic Problems'),
				(new CUrl('zabbix.php'))->setArgument('action', 'problem.view')
			))->addClass(ZBX_STYLE_BTN_LINK))
			->addItem($topbar_overview);

		(new CHtmlPage())
			->setTitle(_('Problems: Dispatch center'))
			->setWebLayoutMode($web_layout_mode)
			->setControls((new CTag('nav', true, $controls))->setAttribute('aria-label', _('Content controls')))
			->addItem(new CTag('style', true, $page_style_css))
			->addItem(new CPartial('monitoring.problem.view.html', $screen_data))
			->show();
	}

	$init = <<<'JS'
(function() {
	const apiUrl = 'zabbix.php?action=report.dispatch.api';
	const ACTIVE_SCAN_MS = 4000;
	const HIDDEN_SCAN_MS = 15000;
	const REQUEST_TIMEOUT_MS = 4000;

	const modalTemplate = `
<style id="dc-style">
#dc-modal {
	display: none;
	position: fixed;
	top: 0;
	left: 0;
	width: 100vw;
	height: 100vh;
	padding: 16px;
	box-sizing: border-box;
	background: rgba(0, 0, 0, 0.38);
	z-index: 9999;
	align-items: center;
	justify-content: center;
}
#dc-modal.dc-open { display: flex; }
.dc-modal-card {
	width: min(980px, 98vw);
	max-height: 94vh;
	overflow: auto;
	background: #f4f6f8;
	border: 1px solid #bcc3ca;
	border-radius: 4px;
	box-shadow: 0 8px 24px rgba(0, 0, 0, 0.32);
	color: #2b313a;
}
.dc-modal-head {
	position: sticky;
	top: 0;
	z-index: 5;
	padding: 12px 16px;
	border-bottom: 1px solid #d6dbe0;
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 10px;
	background: #e9edf2;
}
.dc-modal-head h3 {
	margin: 0;
	font-size: 18px;
	line-height: 1.2;
	font-weight: 700;
	color: #2b313a;
}
.dc-modal-sub { margin-top: 4px; font-size: 12px; color: #59626f; }
.dc-close {
	border: 1px solid #9ea7b3;
	background: #fff;
	border-radius: 3px;
	padding: 6px 10px;
	cursor: pointer;
	font-weight: 600;
	color: #2b313a;
}
.dc-close:hover { background: #f0f3f6; }
.dc-modal-body { padding: 14px 16px 16px; }
.dc-banner {
	display: none;
	padding: 8px 10px;
	border-radius: 3px;
	margin-bottom: 10px;
	font-size: 12px;
	font-weight: 600;
	border: 1px solid transparent;
}
.dc-banner.dc-info { display: block; color: #0f4c5c; background: #e6f6ff; border-color: #9dd8f7; }
.dc-banner.dc-success { display: block; color: #14532d; background: #edf8ef; border-color: #9bd3a6; }
.dc-banner.dc-error { display: block; color: #7f1d1d; background: #fdeeee; border-color: #f2bcbc; }
.dc-event { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-bottom: 12px; }
.dc-event-title { font-size: 14px; font-weight: 700; color: #2b313a; }
.dc-chip {
	border-radius: 10px;
	padding: 2px 8px;
	font-size: 10px;
	font-weight: 700;
	letter-spacing: .02em;
	border: 1px solid transparent;
	text-transform: uppercase;
}
.dc-chip-problem { background: #fce8e6; color: #b71c1c; border-color: #e7b6b1; }
.dc-chip-resolved { background: #e5f4e8; color: #2e7d32; border-color: #b5d7ba; }
.dc-grid { display: grid; grid-template-columns: repeat(2, minmax(250px, 1fr)); gap: 10px; margin-bottom: 12px; }
.dc-role { border: 1px solid #d4dbe3; border-radius: 3px; padding: 10px; background: #fff; }
.dc-role-title {
	margin: 0 0 4px;
	font-size: 11px;
	text-transform: uppercase;
	letter-spacing: .03em;
	color: #6a7380;
	font-weight: 700;
}
.dc-role-name { margin: 0 0 8px; font-size: 13px; font-weight: 700; color: #2b313a; }
.dc-btn {
	border-radius: 3px;
	padding: 7px 11px;
	font-weight: 700;
	cursor: pointer;
	border: 1px solid transparent;
	font-size: 13px;
}
.dc-btn-secondary { background: #fff; border-color: #aab4c0; color: #2f3742; }
.dc-btn-primary { background: #1976d2; border-color: #115293; color: #fff; min-width: 130px; }
.dc-btn:disabled { opacity: .55; cursor: not-allowed; }
.dc-ack {
	width: 100%;
	min-height: 40px;
	border-radius: 3px;
	padding: 8px 10px;
	border: 1px solid #acb5c0;
	background: #d2d7de;
	color: #3a4350;
	font-weight: 700;
	cursor: pointer;
}
.dc-ack:hover { filter: brightness(.98); }
.dc-ack-gray { background: #d2d7de; border-color: #aeb7c3; color: #3a4350; }
.dc-ack-green { background: #2e7d32; border-color: #256628; color: #fff; }
.dc-ack-blue { background: #1976d2; border-color: #115293; color: #fff; }
.dc-ack-green:disabled {
\tbackground: #2e7d32 !important;
\tborder-color: #256628 !important;
\tcolor: #ffffff !important;
\topacity: 1 !important;
}
.dc-ack-blue:disabled {
\tbackground: #1976d2 !important;
\tborder-color: #115293 !important;
\tcolor: #ffffff !important;
\topacity: 1 !important;
}
.dc-ack-locked { background: #e2e6eb; border-color: #c6ced8; color: #5f6977; cursor: not-allowed; }
.dc-ack-status { margin-top: 6px; font-size: 11px; color: #66707f; min-height: 15px; }
.dc-section-title { margin: 0 0 6px; font-size: 13px; font-weight: 700; color: #2b313a; }
.dc-history { margin: 0 0 12px; border: 1px solid #d4dbe3; border-radius: 3px; background: #fff; }
.dc-history-list { list-style: none; margin: 0; padding: 0; max-height: 170px; overflow: auto; }
.dc-history-item { padding: 8px 10px; border-top: 1px solid #eceff3; }
.dc-history-item:first-child { border-top: 0; }
.dc-history-meta { display: flex; flex-wrap: wrap; gap: 8px; font-size: 11px; color: #6a7380; margin-bottom: 4px; }
.dc-history-user { font-weight: 700; color: #404a57; }
.dc-history-text { font-size: 12px; color: #2b313a; white-space: pre-wrap; word-break: break-word; }
.dc-history-empty { padding: 10px; font-size: 12px; color: #7b8592; border-top: 1px solid #eceff3; }
.dc-rca-label { margin: 0 0 4px; font-size: 13px; font-weight: 700; color: #2b313a; }
.dc-rca-help { margin: 0 0 6px; font-size: 12px; color: #6a7380; }
.dc-rca {
	width: 100%;
	min-height: 120px;
	resize: vertical;
	box-sizing: border-box;
	border: 1px solid #b7c0ca;
	border-radius: 3px;
	padding: 8px 10px;
	font-size: 13px;
	line-height: 1.4;
	color: #2b313a;
	background: #fff;
}
.dc-rca:focus { outline: none; border-color: #1976d2; box-shadow: 0 0 0 2px rgba(25, 118, 210, .14); }
.dc-foot { margin-top: 10px; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px; padding-top: 2px; }
.dc-note { font-size: 12px; font-weight: 600; color: #59626f; }
.dc-btns { display: flex; gap: 6px; }
.dc-inline { display: flex; flex-direction: column; gap: 6px; width: 100%; }
.dc-inline-top { display: flex; gap: 8px; width: 100%; }
.dc-inline-bottom { display: flex; gap: 8px; width: 100%; align-items: center; }
.dc-inline-btn {
	flex: 1 1 0;
	min-width: 0;
	border-radius: 8px;
	border: 1px solid #cbd5e1;
	background: #e5e7eb;
	color: #374151;
	font-size: 12px;
	font-weight: 800;
	padding: 6px 8px;
	cursor: pointer;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
.dc-inline-btn-green { background: #16a34a; border-color: #15803d; color: #fff; }
.dc-inline-btn-blue { background: #2563eb; border-color: #1d4ed8; color: #fff; }
.dc-inline-btn-green:disabled {
\tbackground: #16a34a !important;
\tborder-color: #15803d !important;
\tcolor: #ffffff !important;
\topacity: 1 !important;
}
.dc-inline-btn-blue:disabled {
\tbackground: #2563eb !important;
\tborder-color: #1d4ed8 !important;
\tcolor: #ffffff !important;
\topacity: 1 !important;
}
.dc-inline-btn-locked { background: #e5e7eb; color: #9ca3af; border-color: #d1d5db; cursor: not-allowed; }
.dc-inline-rca {
	flex: 1 1 auto;
	min-width: 0;
	border: 1px solid #cbd5e1;
	border-radius: 8px;
	padding: 6px 9px;
	font-size: 12px;
	background: #fff;
}
.dc-inline-save {
	flex: 0 0 88px;
	border: 1px solid #cbd5e1;
	border-radius: 8px;
	background: #f8fafc;
	color: #1e3a5f;
	padding: 6px 8px;
	font-size: 12px;
	font-weight: 800;
	cursor: pointer;
	white-space: nowrap;
}
.dc-inline-save:hover { background: #eef4fb; }
.dc-inline-msg {
	font-size: 11px;
	color: #64748b;
	margin-top: 2px;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
.dc-inline-msg-error { color: #b91c1c; }
.dc-inline-msg-success { color: #166534; }
.dc-row-rca-required {
	box-shadow: inset 4px 0 0 #ef4444;
	background: #fff7f7 !important;
}
.dc-rca-badge {
	display: inline-block;
	margin-left: 8px;
	padding: 2px 7px;
	border-radius: 999px;
	background: #fee2e2;
	color: #991b1b;
	border: 1px solid #fca5a5;
	font-size: 11px;
	font-weight: 800;
	letter-spacing: .02em;
	text-transform: uppercase;
}
.dc-status-problem { color: #d40000 !important; font-weight: 700; }
.dc-status-resolved { color: #1f9d3a !important; font-weight: 700; }
@media (max-width: 840px) {
	.dc-grid { grid-template-columns: 1fr; }
	.dc-head { align-items: center; }
	.dc-btns { width: 100%; }
	.dc-btn { flex: 1; }
	.dc-inline-bottom { flex-wrap: wrap; }
	.dc-inline-save { flex: 1 1 120px; }
}
@media (pointer: coarse) {
	.dc-inline-rca,
	.dc-rca { font-size: 16px; }
}
</style>
<div id="dc-modal" aria-hidden="true">
	<div class="dc-modal-card" role="dialog" aria-modal="true" aria-labelledby="dc-title">
		<div class="dc-modal-head">
			<div>
				<h3 id="dc-title">Dispatch panel</h3>
				<div class="dc-modal-sub">Two-step confirmation workflow with mandatory RCA on recovery.</div>
			</div>
			<button id="dc-close" type="button" class="dc-close">Close</button>
		</div>
		<div class="dc-modal-body">
			<div id="dc-banner" class="dc-banner"></div>
			<div class="dc-event">
				<span id="dc-event-title" class="dc-event-title">Loading event...</span>
				<span id="dc-state" class="dc-chip dc-chip-problem">PROBLEM</span>
			</div>
			<div class="dc-grid">
				<div class="dc-role">
					<div class="dc-role-title">Dispatcher 1</div>
					<div id="dc-role1" class="dc-role-name">-</div>
					<button id="dc-ack1" type="button" class="dc-ack dc-ack-gray">Dispatcher 1</button>
					<div id="dc-ack1-status" class="dc-ack-status"></div>
				</div>
				<div class="dc-role">
					<div class="dc-role-title">Dispatcher 2</div>
					<div id="dc-role2" class="dc-role-name">-</div>
					<button id="dc-ack2" type="button" class="dc-ack dc-ack-gray">Dispatcher 2</button>
					<div id="dc-ack2-status" class="dc-ack-status"></div>
				</div>
			</div>
			<div class="dc-history">
				<p class="dc-section-title">Comment history</p>
				<ul id="dc-history" class="dc-history-list" aria-live="polite"></ul>
				<div id="dc-history-empty" class="dc-history-empty">No comments yet.</div>
			</div>
			<p class="dc-rca-label">Recovery reason (RCA)</p>
			<p class="dc-rca-help">Required when incident is recovered. Describe root cause and what was done.</p>
			<textarea id="dc-rca" class="dc-rca" placeholder="Example: Power loss on node, UPS switched, fiber link restarted, service recovered."></textarea>
			<div class="dc-foot">
				<div id="dc-note" class="dc-note">Open incident.</div>
				<div class="dc-btns">
					<button id="dc-cancel" type="button" class="dc-btn dc-btn-secondary">Cancel</button>
					<button id="dc-save" type="button" class="dc-btn dc-btn-primary">Save RCA</button>
				</div>
			</div>
		</div>
	</div>
</div>`;

	if (!document.getElementById('dc-modal')) {
		document.body.insertAdjacentHTML('beforeend', modalTemplate);
	}

	const el = {
		modal: document.getElementById('dc-modal'),
		close: document.getElementById('dc-close'),
		cancel: document.getElementById('dc-cancel'),
		ack1: document.getElementById('dc-ack1'),
		ack2: document.getElementById('dc-ack2'),
		ack1Status: document.getElementById('dc-ack1-status'),
		ack2Status: document.getElementById('dc-ack2-status'),
		save: document.getElementById('dc-save'),
		title: document.getElementById('dc-event-title'),
		state: document.getElementById('dc-state'),
		note: document.getElementById('dc-note'),
		banner: document.getElementById('dc-banner'),
		rca: document.getElementById('dc-rca'),
		role1: document.getElementById('dc-role1'),
		role2: document.getElementById('dc-role2'),
		history: document.getElementById('dc-history'),
		historyEmpty: document.getElementById('dc-history-empty'),
		kpiTotal: document.getElementById('dc-kpi-total'),
		kpiRecovered: document.getElementById('dc-kpi-recovered'),
		kpiOpen: document.getElementById('dc-kpi-open'),
		kpiDebt: document.getElementById('dc-kpi-debt'),
		kpiMeta: document.getElementById('dc-kpi-meta')
	};

	let currentEventId = null;
	let currentRecovered = false;
	let currentHasRca = false;
	let bodyOverflow = '';
	let scanTimer = null;
	let observer = null;
	let requestSeq = 0;
	let scanInProgress = false;
	const rendered = new Map();
	const lastState = new Map();

	const setBanner = (type, text) => {
		if (!el.banner) return;
		el.banner.className = 'dc-banner';
		if (!text) {
			el.banner.textContent = '';
			return;
		}
		el.banner.classList.add(type === 'error' ? 'dc-error' : type === 'success' ? 'dc-success' : 'dc-info');
		el.banner.textContent = text;
	};

	const requestJson = async (url, options = {}) => {
		const ctrl = new AbortController();
		const timer = setTimeout(() => ctrl.abort(), REQUEST_TIMEOUT_MS);
		try {
			const resp = await fetch(url, {
				credentials: 'same-origin',
				...options,
				signal: ctrl.signal
			});
			const text = await resp.text();
			if (!resp.ok) throw new Error('HTTP ' + resp.status);
			if (!text) throw new Error('Empty API response');
			return JSON.parse(text);
		}
		finally {
			clearTimeout(timer);
		}
	};

	const prettyTime = (raw) => {
		if (raw === null || raw === undefined || raw === '') return '';
		let d = null;
		if (typeof raw === 'number') d = new Date(raw < 1000000000000 ? raw * 1000 : raw);
		else if (/^\d+$/.test(String(raw).trim())) {
			const n = Number(String(raw).trim());
			d = new Date(n < 1000000000000 ? n * 1000 : n);
		}
		else d = new Date(raw);
		if (!d || Number.isNaN(d.getTime())) return String(raw);
		return d.toLocaleString();
	};

	const normalizeHistory = (state) => {
		const arr = Array.isArray(state?.comment_history) ? state.comment_history : [];
		return arr.map((x, i) => ({
			id: String(x?.id ?? i),
			user: String(x?.user ?? 'System'),
			action: String(x?.action ?? ''),
			time: prettyTime(x?.clock ?? x?.time ?? ''),
			text: String(x?.comment ?? '')
		}));
	};

	const renderHistory = (state) => {
		if (!el.history || !el.historyEmpty) return;
		el.history.textContent = '';
		const items = normalizeHistory(state);
		el.historyEmpty.style.display = items.length ? 'none' : 'block';
		for (const item of items) {
			const li = document.createElement('li');
			li.className = 'dc-history-item';

			const meta = document.createElement('div');
			meta.className = 'dc-history-meta';

			const u = document.createElement('span');
			u.className = 'dc-history-user';
			u.textContent = item.user;
			meta.appendChild(u);

			if (item.action) {
				const a = document.createElement('span');
				a.textContent = item.action;
				meta.appendChild(a);
			}
			if (item.time) {
				const t = document.createElement('span');
				t.textContent = item.time;
				meta.appendChild(t);
			}

			const text = document.createElement('div');
			text.className = 'dc-history-text';
			text.textContent = item.text;

			li.appendChild(meta);
			li.appendChild(text);
			el.history.appendChild(li);
		}
	};

	const eventIdFromRow = (row) => {
		const cb = row?.querySelector('input[type="checkbox"][name^="eventids["]');
		return cb ? String(cb.value || '') : null;
	};

	const colIndices = (table) => {
		const result = {
			time: -1,
			status: -1,
			actions: -1,
			update: -1,
			tags: -1
		};
		if (!table) return result;
		const headers = Array.from(table.querySelectorAll('thead th'));
		headers.forEach((th, idx) => {
			const txt = (th.textContent || '').trim().toLowerCase();
			const cls = String(th.className || '').toLowerCase();
			const meta = String(th.getAttribute('data-column') || '').toLowerCase();
			const all = [txt, cls, meta].join(' ');

			if (/(^|\s)(time|время|vaqt)(\s|$)/.test(all)) result.time = idx;
			if (/(^|\s)(status|статус|holat)(\s|$)/.test(all)) result.status = idx;
			if (/(dispatch|диспетчер|update|обнов|action|действ|amal)/.test(all)) result.actions = idx;
			if (/(update|обнов|action|действ|amal)/.test(all)) result.update = idx;
			if (/(tag|тег|teg)/.test(all)) result.tags = idx;
		});
		if (result.actions < 0 && result.update >= 0) result.actions = result.update;
		if (result.actions < 0 && result.tags > 0) result.actions = result.tags - 1;
		if (result.actions < 0 && headers.length > 0) result.actions = headers.length - 1;
		if (result.update === result.actions) result.update = -1;
		if (result.tags === result.actions) result.tags = -1;
		return result;
	};

	const tableEl = () => document.querySelector('form[name="problemForm"] table.list-table, table.list-table');

	const stateFP = (s) => {
		if (!s) return 'none';
		return [
			s.recovered ? 1 : 0,
			s.d1 ? 1 : 0,
			s.d2 ? 1 : 0,
			s.has_rca ? 1 : 0,
			String(s.rca_text || '')
		].join('|');
	};

	const paintStatus = (row, recovered, cols) => {
		if (cols.status < 0) return;
		const cell = row.children[cols.status];
		if (!cell) return;
		const line = cell.querySelector('span, a, div') || cell;
		line.classList.remove('dc-status-problem', 'dc-status-resolved');
		line.classList.add(recovered ? 'dc-status-resolved' : 'dc-status-problem');
		const text = (line.textContent || '').trim();
		line.textContent = recovered ? 'RESOLVED' : 'PROBLEM';
		if (!text && line !== cell) {
			cell.textContent = recovered ? 'RESOLVED' : 'PROBLEM';
		}
	};

	const markRcaDebt = (row, required) => {
		row.classList.toggle('dc-row-rca-required', !!required);
		const durationCell = row.children[7] || null;
		if (!durationCell) return;
		let badge = durationCell.querySelector('.dc-rca-badge');
		if (required) {
			if (!badge) {
				badge = document.createElement('span');
				badge.className = 'dc-rca-badge';
				badge.textContent = 'УКАЖИТЕ ПРИЧИНУ АВАРИИ И ВОССТАНОВЛЕНИЯ';
				durationCell.appendChild(badge);
			}
		}
		else if (badge) {
			badge.remove();
		}
	};

	const setBusyModal = (busy) => {
		if (!el.ack1 || !el.ack2 || !el.save) return;
		el.ack1.disabled = busy || el.ack1.classList.contains('dc-ack-locked');
		el.ack2.disabled = busy || el.ack2.classList.contains('dc-ack-locked');
		el.save.disabled = busy;
	};

	const applyAckButton = (btn, statusNode, confirmed, canAct, labelDefault, lockReason, tone) => {
		if (!btn) return;
		btn.classList.remove('dc-ack-gray', 'dc-ack-green', 'dc-ack-blue', 'dc-ack-locked');
		if (confirmed) {
			btn.classList.add(tone === 'green' ? 'dc-ack-green' : 'dc-ack-blue');
			btn.textContent = labelDefault + ' confirmed';
			btn.disabled = true;
			if (statusNode) statusNode.textContent = 'Confirmed';
			return;
		}
		if (!canAct) {
			btn.classList.add('dc-ack-locked');
			btn.textContent = labelDefault;
			btn.disabled = true;
			if (statusNode) statusNode.textContent = lockReason || 'Unavailable';
			return;
		}
		btn.classList.add('dc-ack-gray');
		btn.textContent = 'Acknowledge ' + labelDefault;
		btn.disabled = false;
		if (statusNode) statusNode.textContent = 'Available';
	};

	const renderModal = (state) => {
		if (!state || !state.ok) return;
		currentRecovered = !!state.recovered;
		currentHasRca = !!state.has_rca;
		if (el.title) {
			el.title.textContent = 'Event #' + String(state.eventid || currentEventId || '') + ': ' + String(state.name || '');
		}
		if (el.state) {
			el.state.className = 'dc-chip ' + (state.recovered ? 'dc-chip-resolved' : 'dc-chip-problem');
			el.state.textContent = state.recovered ? 'RECOVERED' : 'PROBLEM';
		}
		if (el.role1) el.role1.textContent = String(state.dispatch_group_1 || 'Dispatcher 1');
		if (el.role2) el.role2.textContent = String(state.dispatch_group_2 || 'Dispatcher 2');

		applyAckButton(el.ack1, el.ack1Status, !!state.d1, !!state.can_ack1, 'Dispatcher 1', state.lock_reason_ack1, 'blue');
		applyAckButton(el.ack2, el.ack2Status, !!state.d2, !!state.can_ack2, 'Dispatcher 2', state.lock_reason_ack2, 'green');

		if (el.rca && document.activeElement !== el.rca) {
			el.rca.value = String(state.rca_text || '');
		}
		if (el.note) {
			el.note.textContent = state.recovered
				? (state.has_rca ? 'Incident recovered. RCA saved.' : 'Incident recovered. RCA is mandatory.')
				: 'Open incident.';
		}
		renderHistory(state);
	};

	const openModal = () => {
		if (!el.modal) return;
		el.modal.classList.add('dc-open');
		el.modal.setAttribute('aria-hidden', 'false');
		bodyOverflow = document.body.style.overflow;
		document.body.style.overflow = 'hidden';
	};

	const closeModal = () => {
		if (!el.modal) return;
		if (currentRecovered && !currentHasRca) {
			setBanner('error', 'УКАЖИТЕ ПРИЧИНУ АВАРИИ И ВОССТАНОВЛЕНИЯ');
			if (el.note) el.note.textContent = 'Enter RCA and click Save RCA.';
			el.rca?.focus();
			return;
		}
		el.modal.classList.remove('dc-open');
		el.modal.setAttribute('aria-hidden', 'true');
		document.body.style.overflow = bodyOverflow;
		setBanner('', '');
	};

	const loadModalState = async () => {
		if (!currentEventId) return;
		try {
			const data = await requestJson(apiUrl + '&eventid=' + encodeURIComponent(currentEventId));
			if (!data || !data.ok) throw new Error(data?.error || 'Cannot load state');
			renderModal(data);
			lastState.set(String(currentEventId), data);
		}
		catch (e) {
			setBanner('error', e?.message || 'Cannot load state');
		}
	};

	const postAction = async (op, extra = {}) => {
		if (!currentEventId) return;
		setBusyModal(true);
		setBanner('', '');
		try {
			const body = new URLSearchParams();
			body.set('eventid', String(currentEventId));
			body.set('op', op);
			if (typeof extra.rca_text === 'string') body.set('rca_text', extra.rca_text);

			const data = await requestJson(apiUrl, {
				method: 'POST',
				headers: {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'},
				body: body.toString()
			});
			if (!data || !data.ok) throw new Error(data?.error || 'Operation failed');

			renderModal(data);
			lastState.set(String(currentEventId), data);
			setBanner('success', op === 'rca' ? 'RCA saved.' : 'Confirmation saved.');
		}
		catch (e) {
			setBanner('error', e?.message || 'Operation failed');
		}
		finally {
			setBusyModal(false);
		}
	};

	const openForEvent = (eventid) => {
		if (!eventid) return;
		currentEventId = String(eventid);
		openModal();
		setBanner('', '');
		if (el.title) el.title.textContent = 'Loading event...';
		if (el.state) {
			el.state.className = 'dc-chip dc-chip-problem';
			el.state.textContent = 'PROBLEM';
		}
		if (el.note) el.note.textContent = 'Loading...';
		if (el.rca) el.rca.value = '';
		if (el.ack1Status) el.ack1Status.textContent = '';
		if (el.ack2Status) el.ack2Status.textContent = '';
		renderHistory({comment_history: []});
		loadModalState();
	};

	const hideCell = (row, idx) => {
		if (idx < 0) return;
		const cell = row.children[idx];
		if (cell) cell.style.display = 'none';
	};

	const createPendingState = () => ({
		ok: true,
		d1: false,
		d2: false,
		has_rca: false,
		recovered: false,
		can_ack1: false,
		can_ack2: false,
		dispatch_group_1: 'Dispatcher 1',
		dispatch_group_2: 'Dispatcher 2',
		lock_reason_ack1: 'Loading state...',
		lock_reason_ack2: 'Loading state...',
		rca_text: ''
	});

	const renderInline = (row, eventid, state, cols) => {
		const target = row.children[cols.actions];
		if (!target) return;

		const prevInput = target.querySelector('.dc-inline-rca');
		const existingText = prevInput ? prevInput.value : '';

		target.textContent = '';
		const wrap = document.createElement('div');
		wrap.className = 'dc-inline';

		const top = document.createElement('div');
		top.className = 'dc-inline-top';

		const b1 = document.createElement('button');
		b1.type = 'button';
		b1.className = 'dc-inline-btn';

		const b2 = document.createElement('button');
		b2.type = 'button';
		b2.className = 'dc-inline-btn';

		if (state.d1) {
			b1.classList.add('dc-inline-btn-blue');
			b1.textContent = 'Dispatcher 1 confirmed';
			b1.disabled = true;
		}
		else {
			b1.textContent = 'Dispatcher 1';
			b1.disabled = !state.can_ack1;
			if (!state.can_ack1) b1.classList.add('dc-inline-btn-locked');
		}

		if (state.d2) {
			b2.classList.add('dc-inline-btn-green');
			b2.textContent = 'Dispatcher 2 confirmed';
			b2.disabled = true;
		}
		else {
			b2.textContent = 'Dispatcher 2';
			b2.disabled = !state.can_ack2;
			if (!state.can_ack2) b2.classList.add('dc-inline-btn-locked');
		}

		const bottom = document.createElement('div');
		bottom.className = 'dc-inline-bottom';

		const input = document.createElement('input');
		input.type = 'text';
		input.className = 'dc-inline-rca';
		input.placeholder = 'Причина (RCA)...';
		input.value = existingText || String(state.rca_text || '');

		const save = document.createElement('button');
		save.type = 'button';
		save.className = 'dc-inline-save';
		save.textContent = 'Save RCA';

		const details = document.createElement('button');
		details.type = 'button';
		details.className = 'dc-inline-save';
		details.textContent = 'Details';

		const msg = document.createElement('div');
		msg.className = 'dc-inline-msg';
		if (state.recovered && !state.has_rca) {
			msg.textContent = 'УКАЖИТЕ ПРИЧИНУ АВАРИИ И ВОССТАНОВЛЕНИЯ';
			msg.classList.add('dc-inline-msg-error');
		}

		b1.addEventListener('click', async () => {
			if (b1.disabled) return;
			b1.disabled = true;
			msg.className = 'dc-inline-msg';
			msg.textContent = 'Saving...';
			try {
				const body = new URLSearchParams();
				body.set('eventid', String(eventid));
				body.set('op', 'ack1');
				const res = await requestJson(apiUrl, {
					method: 'POST',
					headers: {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'},
					body: body.toString()
				});
				if (!res || !res.ok) throw new Error(res?.error || 'Failed');
				lastState.set(String(eventid), res);
				renderInline(row, eventid, res, cols);
			}
			catch (e) {
				msg.className = 'dc-inline-msg dc-inline-msg-error';
				msg.textContent = e?.message || 'Failed';
				b1.disabled = false;
			}
		});

		b2.addEventListener('click', async () => {
			if (b2.disabled) return;
			b2.disabled = true;
			msg.className = 'dc-inline-msg';
			msg.textContent = 'Saving...';
			try {
				const body = new URLSearchParams();
				body.set('eventid', String(eventid));
				body.set('op', 'ack2');
				const res = await requestJson(apiUrl, {
					method: 'POST',
					headers: {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'},
					body: body.toString()
				});
				if (!res || !res.ok) throw new Error(res?.error || 'Failed');
				lastState.set(String(eventid), res);
				renderInline(row, eventid, res, cols);
			}
			catch (e) {
				msg.className = 'dc-inline-msg dc-inline-msg-error';
				msg.textContent = e?.message || 'Failed';
				b2.disabled = false;
			}
		});

		save.addEventListener('click', async () => {
			const value = (input.value || '').trim();
			if (!value) {
				msg.className = 'dc-inline-msg dc-inline-msg-error';
				msg.textContent = 'RCA is empty';
				return;
			}
			save.disabled = true;
			msg.className = 'dc-inline-msg';
			msg.textContent = 'Saving RCA...';
			try {
				const body = new URLSearchParams();
				body.set('eventid', String(eventid));
				body.set('op', 'rca');
				body.set('rca_text', value);
				const res = await requestJson(apiUrl, {
					method: 'POST',
					headers: {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'},
					body: body.toString()
				});
				if (!res || !res.ok) throw new Error(res?.error || 'Failed');
				lastState.set(String(eventid), res);
				renderInline(row, eventid, res, cols);
			}
			catch (e) {
				msg.className = 'dc-inline-msg dc-inline-msg-error';
				msg.textContent = e?.message || 'Failed';
			}
			finally {
				save.disabled = false;
			}
		});

		details.addEventListener('click', () => openForEvent(eventid));

		top.appendChild(b1);
		top.appendChild(b2);
		bottom.appendChild(input);
		bottom.appendChild(save);
		bottom.appendChild(details);
		wrap.appendChild(top);
		wrap.appendChild(bottom);
		wrap.appendChild(msg);
		target.appendChild(wrap);
		target.colSpan = 1;

		hideCell(row, cols.update);
		hideCell(row, cols.tags);
	};

	const applyOverview = (stats) => {
		if (el.kpiTotal) el.kpiTotal.textContent = String(stats.total || 0);
		if (el.kpiRecovered) el.kpiRecovered.textContent = String(stats.recovered || 0);
		if (el.kpiOpen) el.kpiOpen.textContent = String(stats.open || 0);
		if (el.kpiDebt) el.kpiDebt.textContent = String(stats.debt || 0);
		if (el.kpiMeta) {
			el.kpiMeta.textContent = 'Scanned ' + String(stats.processed || 0) + ' of ' + String(stats.total || 0)
				+ ' at ' + new Date().toLocaleTimeString();
		}
	};

	const scan = async () => {
		if (scanInProgress) return;
		scanInProgress = true;
		const seq = ++requestSeq;
		try {
			const table = tableEl();
			if (!table) return;
			const cols = colIndices(table);
			if (cols.actions < 0) return;

			const header = table.querySelectorAll('thead th');
			if (header[cols.actions]) {
				header[cols.actions].textContent = 'Dispatch Center';
				header[cols.actions].colSpan = 1;
				header[cols.actions].style.minWidth = '360px';
			}
			if (header[cols.update]) header[cols.update].style.display = 'none';
			if (header[cols.tags]) header[cols.tags].style.display = 'none';

			const rows = Array.from(table.querySelectorAll('tbody tr'));
			const targets = [];
			for (const row of rows) {
				const eventid = eventIdFromRow(row);
				if (!eventid) continue;
				targets.push({row, eventid});
				const cached = lastState.get(String(eventid)) || createPendingState();
				renderInline(row, eventid, cached, cols);
			}

			const stats = {total: targets.length, processed: 0, recovered: 0, open: 0, debt: 0};
			if (!targets.length) {
				applyOverview(stats);
				return;
			}

			const ids = targets.map((t) => String(t.eventid));
			const rowMap = new Map(targets.map((t) => [String(t.eventid), t.row]));
			const chunkSize = 80;

			for (let i = 0; i < ids.length; i += chunkSize) {
				if (seq !== requestSeq) return;
				const chunk = ids.slice(i, i + chunkSize);
				let payload = null;
				try {
					payload = await requestJson(apiUrl + '&eventids=' + encodeURIComponent(chunk.join(',')) + '&with_history=0');
				}
				catch (_e) {
					continue;
				}
				if (!payload || !payload.ok || !payload.states) continue;

				for (const eventid of chunk) {
					const row = rowMap.get(String(eventid));
					const state = payload.states[String(eventid)];
					if (!row || !state || !state.ok) continue;

					stats.processed += 1;
					if (state.recovered) stats.recovered += 1;
					else stats.open += 1;
					if (state.recovered && !state.has_rca) stats.debt += 1;

					lastState.set(String(eventid), state);
					const fp = stateFP(state);
					if (rendered.get(String(eventid)) !== fp) {
						renderInline(row, eventid, state, cols);
						rendered.set(String(eventid), fp);
					}
					paintStatus(row, !!state.recovered, cols);
					markRcaDebt(row, !!(state.recovered && !state.has_rca));
				}
			}

			applyOverview(stats);
		}
		finally {
			scanInProgress = false;
		}
	};

	const schedule = (ms) => {
		if (scanTimer) clearTimeout(scanTimer);
		scanTimer = setTimeout(async () => {
			await scan();
			schedule(document.hidden ? HIDDEN_SCAN_MS : ACTIVE_SCAN_MS);
		}, ms);
	};

	const installObserver = () => {
		if (observer) observer.disconnect();
		const table = tableEl();
		const tbody = table ? table.querySelector('tbody') : null;
		if (!tbody) return;
		observer = new MutationObserver(() => schedule(250));
		observer.observe(tbody, {childList: true, subtree: true});
	};

	if (el.close) el.close.addEventListener('click', closeModal);
	if (el.cancel) el.cancel.addEventListener('click', closeModal);
	if (el.modal) {
		el.modal.addEventListener('click', (e) => {
			if (e.target === el.modal) closeModal();
		});
	}
	document.addEventListener('keydown', (e) => {
		if (e.key === 'Escape' && el.modal && el.modal.classList.contains('dc-open')) closeModal();
	});
	if (el.ack1) el.ack1.addEventListener('click', () => postAction('ack1'));
	if (el.ack2) el.ack2.addEventListener('click', () => postAction('ack2'));
	if (el.save) el.save.addEventListener('click', () => postAction('rca', {rca_text: (el.rca?.value || '').trim()}));

	installObserver();
	scan().finally(() => schedule(document.hidden ? HIDDEN_SCAN_MS : ACTIVE_SCAN_MS));
	document.addEventListener('visibilitychange', () => schedule(document.hidden ? 1200 : 200));
	window.addEventListener('focus', () => schedule(200));
	window.addEventListener('beforeunload', () => {
		if (scanTimer) clearTimeout(scanTimer);
		if (observer) observer.disconnect();
	});
})();
JS;

	(new CScriptTag($init))->setOnDocumentReady()->show();
}
else {
	echo (new CPartial('monitoring.problem.view.html', array_intersect_key($data,
		array_flip(['page', 'action', 'sort', 'sortorder', 'filter', 'tabfilter_idx'])
	)))->getOutput();
}
