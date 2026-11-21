(() => {
    class TitleTap {
        static DEFAULTS = {
            selector:      '#title',
            href:          '/qr-code/',
            count:         3,
            interval:      400,
            touchClickGap: 300
        };

        constructor(options = {}) {
            this.options = { ...TitleTap.DEFAULTS, ...options };
            this.abortController = null;
            this.count = 0;
            this.timer = null;
            this.lastTouch = 0;
        }

        // Lifecycle
        init() {
            const element = document.querySelector(this.options.selector);
            if (!element || this.abortController) return;
            this.abortController = new AbortController();
            const signal = this.abortController.signal;

            element.addEventListener('touchend', this.onTouchEnd, { passive: false, signal });
            element.addEventListener('click',    this.onClick,    { signal });
        }

        reinit() {
            this.init();
        }

        cleanup() {
            this.abortController?.abort();
            this.abortController = null;
            this.reset();
        }

        // Events
        onTouchEnd = (event) => {
            if (event.cancelable) event.preventDefault();
            this.lastTouch = Date.now();
            this.tap();
        };

        onClick = () => {
            if (Date.now() - this.lastTouch < this.options.touchClickGap) return;
            this.tap();
        };

        // Taps
        tap() {
            clearTimeout(this.timer);
            this.count++;
            if (this.count >= this.options.count) {
                this.reset();
                window.nercone.navigate(this.options.href);
                return;
            }
            this.timer = setTimeout(() => this.reset(), this.options.interval);
        }

        reset() {
            clearTimeout(this.timer);
            this.timer = null;
            this.count = 0;
        }
    }

    window.nercone.TitleTap = TitleTap;
    window.nercone.register('title-tap', new TitleTap());
})();
