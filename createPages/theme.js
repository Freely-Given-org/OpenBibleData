// theme.js -- Site settings: colour scheme, verse-number position, text size,
// and the colour of Jesus'-words spans.
//
// All settings are independent and combine freely (non-exclusive), unlike the
// old Dropdown which forced a choice between "Left verse nums" and "Large
// print". Each is stored as one field of a JSON object:
//
//   * theme   "system" | "light" | "dark"   -- colour scheme (data-theme)
//   * verses  "inline" | "left"             -- verse numbers in the text or
//                                              in a left gutter (data-verses)
//   * size    "standard" | "large" | "xlarge"
//                                           -- normal, large-print, or extra
//                                              large-print text
//                                              (data-size="large"/"xlarge")
//   * wj      "brown" | "red" | "off"       -- colour of the span.wj elements
//                                              that mark Jesus'/Yeshua's words
//                                              (data-wj="red"/"off" -- absent
//                                               means the default brown)
//
// The object persists in localStorage under key `obd-settings` (migrating the
// earlier separate `obd-theme` / `obd-theme-layout` keys). Before first paint
// the resolved values are applied as data-* attributes on <html> so there is
// no flash of the wrong theme. A single "Settings" button in the top line
// (replacing the old Dark/Light toggle + theme dropdown) opens an in-page
// settings panel built by this script on DOMContentLoaded; every option
// applies immediately and is remembered on the device until "Set to defaults"
// (or "Reset") is used.
//
// common.css reads the data-* attributes to restyle the page. Controls in the
// panel are wired up only after the body exists, but the attributes themselves
// are applied before paint (this script runs synchronously in <head>).

