(() => {
    const CHEVRON_RIGHT = '9 18 15 12 9 6';
    const CHEVRON_DOWN = '6 9 12 15 18 9';

    let sidebar = document.getElementById('sidebar');

    function createChevron() {
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('viewBox', '0 0 24 24');
        svg.setAttribute('fill', 'none');
        svg.setAttribute('stroke', 'currentColor');
        svg.setAttribute('stroke-width', '2');
        svg.setAttribute('stroke-linecap', 'round');
        svg.setAttribute('stroke-linejoin', 'round');
        svg.classList.add('sidebar-chevron');
        const poly = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
        poly.setAttribute('points', CHEVRON_RIGHT);
        svg.appendChild(poly);
        return svg;
    }

    function init() {
        if (!sidebar) return;
        sidebar.querySelectorAll('li').forEach((li) => {
            if (li.dataset.sidebarInit) return;
            li.dataset.sidebarInit = '1';
            if (li.classList.contains('section')) return;
            const nested = li.querySelector(':scope > ul');
            if (!nested) return;
            const title = li.querySelector(':scope > span');
            if (!title) return;
            const btn = document.createElement('button');
            btn.className = 'sidebar-folder-toggle';
            btn.textContent = title.textContent;
            btn.appendChild(createChevron());
            li.replaceChild(btn, title);
            li.classList.add('sidebar-folder');
            nested.hidden = true;
        });
    }

    function attachClickListener(el) {
        el.addEventListener('click', (e) => {
            const btn = e.target.closest('.sidebar-folder-toggle');
            if (!btn) return;
            const li = btn.parentElement;
            const nested = li.querySelector(':scope > ul');
            if (!nested) return;
            li.classList.toggle('sidebar-folder-open');
            const isOpen = li.classList.contains('sidebar-folder-open');
            nested.hidden = !isOpen;
            const poly = btn.querySelector('.sidebar-chevron polyline');
            if (poly) poly.setAttribute('points', isOpen ? CHEVRON_DOWN : CHEVRON_RIGHT);
        });
    }

    if (sidebar) {
        attachClickListener(sidebar);
    }

    window.__sidebarCleanup = () => {};

    window.__sidebarReinit = (doc) => {
        if (doc) {
            const newLayout = doc.querySelector('#sidebar-layout');
            const curLayout = document.querySelector('#sidebar-layout');

            if (curLayout && !newLayout) {
                const main = document.querySelector('main');
                const footer = document.querySelector('footer');
                document.querySelector('header').after(main);
                main.after(footer);
                curLayout.remove();
            } else if (!curLayout && newLayout) {
                const main = document.querySelector('main');
                const footer = document.querySelector('footer');
                const newSidebarEl = newLayout.querySelector('#sidebar');
                const newContentEl = newLayout.querySelector('#sidebar-content');
                const layout = document.createElement('div');
                [...newLayout.attributes].forEach((a) => layout.setAttribute(a.name, a.value));
                const sidebarEl = document.createElement('div');
                if (newSidebarEl) {
                    [...newSidebarEl.attributes].forEach((a) => sidebarEl.setAttribute(a.name, a.value));
                    sidebarEl.innerHTML = newSidebarEl.innerHTML;
                }
                const contentEl = document.createElement('div');
                if (newContentEl) {
                    [...newContentEl.attributes].forEach((a) => contentEl.setAttribute(a.name, a.value));
                }
                contentEl.appendChild(main);
                contentEl.appendChild(footer);
                layout.appendChild(sidebarEl);
                layout.appendChild(contentEl);
                document.querySelector('header').after(layout);
            } else if (curLayout && newLayout) {
                const newSidebarEl = newLayout.querySelector('#sidebar');
                const curSidebarEl = curLayout.querySelector('#sidebar');
                if (newSidebarEl && curSidebarEl) {
                    [...curSidebarEl.attributes].forEach((a) => curSidebarEl.removeAttribute(a.name));
                    [...newSidebarEl.attributes].forEach((a) => curSidebarEl.setAttribute(a.name, a.value));
                    curSidebarEl.innerHTML = newSidebarEl.innerHTML;
                }
            }

            const newSidebar = document.getElementById('sidebar');
            if (newSidebar !== sidebar) {
                sidebar = newSidebar;
                if (sidebar) attachClickListener(sidebar);
            }
        }

        init();
    };

    init();
})();
