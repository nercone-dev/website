// Demos of the Nercone Design pages.
// view-transition.js runs a script only once, even when the page that loaded it is opened again, so every demo is wired up
// with listeners on the document and reads the elements of the current page each time.
(() => {
    class DesignDemos {
        static DEFAULTS = {
            demoAttribute:   'data-demo',
            outputAttribute: 'data-demo-output',
            formatAttribute: 'data-swatch-format',
            progressStep:    5,
            progressDelay:   200
        };

        constructor(options = {}) {
            this.options = { ...DesignDemos.DEFAULTS, ...options };
            this.abortController = null;
            this.timer = 0;
        }

        // Lifecycle
        init() {
            this.sync();
            if (this.abortController) return;
            this.abortController = new AbortController();
            const signal = this.abortController.signal;
            document.addEventListener('click',  this.onClick,  { signal });
            document.addEventListener('input',  this.onInput,  { signal });
            document.addEventListener('change', this.onChange, { signal });
            document.addEventListener('submit', this.onSubmit, { signal });
            // close does not bubble, so it is caught while it goes down to the dialog.
            document.addEventListener('close',  this.onClose,  { signal, capture: true });
        }

        cleanup() {
            this.stopProgress();
        }

        reinit() {
            this.init();
        }

        destroy() {
            this.cleanup();
            this.abortController?.abort();
            this.abortController = null;
        }

        // Events
        onClick = (event) => {
            // The return value is cleared when a demo popup opens, so a popup closed without a value shows none.
            // This runs before the check below, because popup.js prevents the default when it opens the popup itself.
            const opener = event.target.closest?.('button[commandfor][command="show-modal"]');
            const popup = opener && document.getElementById(opener.getAttribute('commandfor'));
            if (popup instanceof HTMLDialogElement && !popup.open) popup.returnValue = '';

            if (event.defaultPrevented) return;
            const trigger = event.target.closest?.(`button[${this.options.demoAttribute}]`);
            if (!trigger) return;
            const action = this.actions[trigger.getAttribute(this.options.demoAttribute)];
            if (action) action();
        };

        onInput = (event) => {
            const input = event.target;
            const output = input.getAttribute?.(this.options.outputAttribute);
            if (output) DesignDemos.setOutput(output, input.value);
            if (input.id === 'progress-value') {
                this.stopProgress();
                this.setProgress(input.valueAsNumber);
            }
        };

        onChange = (event) => {
            // The copy format of a swatch panel is kept on the panel, where swatch.js reads it.
            const input = event.target;
            const panel = input.closest?.(`[${this.options.formatAttribute}]`);
            if (panel && input.matches('.segmented-control input')) panel.setAttribute(this.options.formatAttribute, input.value);
        };

        onSubmit = (event) => {
            const form = event.target;
            if (form.getAttribute(this.options.demoAttribute) !== 'form') return;
            event.preventDefault();
            DesignDemos.toast()?.show('The form is valid. Nothing was sent.', { variant: 'success' });
        };

        onClose = (event) => {
            const popup = event.target;
            const result = document.getElementById('popup-result');
            if (!(popup instanceof HTMLDialogElement) || !result) return;
            result.value = `${popup.id}: ${popup.returnValue || '(none)'}`;
        };

        // Actions
        actions = {
            'toast-persistent':    () => DesignDemos.toast()?.show('This message stays until you close it', { duration: 0 }),
            'toast-long':          () => DesignDemos.toast()?.show('Long messages wrap onto several lines. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.', { variant: 'information' }),
            'toast-undismissible': () => DesignDemos.toast()?.show('This toast has no close button', { dismissible: false }),
            'toast-clear':         () => DesignDemos.toast()?.clear(),
            'toast-many':          () => {
                for (let index = 1; index <= 7; index++) DesignDemos.toast()?.show(`Notification ${index}`);
            },
            'toast-paused':        () => {
                const toast = DesignDemos.toast();
                if (!toast) return;
                const element = toast.show('The timer starts in 3 seconds', { duration: 2000 });
                toast.pause(element);
                setTimeout(() => toast.resume(element), 3000);
            },
            'toast-over-popup':    () => window.nercone.get('popup')?.open('popup-toast'),
            'progress-indeterminate': () => {
                this.stopProgress();
                this.setProgress(null);
            },
            'progress-run':        () => {
                this.stopProgress();
                let value = 0;
                this.setProgress(value);
                this.timer = setInterval(() => {
                    value = Math.min(value + this.options.progressStep, 100);
                    this.setProgress(value);
                    if (value === 100) this.stopProgress();
                }, this.options.progressDelay);
            }
        };

        // Progress
        // Sets the value of the progress demos, or makes them indeterminate when VALUE is null.
        setProgress(value) {
            const range = document.getElementById('progress-value');
            if (range && value !== null) {
                range.value = value;
                window.nercone.get('slider')?.update(range);
            }
            DesignDemos.setOutput('progress-output', value === null ? '-' : String(value));
            for (const progress of document.querySelectorAll('[data-progress-demo]')) {
                if (value === null) progress.removeAttribute('aria-valuenow');
                else progress.setAttribute('aria-valuenow', value);
            }
        }

        stopProgress() {
            clearInterval(this.timer);
            this.timer = 0;
        }

        // Rendering
        sync() {
            // The browser may restore form state, so the outputs and formats are read from the inputs on load.
            for (const input of document.querySelectorAll(`[${this.options.outputAttribute}]`)) {
                DesignDemos.setOutput(input.getAttribute(this.options.outputAttribute), input.value);
            }
            for (const panel of document.querySelectorAll(`[${this.options.formatAttribute}]`)) {
                const checked = panel.querySelector('.segmented-control input:checked');
                if (checked) panel.setAttribute(this.options.formatAttribute, checked.value);
            }
            const range = document.getElementById('progress-value');
            if (range && !this.timer) this.setProgress(range.valueAsNumber);
        }

        // Helpers
        static setOutput(id, value) {
            const output = document.getElementById(id);
            if (output) output.value = value;
        }

        static toast() {
            return window.nercone.get('toast');
        }
    }

    window.nercone.DesignDemos = DesignDemos;
    window.nercone.register('design-demos', new DesignDemos());
})();
