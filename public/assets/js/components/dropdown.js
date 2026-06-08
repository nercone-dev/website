(() => {
    const CHEVRON_DOWN = '6 9 12 15 18 9';
    const CHEVRON_UP = '6 15 12 9 18 15';

    function createChevron() {
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('viewBox', '0 0 24 24');
        svg.setAttribute('width', '12');
        svg.setAttribute('height', '12');
        svg.setAttribute('fill', 'none');
        svg.setAttribute('stroke', 'currentColor');
        svg.setAttribute('stroke-width', '2');
        svg.setAttribute('stroke-linecap', 'round');
        svg.setAttribute('stroke-linejoin', 'round');
        svg.classList.add('dropdown-chevron');
        const poly = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
        poly.setAttribute('points', CHEVRON_DOWN);
        svg.appendChild(poly);
        return svg;
    }

    function setChevron(btn, isOpen) {
        const poly = btn.querySelector('.dropdown-chevron polyline');
        if (poly) poly.setAttribute('points', isOpen ? CHEVRON_UP : CHEVRON_DOWN);
    }

    function init() {
        document.querySelectorAll('.dropdown > button').forEach((btn) => {
            if (btn.dataset.dropdownInit) return;
            btn.dataset.dropdownInit = '1';
            if (!btn.querySelector('.dropdown-chevron')) btn.appendChild(createChevron());
        });
    }

    document.addEventListener('click', (e) => {
        const toggle = e.target.closest('.dropdown > button');
        if (toggle) {
            const dropdown = toggle.closest('.dropdown');
            dropdown.classList.toggle('is-open');
            setChevron(toggle, dropdown.classList.contains('is-open'));
            return;
        }
        document.querySelectorAll('.dropdown.is-open').forEach((d) => {
            if (!d.contains(e.target)) {
                d.classList.remove('is-open');
                const btn = d.querySelector(':scope > button');
                if (btn) setChevron(btn, false);
            }
        });
    });

    window.__dropdownReinit = () => init();

    init();
})();
