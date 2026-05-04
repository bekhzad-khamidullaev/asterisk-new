<?php declare(strict_types = 0);

/**
 * Dispatch Problems widget view.
 *
 * @var CView $this
 * @var array $data
 */

if ($data['url']['error'] !== null) {
	$item = (new CTableInfo())->setNoDataMessage($data['url']['error']);
}
else {
	$item = (new CIFrame($data['url']['url'], '100%', '100%', 'auto'))->addClass(ZBX_STYLE_WIDGET_URL);
}

(new CWidgetView($data))
	->addItem($item)
	->show();
