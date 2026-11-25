(() => {
    class Progress {
        static DEFAULTS = {
            selector:            '.progress-linear, .progress-circular, .progress-logo',
            property:            '--progress-value',
            min:                 0,
            max:                 100,
            valueAttribute:      'aria-valuenow',
            minAttribute:        'aria-valuemin',
            maxAttribute:        'aria-valuemax',
            // Ratios (from 0 to 1) at which the value becomes a warning and a caution, such as "0.75 0.9".
            // They are read from the element or its nearest ancestor that has the attribute.
            thresholdsAttribute: 'data-progress-thresholds',
            levelAttribute:      'data-progress-level'
        };
        static LEVELS = ['warning', 'caution'];

        constructor(options = {}) {
            this.options = { ...Progress.DEFAULTS, ...options };
            this.observer = null;
        }

        get attributes() {
            const { valueAttribute, minAttribute, maxAttribute, thresholdsAttribute } = this.options;
            return [valueAttribute, minAttribute, maxAttribute, thresholdsAttribute];
        }

        // Lifecycle
        init() {
            this.updateAll(document);
            if (this.observer) return;

            this.observer = new MutationObserver(this.onMutations);
            this.observer.observe(document.documentElement, {
                subtree:         true,
                childList:       true,
                attributes:      true,
                attributeFilter: this.attributes
            });
        }

        reinit() {
            this.init();
        }

        destroy() {
            this.observer?.disconnect();
            this.observer = null;
        }

        // Events
        onMutations = (mutations) => {
            for (const mutation of mutations) {
                if (mutation.type === 'attributes') {
                    // Thresholds on an ancestor apply to every indicator inside it.
                    if (mutation.attributeName === this.options.thresholdsAttribute) this.updateAll(mutation.target);
                    else if (mutation.target.matches(this.options.selector)) this.update(mutation.target);
                    continue;
                }
                for (const node of mutation.addedNodes) {
                    if (node.nodeType === Node.ELEMENT_NODE) this.updateAll(node);
                }
            }
        };

        // Rendering
        updateAll(root) {
            if (root.matches?.(this.options.selector)) this.update(root);
            for (const element of root.querySelectorAll(this.options.selector)) this.update(element);
        }

        update(element) {
            const ratio = this.ratioOf(element);
            if (ratio === null) element.style.removeProperty(this.options.property);
            else element.style.setProperty(this.options.property, ratio);

            const level = this.levelOf(element, ratio);
            if (level === null) element.removeAttribute(this.options.levelAttribute);
            else element.setAttribute(this.options.levelAttribute, level);
        }

        ratioOf(element) {
            const { Numbers } = window.nercone;
            const { valueAttribute, minAttribute, maxAttribute } = this.options;
            const value = Numbers.parse(element.getAttribute(valueAttribute), null);
            const min   = Numbers.parse(element.getAttribute(minAttribute), this.options.min);
            const max   = Numbers.parse(element.getAttribute(maxAttribute), this.options.max);
            return value === null ? null : Numbers.ratio(value, min, max);
        }

        // Returns 'normal', 'warning' or 'caution', or null when the element has no thresholds or no value.
        levelOf(element, ratio) {
            const { thresholdsAttribute } = this.options;
            const holder = element.closest(`[${thresholdsAttribute}]`);
            if (!holder || ratio === null) return null;
            const thresholds = Progress.parseThresholds(holder.getAttribute(thresholdsAttribute));
            let level = 'normal';
            Progress.LEVELS.forEach((name, index) => {
                if (index < thresholds.length && ratio >= thresholds[index]) level = name;
            });
            return level;
        }

        static parseThresholds(text) {
            const { Numbers } = window.nercone;
            return (text ?? '').trim().split(/\s+/).map(part => Numbers.parse(part, null)).filter(value => value !== null);
        }
    }

    window.nercone.Progress = Progress;
    window.nercone.register('progress', new Progress());
})();
