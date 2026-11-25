// Server status dashboard. Polls /api/v1/status and fills the current page with window.nercone.Binding (binding.js).
// view-transition.js runs a script only once, even when another status page is opened, so the dashboard reads the elements
// of the current page each time it renders, and keeps the history of the values while the visitor moves between the pages.
//
// Besides the attributes of binding.js, the pages use:
//   data-status-chart="KEY [KEY]"  draws the history of KEYs into a .chart with Chart.draw(). data-chart-max fixes the top
//                                  of the scale, and a .chart-scale inside shows the top, formatted by data-format.
//                                  In list items, the keys come from the data with data-bind-attr="data-status-chart: chart".
(() => {
    const { Binding } = window.nercone;

    // The API gives capacities, traffic and I/O in bits. They are shown in bytes, and speeds of networks in bits per second.
    class StatusFormat {
        static BITS_PER_BYTE = 8;
        static SI_BITS = ['bps', 'kbps', 'Mbps', 'Gbps', 'Tbps'];
        static LOCALE = 'ja-JP';

        static formatters() {
            const base = Binding.formatters(StatusFormat.LOCALE);
            return {
                bytes:     (bits)  => base.bytes(bits / StatusFormat.BITS_PER_BYTE),
                byterate:  (bits)  => `${base.bytes(bits / StatusFormat.BITS_PER_BYTE)}/s`,
                bitrate:   (bits)  => Binding.scaled(bits, 1000, StatusFormat.SI_BITS),
                ghz:       (value) => `${value.toFixed(2)} GHz`,
                celsius:   (value) => `${value.toFixed(1)} °C`,
                mts:       (value) => `${base.number(value)} MT/s`,
                ms:        (value) => `${base.number(value)} ms`,
                up:        (value) => value ? 'UP' : 'DOWN',
                installed: (value) => value ? '装着済み' : '空き'
            };
        }
    }

    class StatusHistory {
        // Values of every key at the same moments. A key that a sample does not have gets null there.
        constructor(length) {
            this.length = length;
            this.size = 0;
            this.series = new Map();
        }

        record(values) {
            for (const [key, series] of this.series) series.push(values.has(key) ? values.get(key) : null);
            for (const [key, value] of values) {
                if (this.series.has(key)) continue;
                const series = new Array(this.size).fill(null);
                series.push(value);
                this.series.set(key, series);
            }
            this.size += 1;

            if (this.size > this.length) {
                const excess = this.size - this.length;
                for (const series of this.series.values()) series.splice(0, excess);
                this.size = this.length;
            }
        }

        get(key) {
            return this.series.get(key) ?? null;
        }
    }

    class StatusData {
        // Adds values computed from the response (ratios, rates, totals, history keys) next to the values they come from.
        // PREVIOUS is the data of the last response and ELAPSED the seconds since it, for the rates.
        static derive(data, previous, elapsed) {
            const hardwares = data.system?.hardwares ?? {};
            const before = previous?.system?.hardwares ?? {};

            const cpus = hardwares.cpu ?? [];
            cpus.forEach((cpu, index) => {
                cpu.chart = `cpu.${index}`;
                // Usage is per logical processor and temperature per physical core, so their indexes do not match and they stay apart.
                cpu.usage.core_list = Object.entries(cpu.usage.cores ?? {}).map(([core, usage]) => ({ index: Number(core), usage }));
                cpu.temperature.core_list = Object.entries(cpu.temperature.cores ?? {}).map(([core, temperature]) => ({ index: Number(core), temperature }));
            });

            const ram = hardwares.ram;
            if (ram) {
                ram.usage.ratio = StatusData.ratio(ram.usage.used, ram.usage.total);
                ram.usage.available_ratio = StatusData.ratio(ram.usage.available, ram.usage.total);
                ram.usage.cache_ratio = StatusData.ratio(ram.usage.cache, ram.usage.total);
                if (ram.swap) ram.swap.ratio = StatusData.ratio(ram.swap.used, ram.swap.total);
                for (const slot of ram.slots ?? []) slot.installed = !slot.free;
                ram.slots_installed = (ram.slots ?? []).filter(slot => !slot.free).length;
                ram.slots_total = ram.slots ? ram.slots.length : null;
            }

            const gpus = hardwares.gpu ?? [];
            gpus.forEach((gpu, index) => {
                gpu.index = index;
                gpu.chart = `gpu.${index}`;
                for (const kind of ['dedicated', 'shared']) {
                    const vram = gpu.vram?.usage?.[kind];
                    if (vram) vram.ratio = StatusData.ratio(vram.used, vram.total);
                }
            });

            const networks = hardwares.network ?? [];
            const networksBefore = new Map((before.network ?? []).map(network => [network.name, network]));
            for (const network of networks) {
                const last = networksBefore.get(network.name);
                network.rate = {
                    sent:     StatusData.rate(network.traffic.sent,     last?.traffic.sent,     elapsed),
                    received: StatusData.rate(network.traffic.received, last?.traffic.received, elapsed)
                };
                network.chart = `network.${network.name}.received network.${network.name}.sent`;
            }

            const storages = hardwares.storage ?? [];
            const storagesBefore = new Map((before.storage ?? []).map(storage => [storage.device, storage]));
            for (const storage of storages) {
                const last = storagesBefore.get(storage.device);
                if (storage.usage) {
                    const usage = storage.usage;
                    usage.ratio = StatusData.ratio(usage.used, usage.total);
                    // Purgeable space (macOS): available to programs, but not free yet.
                    usage.purgeable = Number.isFinite(usage.available) && Number.isFinite(usage.free) ? Math.max(usage.available - usage.free, 0) : null;
                    usage.purgeable_ratio = StatusData.ratio(usage.purgeable, usage.total);
                }
                storage.rate = {
                    read:    StatusData.rate(storage.io.read,    last?.io.read,    elapsed),
                    written: StatusData.rate(storage.io.written, last?.io.written, elapsed)
                };
            }
            // Storages on the same disk (such as APFS volumes) share its counters, which are counted once in the total.
            const disks = new Map();
            for (const storage of storages) {
                if (storage.io.device !== null && !disks.has(storage.io.device)) disks.set(storage.io.device, storage.rate);
            }

            const up = networks.filter(network => network.up);
            const root = storages.find(storage => storage.mountpoints.includes('/')) ?? storages[0] ?? null;
            data.summary = {
                cpu:      StatusData.average(cpus.map(cpu => cpu.usage.average)),
                ram:      ram ? ram.usage.ratio : null,
                swap:     ram?.swap ? ram.swap.ratio : null,
                storage:  root,
                gpu:      StatusData.average(gpus.map(gpu => gpu.usage)),
                gpus:     gpus.length,
                network: {
                    up:       up.length,
                    total:    networks.length,
                    sent:     StatusData.sum(up.map(network => network.rate.sent)),
                    received: StatusData.sum(up.map(network => network.rate.received))
                },
                disk: {
                    devices: [...disks.keys()],
                    read:    StatusData.sum([...disks.values()].map(rate => rate.read)),
                    written: StatusData.sum([...disks.values()].map(rate => rate.written))
                }
            };
            return data;
        }

        // Values recorded in the history, by key. Pages refer to these keys with data-status-chart.
        static samples(data) {
            const hardwares = data.system?.hardwares ?? {};
            const summary = data.summary;
            const values = new Map([
                ['cpu',               summary.cpu],
                ['ram',               summary.ram],
                ['swap',              summary.swap],
                ['gpu',               summary.gpu],
                ['network.sent',      summary.network.sent],
                ['network.received',  summary.network.received],
                ['disk.read',         summary.disk.read],
                ['disk.written',      summary.disk.written]
            ]);
            (hardwares.cpu ?? []).forEach((cpu, index) => values.set(`cpu.${index}`, cpu.usage.average));
            for (const gpu of hardwares.gpu ?? []) values.set(`gpu.${gpu.index}`, gpu.usage);
            for (const network of hardwares.network ?? []) {
                values.set(`network.${network.name}.sent`,     network.rate.sent);
                values.set(`network.${network.name}.received`, network.rate.received);
            }
            return values;
        }

        static ratio(value, total) {
            return Number.isFinite(value) && Number.isFinite(total) && total > 0 ? value / total : null;
        }

        // A counter that went down was reset (such as by a restart of the interface), so there is no rate for that interval.
        static rate(value, last, elapsed) {
            if (!Number.isFinite(value) || !Number.isFinite(last) || !(elapsed > 0) || value < last) return null;
            return (value - last) / elapsed;
        }

        static sum(values) {
            const known = values.filter(Number.isFinite);
            return known.length ? known.reduce((total, value) => total + value, 0) : null;
        }

        static average(values) {
            const known = values.filter(Number.isFinite);
            return known.length ? StatusData.sum(known) / known.length : null;
        }
    }

    class StatusDashboard {
        static DEFAULTS = {
            url:           '/api/v1/status',
            interval:      2000,
            timeout:       10000,
            historyLength: 150,
            pageSelector:  '[data-status-page]'
        };

        static CONNECTION_TEXT = {
            loading: '接続中…',
            live:    'ライブ',
            paused:  '一時停止中',
            hidden:  '待機中',
            error:   '取得に失敗しました'
        };

        constructor(options = {}) {
            this.options = { ...StatusDashboard.DEFAULTS, ...options };
            this.binding = new Binding({ locale: StatusFormat.LOCALE, formatters: StatusFormat.formatters() });
            this.interval = this.options.interval;
            this.paused = false;
            this.timer = 0;
            this.request = null;
            this.data = null;
            this.receivedAt = 0;
            this.error = null;
            this.history = new StatusHistory(this.options.historyLength);
            this.abortController = null;
        }

        // Lifecycle
        init() {
            if (!this.abortController) {
                this.abortController = new AbortController();
                const signal = this.abortController.signal;
                document.addEventListener('change', this.onChange, { signal });
                document.addEventListener('click', this.onClick, { signal });
                document.addEventListener('visibilitychange', this.onVisibilityChange, { signal });
            }

            if (!this.page()) return;
            this.syncControls();
            if (this.data) this.render();
            this.schedule(0);
        }

        cleanup() {
            this.stop();
        }

        reinit() {
            this.init();
        }

        destroy() {
            this.stop();
            this.abortController?.abort();
            this.abortController = null;
        }

        page() {
            return document.querySelector(this.options.pageSelector);
        }

        // Events
        onChange = (event) => {
            const input = event.target;
            if (input.name !== 'status-interval' || !input.closest(this.options.pageSelector)) return;
            const interval = Number(input.value);
            if (!Number.isFinite(interval) || interval <= 0) return;
            this.interval = interval;
            if (!this.paused) this.schedule(this.interval);
        };

        onClick = (event) => {
            const button = event.target.closest?.('[data-status-pause]');
            if (!button || !button.closest(this.options.pageSelector)) return;
            this.paused = !this.paused;
            this.syncControls();
            if (this.paused) this.stop();
            else this.schedule(0);
            this.renderConnection();
        };

        onVisibilityChange = () => {
            if (!this.page()) return;
            // A hidden page has nobody to show the values to, so it does not ask the server for them.
            if (document.hidden) this.stop();
            else this.schedule(0);
            this.renderConnection();
        };

        // Polling
        schedule(delay) {
            clearTimeout(this.timer);
            this.timer = 0;
            if (this.paused || document.hidden || !this.page()) return;
            this.timer = setTimeout(this.poll, delay);
        }

        stop() {
            clearTimeout(this.timer);
            this.timer = 0;
            this.request?.abort();
            this.request = null;
        }

        poll = async () => {
            this.timer = 0;
            if (this.request) return;
            const request = new AbortController();
            this.request = request;
            const timeout = setTimeout(() => request.abort(), this.options.timeout);
            const startedAt = performance.now();

            try {
                const response = await fetch(this.options.url, { cache: 'no-store', headers: { Accept: 'application/json' }, signal: request.signal });
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                const text = await response.text();
                this.receive(text, startedAt, performance.now());
                this.error = null;
            } catch (error) {
                // Aborted by stop(): nothing failed, so nothing is shown.
                if (request.signal.aborted && this.request !== request) return;
                this.error = request.signal.aborted ? 'タイムアウトしました' : String(error.message || error);
            } finally {
                clearTimeout(timeout);
                if (this.request === request) {
                    this.request = null;
                    this.render();
                    this.schedule(this.interval);
                }
            }
        };

        receive(text, startedAt, receivedAt) {
            const previous = this.data;
            const elapsed = previous ? (receivedAt - this.receivedAt) / 1000 : 0;
            const data = StatusData.derive(JSON.parse(text), previous, elapsed);
            data.client = {
                latency:  receivedAt - startedAt,
                interval: this.interval,
                updated:  Date.now(),
                samples:  this.history.size + 1
            };
            // The response as the API sent it, without the derived values. Only the API page shows it, so it is parsed only there.
            Object.defineProperty(data, 'response', { get: () => JSON.parse(text), enumerable: false });
            this.history.record(StatusData.samples(data));
            this.data = data;
            this.receivedAt = receivedAt;
        }

        // Controls
        syncControls() {
            const page = this.page();
            if (!page) return;
            for (const input of page.querySelectorAll('input[name="status-interval"]')) input.checked = Number(input.value) === this.interval;
            for (const button of page.querySelectorAll('[data-status-pause]')) {
                button.setAttribute('aria-pressed', String(this.paused));
                button.textContent = this.paused ? '再開' : '一時停止';
            }
        }

        connectionState() {
            if (this.paused) return 'paused';
            if (document.hidden) return 'hidden';
            if (this.error) return 'error';
            return this.data ? 'live' : 'loading';
        }

        // Rendering
        render() {
            const page = this.page();
            if (!page) return;
            this.renderConnection();
            if (!this.data) return;
            // The bindings come first: they set the keys of the charts in list items.
            this.binding.render(page, this.data);
            for (const element of page.querySelectorAll('[data-status-chart]')) this.renderChart(element);
        }

        renderConnection() {
            const page = this.page();
            if (!page) return;
            const state = this.connectionState();
            for (const element of page.querySelectorAll('[data-status-connection]')) {
                element.setAttribute('data-status-connection', state);
                const label = element.querySelector('[data-status-connection-text]');
                const text = state === 'error' ? `${StatusDashboard.CONNECTION_TEXT.error} (${this.error})` : StatusDashboard.CONNECTION_TEXT[state];
                if (label && label.textContent !== text) label.textContent = text;
            }
            if (this.data) {
                for (const element of page.querySelectorAll('[data-status-updated]')) {
                    const time = new Date(this.data.client.updated);
                    element.dateTime = time.toISOString();
                    element.textContent = time.toLocaleTimeString(StatusFormat.LOCALE);
                }
            }
        }

        renderChart(element) {
            const keys = element.getAttribute('data-status-chart').split(/\s+/).filter(Boolean);
            const max = Number(element.getAttribute('data-chart-max'));
            const top = window.nercone.Chart.draw(element, keys.map(key => this.history.get(key) ?? []), {
                max:    max > 0 ? max : null,
                length: this.options.historyLength
            });

            const scale = element.querySelector('.chart-scale');
            if (scale) {
                const text = top > 0 && !(max > 0) ? `最大 ${this.binding.format(top, element.getAttribute('data-format'))}` : '';
                if (scale.textContent !== text) scale.textContent = text;
            }
        }
    }

    window.nercone.StatusDashboard = StatusDashboard;
    window.nercone.register('status-dashboard', new StatusDashboard());
})();
