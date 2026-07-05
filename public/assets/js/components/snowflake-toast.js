(() => {
    function init() {
        const toast = document.getElementById('snowflake-toast');
        if (!toast || toast.dataset.snowflakeToastInit) return;
        toast.dataset.snowflakeToastInit = '1';

        const closeButton = toast.querySelector('.snowflake-toast-close');
        if (closeButton) {
            closeButton.addEventListener('click', () => {
                toast.classList.add('is-hidden');
            });
        }

        const minimizeButton = toast.querySelector('.snowflake-toast-minimize');
        if (minimizeButton) {
            const setMinimized = (minimized) => {
                toast.classList.toggle('is-minimized', minimized);
                minimizeButton.setAttribute('aria-pressed', minimized ? 'true' : 'false');
                minimizeButton.setAttribute('aria-label', minimized ? '表示' : '非表示');
            };

            minimizeButton.addEventListener('click', () => {
                setMinimized(!toast.classList.contains('is-minimized'));
            });
        }
    }

    document.addEventListener('DOMContentLoaded', init);
    init();
})();
