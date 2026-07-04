(() => {
    const state = {
        config: null,
        attached: new Set(),
        selected: {},
        inserted: {},
        outsideClickAttached: false,
    };

    const css = `
    .jpta-panel {
        margin: 8px 0 12px;
        padding: 0;
        border: 1px solid var(--block-border-color, #4b5563);
        border-radius: 6px;
        background: #111827;
        color: var(--body-text-color, #f3f4f6);
        font: 13px/1.35 sans-serif;
        overflow: visible;
        position: relative;
        z-index: 50;
        width: 100%;
        flex: 0 0 100%;
        align-self: flex-start;
        box-sizing: border-box;
        height: auto !important;
        min-height: 0 !important;
    }
    .jpta-panel[open] {
        z-index: 10020;
    }
    .jpta-panel summary {
        display: flex;
        align-items: center;
        gap: 8px;
        min-height: 30px;
        padding: 6px 8px;
        cursor: pointer;
        color: var(--body-text-color-subdued, #9ca3af);
        font-size: 12px;
        font-weight: 700;
        user-select: none;
    }
    .jpta-panel summary::-webkit-details-marker {
        display: none;
    }
    .jpta-panel summary::before {
        content: ">";
        display: inline-block;
        width: 10px;
        transform: rotate(0deg);
        transition: transform 120ms ease;
    }
    .jpta-panel[open] summary::before {
        transform: rotate(90deg);
    }
    .jpta-body {
        display: none;
        position: absolute;
        z-index: 10021;
        top: calc(100% + 4px);
        left: 0;
        right: 0;
        max-height: min(360px, calc(100vh - 160px));
        overflow: auto;
        padding: 8px;
        border: 1px solid var(--block-border-color, #4b5563);
        border-radius: 6px;
        background: #0b1220;
        box-shadow: 0 18px 42px rgba(0, 0, 0, 0.72);
    }
    .jpta-panel[open] .jpta-body {
        display: block;
    }
    .jpta-top {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 7px;
    }
    .jpta-input {
        flex: 1 1 auto;
        min-width: 120px;
        height: 30px;
        padding: 3px 8px;
        border: 1px solid var(--input-border-color, #4b5563);
        border-radius: 5px;
        background: #1f2937 !important;
        color: var(--input-text-color, #f9fafb) !important;
        box-shadow: none;
        outline: none;
    }
    .jpta-input::placeholder {
        color: var(--input-placeholder-color, #8b95a5);
    }
    .jpta-search {
        flex: 0 0 auto;
        height: 30px;
        padding: 3px 10px;
        border: 1px solid var(--button-secondary-border-color, #4b5563);
        border-radius: 5px;
        background: var(--button-secondary-background-fill, #374151);
        color: var(--button-secondary-text-color, #f9fafb);
        cursor: pointer;
    }
    .jpta-section-title {
        margin: 5px 0 4px;
        color: var(--body-text-color-subdued, #9ca3af);
        font-size: 12px;
    }
    .jpta-list {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
    }
    .jpta-item {
        display: inline-flex;
        flex-direction: column;
        align-items: flex-start;
        gap: 1px;
        max-width: 220px;
        cursor: pointer;
        border: 1px solid var(--button-secondary-border-color, #4b5563);
        border-radius: 5px;
        padding: 4px 7px;
        background: #1f2937;
        color: var(--button-secondary-text-color, #f9fafb);
        text-align: left;
        line-height: 1.22;
        white-space: nowrap;
    }
    .jpta-item:hover,
    .jpta-item.selected {
        background: var(--button-primary-background-fill, #2563eb);
        color: var(--button-primary-text-color, #ffffff);
    }
    .jpta-main {
        display: inline-flex;
        align-items: baseline;
        max-width: 100%;
    }
    .jpta-tag {
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .jpta-count {
        margin-left: 5px;
        opacity: 0.68;
        font-size: 11px;
    }
    .jpta-ja {
        max-width: 190px;
        overflow: hidden;
        text-overflow: ellipsis;
        opacity: 0.72;
        font-size: 11px;
        font-weight: 400;
    }
    }`;

    function appRoot() {
        return typeof gradioApp === "function" ? gradioApp() : document;
    }

    function ensureStyle() {
        if (document.getElementById("jpta-style")) return;
        const style = document.createElement("style");
        style.id = "jpta-style";
        style.textContent = css;
        document.head.appendChild(style);
    }

    function attachOutsideClickHandler() {
        if (state.outsideClickAttached) return;
        state.outsideClickAttached = true;
        document.addEventListener("mousedown", (event) => {
            const openPanels = [...appRoot().querySelectorAll(".jpta-panel[open]")];
            if (!openPanels.length) return;
            openPanels.forEach((panel) => {
                if (!panel.contains(event.target)) {
                    panel.open = false;
                }
            });
        }, true);
    }

    async function fetchJson(url) {
        const separator = url.includes("?") ? "&" : "?";
        const response = await fetch(`${url}${separator}${Date.now()}`);
        if (!response.ok) {
            console.error(`JP Tag Assistant: ${url} returned ${response.status}`);
            return null;
        }
        return response.json();
    }

    async function loadConfig() {
        state.config = await fetchJson("jptagapi/v1/config") || {
            enable: true,
            maxResults: 32,
            relatedMaxResults: 24,
        };
    }

    function visibleTag(tag) {
        if (window.TAC_CFG?.replaceUnderscores) {
            return tag.replaceAll("_", " ");
        }
        return tag;
    }

    function promptArea(tab) {
        return appRoot().querySelector(`#${tab}_prompt textarea, textarea#${tab}_prompt`);
    }

    function negativeArea(tab) {
        return appRoot().querySelector(`#${tab}_neg_prompt textarea, textarea#${tab}_neg_prompt`);
    }

    function promptWrapper(area) {
        return area?.closest(".block") || area?.closest(".form") || area?.parentElement;
    }

    function settingsTabs(tab) {
        const settings = appRoot().querySelector(`#${tab}_settings`);
        return settings?.closest(".tabs") || null;
    }

    function placementAnchor(tab) {
        const prompt = promptArea(tab);
        const negative = negativeArea(tab);
        const start = negative || prompt;
        if (!start) return null;

        const tabs = settingsTabs(tab);
        if (tabs && tabs.parentElement) {
            return { element: tabs, mode: "before" };
        }

        let node = promptWrapper(start);
        while (node && node.parentElement && node !== appRoot()) {
            const parent = node.parentElement;
            if (prompt && negative && parent.contains(prompt) && parent.contains(negative)) {
                node = parent;
                continue;
            }
            const parentRect = parent.getBoundingClientRect();
            const startRect = start.getBoundingClientRect();
            const wrapsSameRow = parentRect.top <= startRect.top + 2 && parentRect.bottom >= startRect.bottom - 2;
            if (wrapsSameRow && parent.children.length <= 6) {
                node = parent;
                continue;
            }
            break;
        }

        return { element: node || promptWrapper(start), mode: "after" };
    }

    function insertTag(area, tag) {
        if (!area) return;
        const insert = visibleTag(tag);
        const start = area.selectionStart ?? area.value.length;
        const end = area.selectionEnd ?? start;
        const before = area.value.slice(0, start);
        const after = area.value.slice(end);
        const prefix = before.length && !/[\s,(]$/.test(before) ? ", " : "";
        const suffix = after.length && !/^\s*,/.test(after) ? ", " : "";
        area.value = `${before}${prefix}${insert}${suffix}${after}`;
        const caret = before.length + prefix.length + insert.length + suffix.length;
        area.focus();
        area.setSelectionRange(caret, caret);
        area.dispatchEvent(new Event("input", { bubbles: true }));
    }

    function removeTag(area, tag) {
        if (!area) return false;
        const insert = visibleTag(tag).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const pattern = new RegExp(`(^|,\\s*)${insert}(?=\\s*,|\\s*$)\\s*,?\\s*`);
        if (!pattern.test(area.value)) return false;
        area.value = area.value
            .replace(pattern, (match, prefix) => prefix && prefix.trim() ? prefix : "")
            .replace(/,\s*,+/g, ", ")
            .replace(/^\s*,\s*/, "")
            .replace(/\s*,\s*$/, "");
        area.focus();
        const caret = area.value.length;
        area.setSelectionRange(caret, caret);
        area.dispatchEvent(new Event("input", { bubbles: true }));
        return true;
    }

    function insertionKey(targetKind, tag) {
        return `${targetKind}:${tag}`;
    }

    function toggleTag(tab, targetKind, area, tag) {
        state.inserted[tab] ||= {};
        const key = insertionKey(targetKind, tag);
        if (state.inserted[tab][key] && removeTag(area, tag)) {
            delete state.inserted[tab][key];
            return false;
        }
        insertTag(area, tag);
        state.inserted[tab][key] = true;
        return true;
    }

    function createPanel(tab) {
        const panel = document.createElement("details");
        panel.className = "jpta-panel";
        panel.dataset.jptaTab = tab;
        panel.innerHTML = `
            <summary>JP Tag Assistant</summary>
            <div class="jpta-body">
            <div class="jpta-top">
                <input class="jpta-input" type="text" placeholder="日本語でタグ検索..." />
                <button class="jpta-search" type="button">Search</button>
            </div>
            <div class="jpta-section-title">Candidates</div>
            <div class="jpta-list jpta-results"></div>
            <div class="jpta-section-title">Related</div>
            <div class="jpta-list jpta-related"></div>
            </div>
        `;

        const input = panel.querySelector(".jpta-input");
        const search = panel.querySelector(".jpta-search");
        panel.addEventListener("toggle", () => {
            if (panel.open) input.focus();
        });
        search.addEventListener("click", () => runSearch(tab, panel));
        input.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                runSearch(tab, panel);
            }
        });
        input.addEventListener("input", () => {
            clearTimeout(input._jptaTimer);
            input._jptaTimer = setTimeout(() => runSearch(tab, panel), 220);
        });
        return panel;
    }

    function renderItems(container, tab, items) {
        container.textContent = "";
        if (!items.length) {
            return;
        }

        items.forEach((item) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "jpta-item";
            button.dataset.tag = item.tag;
            if (state.selected[tab] === item.tag) button.classList.add("selected");

            const main = document.createElement("span");
            main.className = "jpta-main";
            const tag = document.createElement("span");
            tag.className = "jpta-tag";
            tag.textContent = visibleTag(item.tag);
            main.appendChild(tag);

            if (item.count) {
                const count = document.createElement("span");
                count.className = "jpta-count";
                count.textContent = item.count;
                main.appendChild(count);
            }

            button.appendChild(main);
            if (item.labelJa) {
                const ja = document.createElement("span");
                ja.className = "jpta-ja";
                ja.textContent = item.labelJa;
                button.title = `${visibleTag(item.tag)}\n${item.labelJa}`;
                button.appendChild(ja);
            }

            button.addEventListener("mousedown", (event) => event.preventDefault());
            button.addEventListener("click", (event) => {
                const targetKind = event.shiftKey ? "negative" : "prompt";
                const target = targetKind === "negative" ? negativeArea(tab) : promptArea(tab);
                const inserted = toggleTag(tab, targetKind, target, item.tag);
                state.selected[tab] = item.tag;
                container.querySelectorAll(".jpta-item").forEach((el) => {
                    el.classList.toggle("selected", inserted && el.dataset.tag === item.tag);
                });
                loadRelated(tab, item.tag);
            });
            container.appendChild(button);
        });
    }

    async function runSearch(tab, panel) {
        if (!state.config?.enable) return;
        const query = panel.querySelector(".jpta-input").value.trim();
        const results = panel.querySelector(".jpta-results");
        if (!query) {
            renderItems(results, tab, []);
            return;
        }
        const limit = state.config.maxResults || 32;
        const data = await fetchJson(`jptagapi/v1/search?q=${encodeURIComponent(query)}&limit=${limit}`);
        renderItems(results, tab, data?.results || []);
    }

    async function loadRelated(tab, tag) {
        const panel = appRoot().querySelector(`.jpta-panel[data-jpta-tab="${tab}"]`);
        const related = panel?.querySelector(".jpta-related");
        if (!related) return;
        const limit = state.config.relatedMaxResults || 24;
        const data = await fetchJson(`jptagapi/v1/related?tag=${encodeURIComponent(tag)}&limit=${limit}`);
        renderItems(related, tab, data?.results || []);
    }

    function attachTab(tab) {
        if (state.attached.has(tab)) return;
        const anchor = placementAnchor(tab);
        if (!anchor) return;
        const existing = appRoot().querySelector(`.jpta-panel[data-jpta-tab="${tab}"]`);
        if (existing) {
            state.attached.add(tab);
            return;
        }
        const panel = createPanel(tab);
        anchor.element.insertAdjacentElement(anchor.mode === "before" ? "beforebegin" : "afterend", panel);
        state.attached.add(tab);
    }

    async function setup() {
        ensureStyle();
        attachOutsideClickHandler();
        if (!state.config) await loadConfig();
        if (!state.config?.enable) return;
        attachTab("txt2img");
        attachTab("img2img");
    }

    onUiUpdate(setup);
})();
