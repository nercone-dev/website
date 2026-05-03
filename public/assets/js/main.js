/* View Transition */
(() => {
    if (!document.startViewTransition) return;

    function preloadAssets(newDoc) {
        const curStyleHrefs = new Set(
            [...document.head.querySelectorAll('link[rel="stylesheet"]')].map(l => l.href)
        );
        const curScriptSrcs = new Set(
            [...document.head.querySelectorAll('script[src]')].map(s => s.src)
        );

        const tasks = [];

        [...newDoc.head.querySelectorAll('link[rel="stylesheet"]')]
            .filter(l => !curStyleHrefs.has(new URL(l.href, location.href).href))
            .forEach(link => tasks.push(new Promise(resolve => {
                const l = link.cloneNode(true);
                l.addEventListener('load',  resolve, { once: true });
                l.addEventListener('error', resolve, { once: true });
                document.head.appendChild(l);
            })));

        [...newDoc.head.querySelectorAll('script[src]')]
            .filter(s => !curScriptSrcs.has(new URL(s.src, location.href).href))
            .forEach(script => tasks.push(new Promise(resolve => {
                const s = document.createElement('script');
                [...script.attributes].forEach(a => s.setAttribute(a.name, a.value));
                s.addEventListener('load',  resolve, { once: true });
                s.addEventListener('error', resolve, { once: true });
                document.head.appendChild(s);
            })));

        return Promise.all(tasks);
    }

    function updateHead(newDoc) {
        const head = document.head;
        const newHead = newDoc.head;

        const t = newHead.querySelector('title');
        if (t) document.title = t.textContent;

        const META_KEEP = new Set(['charset', 'viewport', 'color-scheme', 'theme-color']);
        head.querySelectorAll('meta').forEach(m => {
            const key = m.getAttribute('name') || m.getAttribute('property');
            if (!key || META_KEEP.has(key)) return;
            m.remove();
        });
        const insertRef = head.querySelector(
            'link[rel="preconnect"], link[rel="stylesheet"], link[rel="manifest"], link[rel="icon"], script'
        );
        newHead.querySelectorAll('meta[name], meta[property]').forEach(m => {
            const key = m.getAttribute('name') || m.getAttribute('property');
            if (!META_KEEP.has(key)) head.insertBefore(m.cloneNode(true), insertRef);
        });

        const nc = newHead.querySelector('link[rel="canonical"]');
        const cc = head.querySelector('link[rel="canonical"]');
        if (nc && cc) cc.href = nc.href;

        const newStyleHrefs = new Set(
            [...newHead.querySelectorAll('link[rel="stylesheet"]')]
                .map(l => new URL(l.href, location.href).href)
        );
        head.querySelectorAll('link[rel="stylesheet"]').forEach(l => {
            if (!newStyleHrefs.has(l.href)) l.remove();
        });

        const newScriptSrcs = new Set(
            [...newHead.querySelectorAll('script[src]')]
                .map(s => new URL(s.src, location.href).href)
        );
        head.querySelectorAll('script[src]').forEach(s => {
            if (!newScriptSrcs.has(s.src)) s.remove();
        });

        head.querySelectorAll('style').forEach(s => s.remove());
        newHead.querySelectorAll('style').forEach(s => head.appendChild(s.cloneNode(true)));
    }

    let abortController = null;

    async function navigate(url) {
        if (abortController) abortController.abort();
        const ac = new AbortController();
        abortController = ac;

        document.startViewTransition(async () => {
            let response;
            try {
                response = await fetch(url.href, {
                    headers: { 'X-Requested-With': 'view-transition' },
                    signal: ac.signal
                });
            } catch (err) {
                if (err.name === 'AbortError') return;
                location.href = url.href;
                return;
            }

            if (ac.signal.aborted) return;

            const html = await response.text();
            const doc = new DOMParser().parseFromString(html, 'text/html');

            if (typeof window.__cursorCleanup === 'function') {
                window.__cursorCleanup();
            }

            await preloadAssets(doc);
            updateHead(doc);

            for (const tag of ['header', 'main', 'footer']) {
                const newEl = doc.querySelector(tag);
                const curEl = document.querySelector(tag);
                if (!newEl || !curEl) { location.href = url.href; return; }
                [...curEl.attributes].forEach(a => curEl.removeAttribute(a.name));
                [...newEl.attributes].forEach(a => curEl.setAttribute(a.name, a.value));
                curEl.innerHTML = newEl.innerHTML;
                curEl.querySelectorAll('script').forEach(old => {
                    const s = document.createElement('script');
                    [...old.attributes].forEach(a => s.setAttribute(a.name, a.value));
                    s.textContent = old.textContent;
                    old.replaceWith(s);
                });
            }

            history.pushState(null, '', response.url);

            if (typeof window.__cursorReinit === 'function') {
                window.__cursorReinit();
            }
        });
    }

    window.__navigate = function (href) {
        let url;
        try { url = new URL(href, location.href); } catch (_) { location.href = href; return; }
        if (url.origin !== location.origin) { location.href = href; return; }
        navigate(url);
    };

    document.addEventListener('click', (event) => {
        const link = event.target.closest('a');
        if (!link || link.hasAttribute('download')) return;

        const url = new URL(link.href, location.href);
        if (url.origin !== location.origin) return;
        if (link.target || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

        if (url.hash && url.pathname === location.pathname) {
            event.preventDefault();
            const target = document.querySelector(url.hash);
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                history.pushState(null, '', url.hash);
            }
            return;
        }

        event.preventDefault();
        navigate(url);
    });

    window.addEventListener('popstate', () => location.reload());
})();

