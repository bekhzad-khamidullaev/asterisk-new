<?php declare(strict_types = 0);

namespace Widgets\DispatchProblems;

use Zabbix\Core\CWidget;

class Widget extends CWidget {
	public function getDefaultName(): string {
		return _('Dispatch Problems');
	}
}
