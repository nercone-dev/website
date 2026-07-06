(() => {
    class ClassPrefix {
        static CONFIG = [
            { prefix: 'small',  media: '(max-width: 768px)' },
            { prefix: 'medium', media: '(min-width: 769px) and (max-width: 1080px)' },
            { prefix: 'large',  media: '(min-width: 1081px)' }
        ];

        constructor(config = ClassPrefixManager.CONFIG) {
            this.config = config;
            this.prefixes = config.map(e => e.prefix);
            this.selector = this.prefixes.map(p => `[class*="${p}:"]`).join(',');
            this.resolvers = new Map();
            this.unsubscribers = [];
            this.bodyObserver = null;
        }

        buildResolvers() {
            for (const entry of this.config) {
                if (entry.media) {
                    const mq = window.matchMedia(entry.media);
                    this.resolvers.set(entry.prefix, () => mq.matches);
                    const h = () => this.applyAll();
                    mq.addEventListener('change', h);
                    this.unsubscribers.push(() => mq.removeEventListener('change', h));

                } else if (entry.attr) {
                    const { selector, name: attrName, value: attrValue } = entry.attr;
                    const target = document.querySelector(selector) || document.documentElement;
                    this.resolvers.set(entry.prefix, () => target.getAttribute(attrName) === attrValue);
                    const obs = new MutationObserver(() => this.applyAll());
                    obs.observe(target, { attributes: true, attributeFilter: [attrName] });
                    this.unsubscribers.push(() => obs.disconnect());

                } else if (entry.fn) {
                    this.resolvers.set(entry.prefix, entry.fn);
                }
            }
        }

        applyToElement(el) {
            if (!(el instanceof Element)) return;
            for (const cls of el.classList) {
                const i = cls.indexOf(':');
                if (i === -1) continue;

                const resolver = this.resolvers.get(cls.slice(0, i));
                if (!resolver) continue;

                const name = cls.slice(i + 1);
                if (!name) continue;

                el.classList.toggle(name, resolver());
            }
        }

        applyToSubtree(root) {
            if (root instanceof Element) this.applyToElement(root);
            if (root.querySelectorAll) {
                root.querySelectorAll(this.selector).forEach(el => this.applyToElement(el));
            }
        }

        applyAll() {
            if (document.body) this.applyToSubtree(document.body);
        }

        init() {
            this.buildResolvers();

            this.bodyObserver = new MutationObserver((mutations) => {
                for (const m of mutations) {
                    if (m.type === 'childList') {
                        for (const node of m.addedNodes) this.applyToSubtree(node);

                    } else if (m.type === 'attributes') {
                        const el = m.target;
                        const oldSet = new Set((m.oldValue || '').split(/\s+/).filter(Boolean));

                        let hasNew = false;
                        for (const cls of el.classList) {
                            const idx = cls.indexOf(':');
                            if (idx !== -1 && this.resolvers.has(cls.slice(0, idx)) && !oldSet.has(cls)) {
                                hasNew = true;
                                break;
                            }
                        }

                        if (hasNew) this.applyToElement(el);
                    }
                }
            });

            this.bodyObserver.observe(document.body, {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: ['class'],
                attributeOldValue: true
            });

            this.applyAll();
        }
    }

    const responsive = new ClassPrefix(window.nercone.responsiveConfig || ClassPrefix.CONFIG);
    window.nercone.register('responsive', { init: () => responsive.init() });
})();
