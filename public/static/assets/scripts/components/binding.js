(() => {
    // Fills elements with values from data, such as a response of an API, by their attributes.
    // PATH is a dot-separated path into the data, such as "system.cpu.0.name", relative to the list item the element is in.
    //   data-bind="PATH" data-format="NAME"   sets the text to the value, formatted by the formatter NAME (default: text).
    //   data-bind-attr="NAME: PATH; ..."      sets the attribute NAME to the value as text, and removes it when the value is
    //                                         missing. The element gets data-bind-missing while any of them is missing.
    //   data-bind-show="PATH"                 shows the element only while the value is present.
    //   data-bind-hide="PATH"                 hides the element while the value is present.
    //   data-bind-list="PATH"                 repeats the first element of its <template> once for each item of an array.
    //                                         The paths inside an item are relative to the item.
    // A value is missing when it is null, undefined, or a number that is not finite. It is present when it is not missing,
    // not false, and not an empty array.
    class Binding {
        static DEFAULTS = {
            missing:       '—',
            locale:        undefined,
            formatters:    {},
            itemAttribute: 'data-bind-item'
        };
        static SELECTORS = ['[data-bind]', '[data-bind-attr]', '[data-bind-show]', '[data-bind-hide]', '[data-bind-list]'];

        constructor(options = {}) {
            this.options = { ...Binding.DEFAULTS, ...options };
            this.formatters = { ...Binding.formatters(this.options.locale), ...this.options.formatters };
        }

        // The formatters every Binding has. LOCALE is for Intl.NumberFormat and Date; by default, that of the browser.
        static formatters(locale) {
            const integer = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 });
            return {
                text:    (value) => Array.isArray(value) ? value.join(', ') : String(value),
                number:  (value) => integer.format(value),
                percent: (value) => `${(value * 100).toFixed(1)}%`,
                bytes:   (value) => Binding.scaled(value, 1024, ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB']),
                json:    (value) => JSON.stringify(value, null, 4),
                time:    (value) => new Date(value).toLocaleTimeString(locale),
                date:    (value) => new Date(value).toLocaleString(locale)
            };
        }

        // Divides VALUE by BASE while it reaches BASE, and adds the unit, such as "1.5 GiB". Values below BASE have no decimals.
        static scaled(value, base, units, digits = 1) {
            let index = 0;
            let scaled = Math.abs(value);
            while (scaled >= base && index < units.length - 1) {
                scaled /= base;
                index += 1;
            }
            return `${value < 0 ? '-' : ''}${scaled.toFixed(index === 0 ? 0 : digits)} ${units[index]}`;
        }

        static get(data, path) {
            if (path === null || path.trim() === '') return data;
            let value = data;
            for (const key of path.trim().split('.')) {
                if (value === null || value === undefined) return undefined;
                value = value[key];
            }
            return value;
        }

        static isMissing(value) {
            return value === null || value === undefined || (typeof value === 'number' && !Number.isFinite(value));
        }

        static isPresent(value) {
            if (Binding.isMissing(value) || value === false) return false;
            if (Array.isArray(value)) return value.length > 0;
            return true;
        }

        // "aria-valuenow: usage; data-state: up" -> [['aria-valuenow', 'usage'], ['data-state', 'up']]
        static parseAttributes(text) {
            return text.split(';').map(part => {
                const separator = part.indexOf(':');
                return separator < 0 ? null : [part.slice(0, separator).trim(), part.slice(separator + 1).trim()];
            }).filter(pair => pair && pair[0]);
        }

        format(value, name) {
            if (Binding.isMissing(value)) return this.options.missing;
            const formatter = this.formatters[name || 'text'];
            if (!formatter) throw new Error(`unknown formatter: ${name}`);
            return formatter(value);
        }

        // Fills ROOT and its descendants with DATA. Elements are changed only where their values changed.
        render(root, data) {
            this.renderScope(root, data, root.closest(`[${this.options.itemAttribute}]`));
        }

        // Fills the elements whose nearest list item is ITEM (null outside of lists) with DATA.
        renderScope(root, data, item) {
            const itemSelector = `[${this.options.itemAttribute}]`;
            const elements = [...root.querySelectorAll(Binding.SELECTORS.join(','))].filter(element => element.closest(itemSelector) === item);
            if (root.matches(Binding.SELECTORS.join(',')) && root.closest(itemSelector) === item) elements.unshift(root);

            for (const element of elements) {
                if (element.hasAttribute('data-bind')) {
                    const text = this.format(Binding.get(data, element.getAttribute('data-bind')), element.getAttribute('data-format'));
                    if (element.textContent !== text) element.textContent = text;
                }
                if (element.hasAttribute('data-bind-attr')) {
                    let missing = false;
                    for (const [name, path] of Binding.parseAttributes(element.getAttribute('data-bind-attr'))) {
                        const value = Binding.get(data, path);
                        if (Binding.isMissing(value)) {
                            missing = true;
                            element.removeAttribute(name);
                        } else if (element.getAttribute(name) !== String(value)) {
                            element.setAttribute(name, String(value));
                        }
                    }
                    element.toggleAttribute('data-bind-missing', missing);
                }
                if (element.hasAttribute('data-bind-show')) {
                    element.hidden = !Binding.isPresent(Binding.get(data, element.getAttribute('data-bind-show')));
                }
                if (element.hasAttribute('data-bind-hide')) {
                    element.hidden = Binding.isPresent(Binding.get(data, element.getAttribute('data-bind-hide')));
                }
                if (element.hasAttribute('data-bind-list')) {
                    this.renderList(element, Binding.get(data, element.getAttribute('data-bind-list')));
                }
            }
        }

        renderList(container, items) {
            const template = container.querySelector(':scope > template');
            const prototype = template?.content.firstElementChild;
            if (!prototype) return;
            const list = Array.isArray(items) ? items : [];
            const elements = [...container.children].filter(element => element.hasAttribute(this.options.itemAttribute));

            // Items are kept and filled again, so that only their changed values are touched.
            for (let index = elements.length; index < list.length; index += 1) {
                const element = prototype.cloneNode(true);
                element.setAttribute(this.options.itemAttribute, '');
                container.append(element);
                elements.push(element);
            }
            for (const element of elements.splice(list.length)) element.remove();

            elements.forEach((element, index) => this.renderScope(element, list[index], element));
        }
    }

    window.nercone.Binding = Binding;
})();
