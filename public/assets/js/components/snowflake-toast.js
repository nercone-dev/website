(() => {
    const STORAGE_KEY = 'dev.nercone.options.snowflake.dismissed';

    function init() {
        const toast = document.getElementById('snowflake-toast');
        if (!toast || toast.dataset.snowflakeToastInit) return;
        toast.dataset.snowflakeToastInit = '1';

        if (localStorage.getItem(STORAGE_KEY) === '1') {
            toast.classList.add('is-hidden');
            return;
        }

        const closeButton = toast.querySelector('.snowflake-toast-close');
        if (closeButton) {
            closeButton.addEventListener('click', () => {
                toast.classList.add('is-hidden');
                localStorage.setItem(STORAGE_KEY, '1');
            });
        }
    }

    document.addEventListener('DOMContentLoaded', init);
    init();
})();
