(() => {
    class Snowflake {
        init() {
            const toast = document.getElementById('snowflake');
            if (!toast || toast.dataset.snowflakeInit) return;
            toast.dataset.snowflakeInit = '1';

            const closeButton = toast.querySelector('.snowflake-close');
            if (closeButton) {
                closeButton.addEventListener('click', () => toast.classList.add('is-hidden'));
            }

            const minimizeButton = toast.querySelector('.snowflake-minimize');
            if (minimizeButton) {
                const setMinimized = (minimized) => {
                    toast.classList.toggle('is-minimized', minimized);
                    minimizeButton.setAttribute('aria-pressed', minimized ? 'true' : 'false');
                    minimizeButton.setAttribute('aria-label', minimized ? '表示' : '非表示');
                };
                minimizeButton.addEventListener('click', () => setMinimized(!toast.classList.contains('is-minimized')));
            }
        }
    }

    const snowflake = new Snowflake();
    window.nercone.register('snowflake', { init: () => snowflake.init() });
})();
