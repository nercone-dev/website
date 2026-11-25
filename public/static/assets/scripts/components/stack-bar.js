(() => {
    // A stack bar segment is drawn like a progress indicator, from the value in data-value between data-min (0) and data-max (1).
    const { Progress } = window.nercone;
    window.nercone.register('stack-bar', new Progress({
        selector:       '.stack-bar-segment',
        property:       '--stack-bar-value',
        min:            0,
        max:            1,
        valueAttribute: 'data-value',
        minAttribute:   'data-min',
        maxAttribute:   'data-max'
    }));
})();
