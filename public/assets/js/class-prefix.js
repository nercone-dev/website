(() => {
    const CONFIG = [
        { prefix: 'small',  media: '(max-width: 512px)' },
        { prefix: 'medium', media: '(min-width: 512px) and (max-width: 1080px)' },
        { prefix: 'large',  media: '(min-width: 1081px)' }
    ];

    function buildResolvers(config, onAnyChange) {
        const resolvers = new Map();
        const unsubscribers = [];

        config.forEach((entry) => {
            if (entry.media) {
                const mq = window.matchMedia(entry.media);
                resolvers.set(entry.prefix, () => mq.matches);
                const h = () => onAnyChange();
                mq.addEventListener('change', h);
                unsubscribers.push(() => mq.removeEventListener('change', h));

            } else if (entry.attr) {
                const { selector, name: attrName, value: attrValue } = entry.attr;
                const target = document.querySelector(selector) || document.documentElement;
                resolvers.set(entry.prefix, () => target.getAttribute(attrName) === attrValue);
                const obs = new MutationObserver(() => onAnyChange());
                obs.observe(target, { attributes: true, attributeFilter: [attrName] });
                unsubscribers.push(() => obs.disconnect());

            } else if (entry.fn) {
                resolvers.set(entry.prefix, entry.fn);
            }
        });

        return { resolvers, unsubscribers };
    }

    function buildSelector(prefixes) {
        return prefixes.map(p => `[class*="${p}:"]`).join(',');
    }

    function applyToElement(el, resolvers) {
        if (!(el instanceof Element)) return;
        for (const cls of el.classList) {
            const i = cls.indexOf(':');
            if (i === -1) continue;
            const prefix = cls.slice(0, i);
            const resolver = resolvers.get(prefix);
            if (!resolver) continue;
            const name = cls.slice(i + 1);
            if (!name) continue;
            el.classList.toggle(name, resolver());
        }
    }

    let state = null;

    function init() {
        const config = window.__classPrefixConfig || CONFIG;
        const prefixes = config.map(e => e.prefix);
        const selector = buildSelector(prefixes);

        function applyToSubtree(root) {
            if (root instanceof Element) applyToElement(root, state.resolvers);
            if (root.querySelectorAll) {
                root.querySelectorAll(selector).forEach(el => applyToElement(el, state.resolvers));
            }
        }

        function applyAll() {
            if (document.body) applyToSubtree(document.body);
        }

        const built = buildResolvers(config, applyAll);

        const bodyObserver = new MutationObserver((mutations) => {
            for (const m of mutations) {
                if (m.type === 'childList') {
                    for (const node of m.addedNodes) {
                        applyToSubtree(node);
                    }
                } else if (m.type === 'attributes') {
                    const el = m.target;
                    const oldSet = new Set((m.oldValue || '').split(/\s+/).filter(Boolean));
                    let hasNew = false;
                    for (const cls of el.classList) {
                        const idx = cls.indexOf(':');
                        if (idx !== -1 && state.resolvers.has(cls.slice(0, idx)) && !oldSet.has(cls)) {
                            hasNew = true;
                            break;
                        }
                    }
                    if (hasNew) applyToElement(el, state.resolvers);
                }
            }
        });

        bodyObserver.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['class'],
            attributeOldValue: true,
        });

        state = {
            resolvers: built.resolvers,
            unsubscribers: built.unsubscribers,
            bodyObserver,
            applyAll,
        };

        applyAll();
    }

    function cleanup() {
        if (!state) return;
        state.bodyObserver.disconnect();
        state.unsubscribers.forEach(unsub => unsub());
        state = null;
    }

    init();

    window.__classPrefixApply   = () => { if (state) state.applyAll(); };
    window.__classPrefixCleanup = cleanup;
    window.__classPrefixReinit  = () => { cleanup(); init(); };
})();