(function () {
    'use strict';

    var SETTINGS_KEY = 'obd-settings';
    var LEGACY_THEME_KEY = 'obd-theme';
    var LEGACY_LAYOUT_KEY = 'obd-theme-layout';

    var DEFAULTS = {
        theme: 'system',   // system | light | dark
        verses: 'inline',  // inline  | left
        size: 'standard',  // standard| large | xlarge
        wj: 'brown'        // brown   | red | off
    };
    var ALLOWED = {
        theme: { system: true, light: true, dark: true },
        verses: { inline: true, left: true },
        size: { standard: true, large: true, xlarge: true },
        wj: { brown: true, red: true, off: true }
    };

    var settings = null; // merged, validated settings object
    var panel = null;    // the settings panel element (built at DOMContentLoaded)

    // ---- Storage ----------------------------------------------------------

    function readStored() {
        try {
            var raw = localStorage.getItem(SETTINGS_KEY);
            if (!raw) return {};
            var parsed = JSON.parse(raw);
            if (parsed && typeof parsed === 'object') return parsed;
        } catch (e) { /* localStorage unavailable or corrupt JSON */ }
        return {};
    }

    function settingsFromStorage() {
        var stored = readStored();
        var migrated = false;
        // Migrate the old independent keys if the new key has no value yet.
        if (stored.theme === undefined) {
            try {
                var oldTheme = localStorage.getItem(LEGACY_THEME_KEY);
                if (oldTheme === 'dark' || oldTheme === 'light') {
                    stored.theme = oldTheme;
                    migrated = true;
                }
            } catch (e) { /* ignore */ }
        }
        if (stored.verses === undefined || stored.size === undefined) {
            try {
                var oldLayout = localStorage.getItem(LEGACY_LAYOUT_KEY);
                if (oldLayout === 'left') {
                    if (stored.verses === undefined) { stored.verses = 'left'; migrated = true; }
                } else if (oldLayout === 'large') {
                    if (stored.size === undefined) { stored.size = 'large'; migrated = true; }
                }
            } catch (e) { /* ignore */ }
        }
        var out = {};
        for (var key in DEFAULTS) {
            out[key] = DEFAULTS[key];
            if (stored[key] !== undefined && ALLOWED[key][stored[key]]) {
                out[key] = stored[key];
            }
        }
        if (migrated) {
            try {
                localStorage.removeItem(LEGACY_THEME_KEY);
                localStorage.removeItem(LEGACY_LAYOUT_KEY);
                localStorage.setItem(SETTINGS_KEY, JSON.stringify(out));
            } catch (e) { /* ignore */ }
        }
        return out;
    }

    function writeSettings() {
        try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings)); } catch (e) { /* ignore */ }
    }

    function setSetting(key, value) {
        if (!ALLOWED[key] || !ALLOWED[key][value]) return;
        settings[key] = value;
        writeSettings();
        applySettings();
    }

    function resetSettings() {
        settings = {};
        for (var key in DEFAULTS) settings[key] = DEFAULTS[key];
        try {
            localStorage.removeItem(SETTINGS_KEY);
            localStorage.removeItem(LEGACY_THEME_KEY);
            localStorage.removeItem(LEGACY_LAYOUT_KEY);
        } catch (e) { /* ignore */ }
        applySettings();
    }

    // ---- Theme resolution --------------------------------------------------

    function systemTheme() {
        try {
            if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                return 'dark';
            }
        } catch (e) { /* matchMedia unavailable */ }
        return 'light';
    }

    // ---- Applying settings to <html> ----------------------------------------

    function applySettings() {
        var theme = settings.theme === 'system' ? systemTheme() : settings.theme;
        theme = theme === 'dark' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', theme);

        document.documentElement.setAttribute(
            'data-verses',
            settings.verses === 'left' ? 'left' : 'default'
        );
        if (settings.size === 'large' || settings.size === 'xlarge') {
            document.documentElement.setAttribute('data-size', settings.size);
        } else {
            document.documentElement.removeAttribute('data-size');
        }
        if (settings.wj === 'red' || settings.wj === 'off') {
            document.documentElement.setAttribute('data-wj', settings.wj);
        } else {
            document.documentElement.removeAttribute('data-wj');
        }
        syncPanel();
    }

    // In "system" mode the resolved light/dark state must track the OS.
    function watchSystemTheme() {
        if (!window.matchMedia) return;
        try {
            var mq = window.matchMedia('(prefers-color-scheme: dark)');
            var onChange = function () {
                if (settings && settings.theme === 'system') {
                    document.documentElement.setAttribute(
                        'data-theme',
                        systemTheme() === 'dark' ? 'dark' : 'light'
                    );
                }
            };
            if (mq.addEventListener) mq.addEventListener('change', onChange);
            else if (mq.addListener) mq.addListener(onChange); // legacy Safari
        } catch (e) { /* ignore */ }
    }

    // ---- Settings panel ------------------------------------------------------

    var panelHtml =
        '<div class="settingsPanel" id="obdSettingsPanel" role="dialog" aria-labelledby="obdSettingsTitle">' +
        '  <div class="settingsPanel-content">' +
        '    <h2 id="obdSettingsTitle">Settings</h2>' +
        '    <fieldset>' +
        '      <legend>Colour scheme</legend>' +
        '      <label><input type="radio" name="obd-setting-theme" value="system">Automatic (follow the computer)</label>' +
        '      <label><input type="radio" name="obd-setting-theme" value="light">Light</label>' +
        '      <label><input type="radio" name="obd-setting-theme" value="dark">Dark</label>' +
        '    </fieldset>' +
        '    <fieldset>' +
        '      <legend>Verse numbers</legend>' +
        '      <label><input type="radio" name="obd-setting-verses" value="inline">Inline (in the text)</label>' +
        '      <label><input type="radio" name="obd-setting-verses" value="left">Left of the text <span class="settingsNote">(on reading pages)</span></label>' +
        '    </fieldset>' +
        '    <fieldset>' +
        '      <legend>Text size</legend>' +
        '      <label><input type="radio" name="obd-setting-size" value="standard">Standard</label>' +
        '      <label><input type="radio" name="obd-setting-size" value="large">Large print</label>' +
        '      <label><input type="radio" name="obd-setting-size" value="xlarge">Extra large print</label>' +
        '    </fieldset>' +
        '    <fieldset>' +
        '      <legend>Jesus&#39; words</legend>' +
        '      <label><input type="radio" name="obd-setting-wj" value="brown">Brown (default)</label>' +
        '      <label><input type="radio" name="obd-setting-wj" value="red">Red</label>' +
        '      <label><input type="radio" name="obd-setting-wj" value="off">No special colour</label>' +
        '    </fieldset>' +
        '    <div class="settingsActions">' +
        '      <button type="button" id="obdSettingsReset" class="themeSettings">Set to defaults</button>' +
        '      <button type="button" id="obdSettingsDone" class="themeSettings">Done</button>' +
        '    </div>' +
        '  </div>' +
        '</div>';

    function buildPanel() {
        var holder = document.createElement('div');
        holder.innerHTML = panelHtml;
        panel = holder.firstElementChild;
        document.body.appendChild(panel);
        var radios = panel.querySelectorAll('input[type="radio"]');
        var i, radio;
        for (i = 0; i < radios.length; i++) {
            radios[i].addEventListener('change', onSettingChange);
        }
        var resetBtn = document.getElementById('obdSettingsReset');
        if (resetBtn) resetBtn.addEventListener('click', resetSettings);
        var doneBtn = document.getElementById('obdSettingsDone');
        if (doneBtn) doneBtn.addEventListener('click', closePanel);
        syncPanel();
    }

    function onSettingChange(event) {
        var radio = event.target;
        if (!radio.checked) return;
        setSetting(radio.name.replace('obd-setting-', ''), radio.value);
    }

    function syncPanel() {
        if (!panel) return;
        var radios = panel.querySelectorAll('input[type="radio"]');
        var i, radio;
        for (i = 0; i < radios.length; i++) {
            radio = radios[i];
            radio.checked = settings[radio.name.replace('obd-setting-', '')] === radio.value;
        }
    }

    function openPanel() {
        if (!panel) return;
        panel.setAttribute('data-open', 'true');
        var btn = document.getElementById('settingsButton');
        if (btn) btn.setAttribute('aria-expanded', 'true');
        var firstRadio = panel.querySelector('input[type="radio"]');
        if (firstRadio) firstRadio.focus();
    }

    function closePanel() {
        if (!panel) return;
        panel.removeAttribute('data-open');
        var btn = document.getElementById('settingsButton');
        if (btn) {
            btn.setAttribute('aria-expanded', 'false');
            btn.focus();
        }
    }

    // Close on Escape (or when clicking the dark overlay -- the panel itself,
    // as opposed to its content).
    function onKeyDown(event) {
        var key = event.key || String.fromCharCode(event.keyCode || 0);
        if (key === 'Escape' || event.keyCode === 27) closePanel();
    }
    function onPanelClick(event) {
        if (event.target === panel) closePanel();
    }

    // ---- Initialise -----------------------------------------------------------
    // Apply the saved (or default) settings before first paint.
    settings = settingsFromStorage();
    applySettings();

    // Wire up the panel once the body is parsed (this script runs in <head>).
    function wireUp() {
        buildPanel();
        var btn = document.getElementById('settingsButton');
        if (btn) {
            btn.addEventListener('click', function () {
                if (panel && panel.getAttribute('data-open') === 'true') {
                    closePanel();
                } else {
                    openPanel();
                }
            });
        }
        document.addEventListener('keydown', onKeyDown);
        if (panel) panel.addEventListener('click', onPanelClick);
        watchSystemTheme();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', wireUp);
    } else {
        wireUp();
    }
})();