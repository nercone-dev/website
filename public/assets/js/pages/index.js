(() => {
    const el = document.getElementById('big-text');
    if (!el) return;
    let tapCount = 0, tapTimer = null, lastTouch = 0;

    function onTap() {
        tapCount++;
        if (tapCount >= 3) {
            clearTimeout(tapTimer);
            tapCount = 0;
            typeof window.__navigate === 'function' ? window.__navigate('/qr-code/') : (location.href = '/qr-code/');
            return;
        }
        clearTimeout(tapTimer);
        tapTimer = setTimeout(() => { tapCount = 0; }, 400);
    }

    el.addEventListener('touchend', (e) => {
        e.preventDefault();
        lastTouch = Date.now();
        onTap();
    }, { passive: false });

    el.addEventListener('click', () => {
        if (Date.now() - lastTouch < 300) return;
        onTap();
    });
})();
