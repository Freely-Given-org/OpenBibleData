// theme.js -- Dark/Light mode toggle plus an independent "theme" dropdown.
//
// The two controls are entirely independent:
//
//   * The Dark/Light toggle switches a `data-theme` attribute ("light"/"dark")
//     on <html>. common.css uses it to flip CSS custom properties. It persists
//     in localStorage under key `obd-theme`. On first visit (no saved choice)
//     it follows the operating system preference (prefers-color-scheme).
//
//   * The "theme" dropdown selects one of three global themes via `data-verses`
//     and `data-size` attributes on <html>:
//        "default"        -> normal verse layout, normal size
//        "left"           -> verse numbers moved to the left margin
//                            (data-verses="left"; verse page types only)
//        "large"          -> "Large print" theme (data-size="large"; all pages)
//                            big fonts get slightly larger, small fonts get an
//                            extra size boost. Scaled entirely by common.css.
//     It persists under localStorage key `obd-theme-layout` and is unaffected
//     by light/dark mode.
//
// The <script> is included in <head> so both attributes are applied before the
// page paints (avoiding a flash of the wrong theme). DOM wiring for the
// controls waits for DOMContentLoaded because they live in the body which
// isn't parsed yet when this script runs.

(function () {
    'use strict';

    var THEME_KEY = 'obd-theme';
    var LAYOUT_KEY = 'obd-theme-layout';
    var THEMES = { 'default': true, 'left': true, 'large': true };

    // ---- Dark / Light mode ---------------------------------------------------

    function savedTheme() {
        try {
            var t = localStorage.getItem(THEME_KEY);
            if (t === 'dark' || t === 'light') return t;
        } catch (e) { /* localStorage unavailable */ }
        return null;
    }

    function systemTheme() {
        try {
            if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                return 'dark';
            }
        } catch (e) { /* matchMedia unavailable */ }
        return 'light';
    }

    function currentTheme() {
        var t = savedTheme();
        if (t !== null) return t;
        return systemTheme();
    }

    function applyTheme(theme) {
        theme = theme === 'dark' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', theme);
        // The button shows the *current* mode; aria-pressed reflects it and the
        // title states the action that a click performs (switching to the other).
        var btn = document.getElementById('themeToggle');
        if (btn) {
            btn.textContent = theme === 'dark' ? 'Dark' : 'Light';
            btn.setAttribute('aria-pressed', theme === 'dark' ? 'true' : 'false');
            btn.setAttribute('title', theme === 'dark'
                ? 'Switch to light mode'
                : 'Switch to dark mode');
        }
    }

    function toggleTheme() {
        var next = currentTheme() === 'dark' ? 'light' : 'dark';
        try { localStorage.setItem(THEME_KEY, next); } catch (e) { /* ignore */ }
        applyTheme(next);
    }

    // ---- Theme dropdown (Default / Left verse nums / Large print) ------------

    function savedThemeChoice() {
        try {
            var l = localStorage.getItem(LAYOUT_KEY);
            if (l && THEMES[l]) return l;
        } catch (e) { /* localStorage unavailable */ }
        return 'default';
    }

    function applyThemeChoice(choice) {
        choice = THEMES[choice] ? choice : 'default';
        // Verse-number layout: only "left" moves them into the margin.
        var verses = choice === 'left' ? 'left' : 'default';
        document.documentElement.setAttribute('data-verses', verses);
        // Font size: only "large" switches on the Large print theme.
        if (choice === 'large') {
            document.documentElement.setAttribute('data-size', 'large');
        } else {
            document.documentElement.removeAttribute('data-size');
        }
        var sel = document.getElementById('themeSelect');
        if (sel) {
            sel.value = choice;
        }
    }

    function onThemeChoiceChange() {
        var sel = document.getElementById('themeSelect');
        if (!sel) return;
        var choice = sel.value;
        try { localStorage.setItem(LAYOUT_KEY, choice); } catch (e) { /* ignore */ }
        applyThemeChoice(choice);
    }

    // ---- Initialise (before first paint) --------------------------------------

    applyTheme(currentTheme());
    applyThemeChoice(savedThemeChoice());

    // ---- Wire up the controls once the body is parsed -------------------------

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', wireUp);
    } else {
        wireUp();
    }

    function wireUp() {
        var btn = document.getElementById('themeToggle');
        if (btn) {
            btn.addEventListener('click', toggleTheme);
        }
        var sel = document.getElementById('themeSelect');
        if (sel) {
            sel.addEventListener('change', onThemeChoiceChange);
        }
    }
})();