/* Cursor */
(() => {
    const textSelectors = 'p, h1, h2, h3, h4, h5, h6, span, li, label, td, th, pre, .code';
    const linkSelectors = 'a, button, [role="button"], input[type="submit"], input[type="button"]';
    const padding = 6;

    let ac = null;
    let sig = null;

    let mouseX = 0, mouseY = 0;
    let currentLinkEl = null;
    let rafId = null;
    let cursor = null;
    let cursorVisible = false;
    let lastTouchTime = 0;
    let isMouseDown = false;
    const TOUCH_MOUSE_GUARD_MS = 800;

    window.__cursorCleanup = () => {
        if (ac) ac.abort();
        if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
        document.documentElement.style.cursor = '';
        if (cursor) cursor.classList.remove('visible', 'on-link', 'on-text');
        cursorVisible = false;
        currentLinkEl = null;
    };

    function showCursor() {
        if (!cursorVisible && cursor) {
            cursorVisible = true;
            cursor.classList.add('visible');
        }
    }

    function hideCursor() {
        if (cursor) {
            cursorVisible = false;
            cursor.style.borderRadius = '';
            cursor.classList.remove('visible');
            currentLinkEl = null;
            if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
            cursor.classList.remove('on-link', 'on-text');
        }
    }

    function isSyntheticMouse() {
        return Date.now() - lastTouchTime < TOUCH_MOUSE_GUARD_MS;
    }

    function updateCursorForLink(el) {
        let rect = el.getBoundingClientRect();

        if (getComputedStyle(el).display === 'inline') {
            const descendants = el.querySelectorAll('*');
            if (descendants.length > 0) {
                const rects = [...descendants].map(c => c.getBoundingClientRect());
                const left   = Math.min(...rects.map(r => r.left));
                const top    = Math.min(...rects.map(r => r.top));
                const right  = Math.max(...rects.map(r => r.right));
                const bottom = Math.max(...rects.map(r => r.bottom));
                rect = { left, top, width: right - left, height: bottom - top };
            }
        }

        cursor.classList.remove('on-text');
        cursor.classList.add('on-link');
        cursor.style.transform = 'none';
        cursor.style.left   = (rect.left - padding) + 'px';
        cursor.style.top    = (rect.top  - padding) + 'px';
        cursor.style.width  = (rect.width  + padding * 2) + 'px';
        cursor.style.height = (rect.height + padding * 2) + 'px';

        function parseRadius(val, wRef) {
            if (!val) return 0;
            const first = val.trim().split(' ')[0];
            return first.endsWith('%') ? parseFloat(first) / 100 * wRef : (parseFloat(first) || 0);
        }
        function resolveRadiusSource(el, wRef) {
            const PROPS = [
                'borderTopLeftRadius', 'borderTopRightRadius',
                'borderBottomRightRadius', 'borderBottomLeftRadius',
            ];
            for (const target of [el, ...el.children]) {
                const cs = getComputedStyle(target);
                if (PROPS.some(p => parseRadius(cs[p], wRef) > 0)) return cs;
            }
            return getComputedStyle(el);
        }
        const w = rect.width;
        const cs = resolveRadiusSource(el, w);
        cursor.style.borderRadius = [
            cs.borderTopLeftRadius,
            cs.borderTopRightRadius,
            cs.borderBottomRightRadius,
            cs.borderBottomLeftRadius,
        ].map(v => `${parseRadius(v, w) + padding}px`).join(' ');
    }

    function trackLink() {
        if (currentLinkEl) {
            updateCursorForLink(currentLinkEl);
            rafId = requestAnimationFrame(trackLink);
        }
    }

    document.documentElement.style.cursor = 'none';

    function init() {
        ac = new AbortController();
        sig = ac.signal;

        cursor = document.getElementById('cursor');
        if (!cursor) return;

        document.addEventListener('touchstart', () => { lastTouchTime = Date.now(); hideCursor(); }, { passive: true, signal: sig });
        document.addEventListener('touchmove',  () => { lastTouchTime = Date.now(); hideCursor(); }, { passive: true, signal: sig });
        document.addEventListener('touchend',   () => { lastTouchTime = Date.now(); },               { passive: true, signal: sig });

        document.addEventListener('mousemove', (e) => {
            if (isSyntheticMouse()) return;
            if (e.sourceCapabilities && e.sourceCapabilities.firesTouchEvents) return;

            mouseX = e.clientX;
            mouseY = e.clientY;

            showCursor();

            const el = document.elementFromPoint(mouseX, mouseY);
            const linkEl = el ? el.closest(linkSelectors) : null;

            if (linkEl) {
                if (currentLinkEl !== linkEl) {
                    currentLinkEl = linkEl;
                    if (rafId) cancelAnimationFrame(rafId);
                    rafId = requestAnimationFrame(trackLink);
                }
            } else {
                if (currentLinkEl) {
                    currentLinkEl = null;
                    if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
                }
                cursor.classList.remove('on-link');
                cursor.style.transform = isMouseDown ? 'translate(-50%, -50%) scale(0.9)' : 'translate(-50%, -50%)';
                cursor.style.borderRadius = '';
                cursor.style.left = mouseX + 'px';
                cursor.style.top  = mouseY + 'px';
                cursor.style.width = '';
                cursor.style.height = '';

                if (el && el.closest(textSelectors)) {
                    cursor.classList.add('on-text');
                } else {
                    cursor.classList.remove('on-text');
                }
            }
        }, { signal: sig });

        document.addEventListener('mousedown', () => {
            isMouseDown = true;
            cursor.style.transform = currentLinkEl ? 'none' : 'translate(-50%, -50%) scale(0.9)';
        }, { signal: sig });
        document.addEventListener('mouseup', () => {
            isMouseDown = false;
            cursor.style.transform = currentLinkEl ? 'none' : 'translate(-50%, -50%) scale(1)';
        }, { signal: sig });

        window.addEventListener('scroll', () => {
            if (currentLinkEl) updateCursorForLink(currentLinkEl);
        }, { passive: true, signal: sig });
    }

    function reinit() {
        cursor = document.getElementById('cursor');
        if (!cursor) return;

        currentLinkEl = null;
        if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
        cursor.classList.remove('on-link', 'on-text');
        cursor.style.transform = 'translate(-50%, -50%)';
        cursor.style.borderRadius = '';
        cursor.style.left = mouseX + 'px';
        cursor.style.top  = mouseY + 'px';
        cursor.style.width = '';
        cursor.style.height = '';

        const el = document.elementFromPoint(mouseX, mouseY);
        const newLinkEl = el ? el.closest(linkSelectors) : null;
        if (newLinkEl) {
            currentLinkEl = newLinkEl;
            rafId = requestAnimationFrame(trackLink);
        } else if (el && el.closest(textSelectors)) {
            cursor.classList.add('on-text');
        }

        init();
    }

    window.__cursorReinit = reinit;
    window.__cursorGetState = () => ({ mouseX, mouseY, currentLinkEl, rafId, trackLink, linkSelectors, textSelectors });

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init, { once: true });
    } else {
        init();
    }
})();

