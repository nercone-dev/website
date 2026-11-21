(() => {
    const result = document.getElementById('popup-result');
    for (const popup of document.querySelectorAll('dialog')) {
        popup.addEventListener('close', () => {
            result.value = `${popup.id}: ${popup.returnValue || '(none)'}`;
            popup.returnValue = '';
        });
    }

    const toast = () => window.nercone.get('toast');
    document.getElementById('toast-persistent').addEventListener('click', () => {
        toast().show('This message stays until you close it', { duration: 0 });
    });
    document.getElementById('toast-long').addEventListener('click', () => {
        toast().show('Long messages wrap onto several lines. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.', { variant: 'information' });
    });
    document.getElementById('toast-many').addEventListener('click', () => {
        for (let index = 1; index <= 7; index++) toast().show(`Notification ${index}`);
    });
    document.getElementById('toast-undismissible').addEventListener('click', () => {
        toast().show('This toast has no close button', { dismissible: false });
    });
    document.getElementById('toast-paused').addEventListener('click', () => {
        const element = toast().show('The timer starts in 3 seconds', { duration: 2000 });
        toast().pause(element);
        setTimeout(() => toast().resume(element), 3000);
    });
    document.getElementById('toast-over-popup').addEventListener('click', () => {
        window.nercone.get('popup').open('popup-toast');
    });
    document.getElementById('toast-clear').addEventListener('click', () => {
        toast().clear();
    });
})();
