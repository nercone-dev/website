(() => {
    class Sidebar {
        static CHEVRON_RIGHT = '9 18 15 12 9 6';
        static CHEVRON_DOWN  = '6 9 12 15 18 9';

        constructor() {
            this.sidebar = document.getElementById('sidebar');
            if (this.sidebar) this.attachClickListener(this.sidebar);
        }

        createChevron() {
            const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svg.setAttribute('viewBox', '0 0 24 24');
            svg.setAttribute('fill', 'none');
            svg.setAttribute('stroke', 'currentColor');
            svg.setAttribute('stroke-width', '2');
            svg.setAttribute('stroke-linecap', 'round');
            svg.setAttribute('stroke-linejoin', 'round');
            svg.classList.add('sidebar-chevron');
            const poly = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
            poly.setAttribute('points', Sidebar.CHEVRON_RIGHT);
            svg.appendChild(poly);
            return svg;
        }

        attachClickListener(el) {
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
                if (poly) poly.setAttribute('points', isOpen ? Sidebar.CHEVRON_DOWN : Sidebar.CHEVRON_RIGHT);
            });
        }

        // Lifecycle
        init() {
            if (!this.sidebar) return;
            this.sidebar.querySelectorAll('li').forEach((li) => {
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
                btn.appendChild(this.createChevron());
                li.replaceChild(btn, title);
                li.classList.add('sidebar-folder');
                nested.hidden = true;
            });
        }

        cleanup() {}

        reinit(doc) {
            if (doc) {
                const newLayout = doc.querySelector('#sidebar-layout');
                const curLayout = document.querySelector('#sidebar-layout');

                if (curLayout && !newLayout) {
                    const main = document.querySelector('main');
                    document.querySelector('header').after(main);
                    curLayout.remove();
                } else if (!curLayout && newLayout) {
                    const main = document.querySelector('main');

                    const layout = document.createElement('div');
                    [...newLayout.attributes].forEach((a) => layout.setAttribute(a.name, a.value));

                    const sidebarEl = document.createElement('div');
                    const newSidebarEl = newLayout.querySelector('#sidebar');
                    if (newSidebarEl) {
                        [...newSidebarEl.attributes].forEach((a) => sidebarEl.setAttribute(a.name, a.value));
                        sidebarEl.innerHTML = newSidebarEl.innerHTML;
                    }

                    const contentEl = document.createElement('div');
                    const newContentEl = newLayout.querySelector('#sidebar-content');
                    if (newContentEl) {
                        [...newContentEl.attributes].forEach((a) => contentEl.setAttribute(a.name, a.value));
                    }

                    contentEl.appendChild(main);
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
                if (newSidebar !== this.sidebar) {
                    this.sidebar = newSidebar;
                    if (this.sidebar) this.attachClickListener(this.sidebar);
                }
            }

            this.init();
        }
    }

    const sidebar = new Sidebar();
    window.nercone.register('sidebar', {
        init:    () => sidebar.init(),
        cleanup: () => sidebar.cleanup(),
        reinit:  (doc) => sidebar.reinit(doc)
    });
})();
