(() => {
    for (const [id, outputId] of [['slider-volume', 'slider-volume-output'], ['slider-step', 'slider-step-output']]) {
        const slider = document.getElementById(id);
        const output = document.getElementById(outputId);
        slider.addEventListener('input', () => output.value = slider.value);
    }

    document.getElementById('form-example').addEventListener('submit', (event) => {
        event.preventDefault();
        window.nercone.get('toast')?.show('The form is valid. Nothing was sent.', { variant: 'success' });
    });
})();
