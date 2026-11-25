(() => {
    // Line charts. Chart.draw() draws arrays of numbers into a .chart element; the chart feature draws the charts
    // whose values are written in data-chart-values, such as "3 5 8 13; 1 2 - 4" (series separated by ";", "-" for no value).
    class Chart {
        static DEFAULTS = {
            selector:        '.chart',
            valuesAttribute: 'data-chart-values',
            maxAttribute:    'data-chart-max',
            lengthAttribute: 'data-chart-length'
        };
        static SVG = 'http://www.w3.org/2000/svg';
        static HEIGHT = 100;
        // Without a fixed maximum, the scale leaves this much room above the highest value.
        static HEADROOM = 1.15;

        constructor(options = {}) {
            this.options = { ...Chart.DEFAULTS, ...options };
            this.observer = null;
        }

        // Lifecycle
        init() {
            this.drawAll(document);
            if (this.observer) return;

            const { valuesAttribute, maxAttribute, lengthAttribute } = this.options;
            this.observer = new MutationObserver(this.onMutations);
            this.observer.observe(document.documentElement, {
                subtree:         true,
                childList:       true,
                attributes:      true,
                attributeFilter: [valuesAttribute, maxAttribute, lengthAttribute]
            });
        }

        reinit() {
            this.init();
        }

        destroy() {
            this.observer?.disconnect();
            this.observer = null;
        }

        // Events
        onMutations = (mutations) => {
            for (const mutation of mutations) {
                if (mutation.type === 'attributes') {
                    if (mutation.target.matches(this.options.selector)) this.drawFromAttributes(mutation.target);
                    continue;
                }
                for (const node of mutation.addedNodes) {
                    if (node.nodeType === Node.ELEMENT_NODE) this.drawAll(node);
                }
            }
        };

        // Rendering from attributes
        drawAll(root) {
            const selector = `${this.options.selector}[${this.options.valuesAttribute}]`;
            if (root.matches?.(selector)) this.drawFromAttributes(root);
            for (const element of root.querySelectorAll(selector)) this.drawFromAttributes(element);
        }

        drawFromAttributes(element) {
            const { Numbers } = window.nercone;
            const { valuesAttribute, maxAttribute, lengthAttribute } = this.options;
            const text = element.getAttribute(valuesAttribute);
            if (text === null) return;
            const series = text.split(';').map(part => part.trim().split(/\s+/).filter(Boolean).map(value => Numbers.parse(value, null)));
            Chart.draw(element, series, {
                max:    Numbers.parse(element.getAttribute(maxAttribute), null),
                length: Numbers.parse(element.getAttribute(lengthAttribute), null)
            });
        }

        // Drawing
        // Draws SERIES (arrays of numbers; null or a non-finite number leaves a gap) into ELEMENT, the last values at the right edge.
        // MAX fixes the top of the scale; otherwise it follows the highest value. LENGTH is the number of values across the chart;
        // by default, the length of the longest series.
        // Returns the top of the scale, or 0 when the scale follows the values and none is above 0.
        static draw(element, series, { max = null, length = null } = {}) {
            const count = Math.max(2, length ?? Math.max(0, ...series.map(values => values.length)));
            const width = count - 1;
            const height = Chart.HEIGHT;

            let top = max > 0 ? max : 0;
            if (!(max > 0)) {
                for (const values of series) for (const value of values) if (Number.isFinite(value) && value > top) top = value;
                top *= Chart.HEADROOM;
            }
            const scale = top > 0 ? top : 1;

            let svg = element.querySelector(':scope > svg');
            if (!svg) {
                svg = document.createElementNS(Chart.SVG, 'svg');
                svg.setAttribute('preserveAspectRatio', 'none');
                svg.setAttribute('aria-hidden', 'true');
                element.prepend(svg);
            }
            svg.setAttribute('viewBox', `0 0 ${width} ${height}`);

            series.forEach((values, index) => {
                const offset = width - (values.length - 1);
                const points = values.map((value, position) => Number.isFinite(value)
                    ? [offset + position, height - Math.min(Math.max(value / scale, 0), 1) * height]
                    : null);
                const runs = Chart.runsOf(points);
                Chart.pathOf(svg, index * 2,     `chart-area chart-series-${index + 1}`).setAttribute('d', Chart.areaPath(runs, height));
                Chart.pathOf(svg, index * 2 + 1, `chart-line chart-series-${index + 1}`).setAttribute('d', Chart.linePath(runs));
            });
            while (svg.children.length > series.length * 2) svg.lastElementChild.remove();

            return top;
        }

        static pathOf(svg, index, className) {
            let path = svg.children[index];
            if (!path) {
                path = document.createElementNS(Chart.SVG, 'path');
                svg.append(path);
            }
            path.setAttribute('class', className);
            return path;
        }

        // Splits POINTS into runs of consecutive points, at the gaps (null).
        static runsOf(points) {
            const runs = [];
            let run = [];
            for (const point of points) {
                if (point) run.push(point);
                else if (run.length) {
                    runs.push(run);
                    run = [];
                }
            }
            if (run.length) runs.push(run);
            return runs;
        }

        static linePath(runs) {
            return runs.map(run => run.map(([x, y], index) => `${index ? 'L' : 'M'}${x} ${y.toFixed(2)}`).join('')).join('');
        }

        static areaPath(runs, height) {
            return runs.map(run => `M${run[0][0]} ${height}` + run.map(([x, y]) => `L${x} ${y.toFixed(2)}`).join('') + `L${run[run.length - 1][0]} ${height}Z`).join('');
        }
    }

    window.nercone.Chart = Chart;
    window.nercone.register('chart', new Chart());
})();
