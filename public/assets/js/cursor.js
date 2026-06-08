(() => {
    const LINK_SELECTORS = 'a, button, [role="button"], input[type="submit"], input[type="button"]';
    const PADDING = 6;
    const TOUCH_MOUSE_GUARD_MS = 800;
    const TEXT_GAP_PX = 4;
    const LINK_GAP_PX = 4;

    let ac = null;
    let sig = null;
    let mouseX = 0;
    let mouseY = 0;
    let currentLinkEl = null;
    let rafId = null;
    let cursor = null;
    let cursorVisible = false;
    let lastTouchTime = 0;
    let isMouseDown = false;

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

    function findNearbyLink(x, y) {
        const el = document.elementFromPoint(x, y);
        const exact = el ? el.closest(LINK_SELECTORS) : null;
        if (exact) return exact;

        let best = null;
        let bestDist = Infinity;
        for (const link of document.querySelectorAll(LINK_SELECTORS)) {
            const r = link.getBoundingClientRect();
            const dx = Math.max(0, r.left - x, x - r.right);
            const dy = Math.max(0, r.top  - y, y - r.bottom);
            const dist = Math.max(dx, dy);
            if (dist <= LINK_GAP_PX && dist < bestDist) {
                bestDist = dist;
                best = link;
            }
        }
        return best;
    }

    function isOverRenderedText(x, y) {
        let node, offset;
        if (document.caretPositionFromPoint) {
            const pos = document.caretPositionFromPoint(x, y);
            if (!pos || pos.offsetNode.nodeType !== Node.TEXT_NODE) return false;
            node = pos.offsetNode;
            offset = pos.offset;
        } else if (document.caretRangeFromPoint) {
            const r = document.caretRangeFromPoint(x, y);
            if (!r || r.startContainer.nodeType !== Node.TEXT_NODE) return false;
            node = r.startContainer;
            offset = r.startOffset;
        } else {
            return false;
        }

        const range = document.createRange();
        const candidates = [];
        if (offset < node.length) candidates.push([offset, offset + 1]);
        if (offset > 0)           candidates.push([offset - 1, offset]);
        if (candidates.length === 0) return false;

        for (const [s, e] of candidates) {
            range.setStart(node, s);
            range.setEnd(node, e);
            for (const rect of range.getClientRects()) {
                if (x >= rect.left - TEXT_GAP_PX && x <= rect.right  + TEXT_GAP_PX &&
                    y >= rect.top  - TEXT_GAP_PX && y <= rect.bottom + TEXT_GAP_PX) return true;
            }
        }
        return false;
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
        cursor.style.left   = (rect.left - PADDING) + 'px';
        cursor.style.top    = (rect.top  - PADDING) + 'px';
        cursor.style.width  = (rect.width  + PADDING * 2) + 'px';
        cursor.style.height = (rect.height + PADDING * 2) + 'px';

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
        ].map(v => `${parseRadius(v, w) + PADDING}px`).join(' ');
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

            const linkEl = findNearbyLink(mouseX, mouseY);

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

                if (isOverRenderedText(mouseX, mouseY)) {
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

        const newLinkEl = findNearbyLink(mouseX, mouseY);
        if (newLinkEl) {
            currentLinkEl = newLinkEl;
            rafId = requestAnimationFrame(trackLink);
        } else if (isOverRenderedText(mouseX, mouseY)) {
            cursor.classList.add('on-text');
        }

        init();
    }

    window.__cursorReinit = reinit;
    window.__cursorGetState = () => ({ mouseX, mouseY, currentLinkEl, rafId, trackLink, linkSelectors: LINK_SELECTORS });

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init, { once: true });
    } else {
        init();
    }
})();
