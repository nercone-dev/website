(() => {
    // The selected format is kept on the panel, where swatch.js reads it (data-swatch-format).
    // It is read from the checked input on load as well, because the browser may restore form state.
    for (const panel of document.querySelectorAll('[data-swatch-format]')) {
        const sync = () => {
            const checked = panel.querySelector('.segmented-control input:checked');
            if (checked) panel.dataset.swatchFormat = checked.value;
        };
        panel.addEventListener('change', sync);
        sync();
    }
})();
