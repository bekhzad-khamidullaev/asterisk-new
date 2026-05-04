class CWidgetDispatchProblems extends CWidget {
	_hideFullscreenActions() {
		const selectors = [
			'.js-widget-action.zi-fullscreen',
			'.js-widget-action.zi-maximize',
			'.js-widget-action[data-action="enterFullscreen"]',
			'.js-widget-action[data-action="kioskMode"]'
		];

		for (const selector of selectors) {
			for (const btn of this._target.querySelectorAll(selector)) {
				btn.style.display = 'none';
			}
		}
	}

	onStart() {
		this._events = {
			...this._events,

			mousedown: () => {
				if (this._is_edit_mode) {
					const iframe = this._contents.querySelector('iframe');

					if (iframe !== null) {
						iframe.style.pointerEvents = 'none';
						addEventListener('mouseup', this._events.mouseup, {once: true});
					}
				}
			},

			mouseup: () => {
				const iframe = this._contents.querySelector('iframe');

				if (iframe !== null) {
					iframe.style.pointerEvents = '';
				}
			}
		};
	}

	onActivate() {
		this._target.addEventListener('mousedown', this._events.mousedown);
		this._hideFullscreenActions();
	}

	onDeactivate() {
		this._target.removeEventListener('mousedown', this._events.mousedown);
	}

	hasPadding() {
		return false;
	}
}
