<?php declare(strict_types = 0);

namespace Widgets\DispatchProblems\Actions;

use CControllerDashboardWidgetView;
use CControllerResponseData;

class WidgetView extends CControllerDashboardWidgetView {

	protected function doAction(): void {
		$url = (new \CUrl('zabbix.php'))
			->setArgument('action', 'problem.dispatch.view')
			->setArgument('embedded', '1')
			->setArgument('kiosk', '1')
			->getUrl();

		$this->setResponse(new CControllerResponseData([
			'name' => $this->getInput('name', $this->widget->getDefaultName()),
			'url' => [
				'url' => $url,
				'error' => null
			],
			'user' => [
				'debug_mode' => $this->getDebugMode()
			]
		]));
	}
}
