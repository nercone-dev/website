(() => {
    const overlay = document.getElementById('loading-overlay');
    if (!overlay) return;

    const svg = overlay.querySelector('svg');
    const line = overlay.querySelector('polyline');
    if (!svg || !line) { overlay.remove(); return; }

    const length = line.getTotalLength();
    line.style.strokeDasharray = length;
    line.style.strokeDashoffset = length;

    const ease = 'cubic-bezier(0.22, 1, 0.36, 1)';
    const PHASE_IN = 3000;
    const PHASE_WAIT = 1000;
    const PHASE_OUT = 1000;
    const opts = (d) => ({ duration: d, easing: ease, fill: 'forwards' });

    svg.animate([
        { opacity: 0, transform: 'scale(1)',   filter: 'blur(20px)' },
        { opacity: 1, transform: 'scale(0.5)', filter: 'blur(0px)'  }
    ], opts(PHASE_IN));
    line.animate([
        { strokeDashoffset: length },
        { strokeDashoffset: 0 }
    ], opts(PHASE_IN));

    setTimeout(() => {
        svg.animate([
            { opacity: 1, transform: 'scale(0.5)',  filter: 'blur(0px)'  },
            { opacity: 0, transform: 'scale(0.75)', filter: 'blur(20px)' }
        ], opts(PHASE_OUT));

        line.animate([
            { strokeDashoffset: 0 },
            { strokeDashoffset: length }
        ], opts(PHASE_OUT));

        overlay.animate([
            { opacity: 1, backdropFilter: 'blur(40px)', WebkitBackdropFilter: 'blur(40px)' },
            { opacity: 0, backdropFilter: 'blur(0px)',  WebkitBackdropFilter: 'blur(0px)'  }
        ], opts(PHASE_OUT));

        setTimeout(() => overlay.remove(), PHASE_OUT);
    }, PHASE_IN + PHASE_WAIT);
})();

