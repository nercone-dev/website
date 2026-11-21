(() => {
    const range         = document.getElementById('progress-value');
    const output        = document.getElementById('progress-output');
    const progresses    = document.querySelectorAll('[data-progress-demo]');
    let timer = 0;

    const setValue = (value) => {
        range.value = value;
        window.nercone.get('slider')?.update(range);
        output.value = value;
        for (const progress of progresses) progress.setAttribute('aria-valuenow', value);
    };

    range.addEventListener('input', () => {
        clearInterval(timer);
        setValue(range.value);
    });
    document.getElementById('progress-indeterminate').addEventListener('click', () => {
        clearInterval(timer);
        output.value = '-';
        for (const progress of progresses) progress.removeAttribute('aria-valuenow');
    });
    document.getElementById('progress-run').addEventListener('click', () => {
        clearInterval(timer);
        let value = 0;
        setValue(value);
        timer = setInterval(() => {
            value = Math.min(value + 5, 100);
            setValue(value);
            if (value === 100) clearInterval(timer);
        }, 200);
    });
})();