/* Loading Overlay */
(() => {
    const overlay = document.getElementById('loading-overlay');
    if (!overlay) return;

    const svg = overlay.querySelector('svg');
    const line = overlay.querySelector('polyline');
    if (!svg || !line) { overlay.remove(); return; }

    const length = line.getTotalLength();
    line.style.strokeDasharray = length;
    line.style.strokeDashoffset = length;

    const ease = 'cubic-bezier(0.22, 1, 0.36, 1)';
    const PHASE_IN = 3000;
    const PHASE_WAIT = 1000;
    const PHASE_OUT = 1000;
    const opts = (d) => ({ duration: d, easing: ease, fill: 'forwards' });

    svg.animate([
        { opacity: 0, transform: 'scale(1)',   filter: 'blur(20px)' },
        { opacity: 1, transform: 'scale(0.5)', filter: 'blur(0px)'  }
    ], opts(PHASE_IN));
    line.animate([
        { strokeDashoffset: length },
        { strokeDashoffset: 0 }
    ], opts(PHASE_IN));

    setTimeout(() => {
        svg.animate([
            { opacity: 1, transform: 'scale(0.5)',  filter: 'blur(0px)'  },
            { opacity: 0, transform: 'scale(0.75)', filter: 'blur(20px)' }
        ], opts(PHASE_OUT));

        line.animate([
            { strokeDashoffset: 0 },
            { strokeDashoffset: length }
        ], opts(PHASE_OUT));

        overlay.animate([
            { opacity: 1, backdropFilter: 'blur(40px)', WebkitBackdropFilter: 'blur(40px)' },
            { opacity: 0, backdropFilter: 'blur(0px)',  WebkitBackdropFilter: 'blur(0px)'  }
        ], opts(PHASE_OUT));

        setTimeout(() => overlay.remove(), PHASE_OUT);
    }, PHASE_IN + PHASE_WAIT);
})();
