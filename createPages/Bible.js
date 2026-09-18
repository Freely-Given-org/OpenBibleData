function hide_show_marks() {
    classes_to_adjust = ['ul', 'dom', 'untr'];
    let btn = document.getElementById('marksButton');
    if (btn.textContent === 'Hide marks') {
        for (let cl of classes_to_adjust) {
            let elements_to_adjust = document.getElementsByClassName(cl);
            for (let i=0; i<elements_to_adjust.length; i++) {
                if (cl == 'ul') elements_to_adjust[i].style.color = 'white'; // We don't want to lose the space
                else if (cl == 'untr') elements_to_adjust[i].style.textDecoration = 'none'; // Remove the strikeout
                // else elements_to_adjust[i].style.visibility = 'hidden';
                else elements_to_adjust[i].style.display = 'none';
                }
        }
        btn.textContent = 'Show marks';
    } else {
        for (let cl of classes_to_adjust) {
            let elements_to_adjust = document.getElementsByClassName(cl);
            for (let i=0; i<elements_to_adjust.length; i++) {
                if (cl == 'ul') elements_to_adjust[i].style.color = 'darkGrey'; // Should match the span.ul color in the CSS
                else if (cl == 'untr') elements_to_adjust[i].style.textDecoration = 'line-through';
                // else elements_to_adjust[i].style.visibility = 'visible';
                else elements_to_adjust[i].style.display = 'revert';
                }
        }
        btn.textContent = 'Hide marks';
    }
}

function hide_show_fields() {
    if (window.OBDSettings) {
        // theme.js owns the state: the settings panel, the CSS (data-par-fields)
        // and these buttons all agree and persist across pages and sessions.
        OBDSettings.set('parFields', OBDSettings.get('parFields') === 'hide' ? 'show' : 'hide');
        return;
    }
    // Legacy fallback for pages without theme.js: toggle inline, as before.
    let divs = document.getElementsByClassName('hideables');
    console.assert(divs.length === 1); // We only expect one
    let div = divs[0];
    let topBtn = document.getElementById('TopFieldsButton');
    let btmBtn = document.getElementById('BottomNavsFieldsButton');
    if (div.style.display==='' || div.style.display==='revert') {
        div.style.display = 'none';
        if (topBtn) topBtn.title = 'Show historical translations'; if (btmBtn) btmBtn.title = 'Show historical translations';
        if (topBtn) topBtn.style.backgroundColor = 'mistyRose'; if (btmBtn) btmBtn.style.backgroundColor = 'mistyRose';
    } else {
        div.style.display = 'revert';
        if (topBtn) topBtn.title = 'Hide historical translations'; if (btmBtn) btmBtn.title = 'Hide historical translations';
        if (topBtn) topBtn.style.backgroundColor = null; if (btmBtn) btmBtn.style.backgroundColor = null;
    }
}

// The transliteration / modernised-spelling classes actually generated on the
// parallel verse pages (see createParallelVersePages.py). Mirrors the list in
// common.css's html[data-par-translit="hide"] selector.
const transliteration_classes = ['SR-GNT_trans','UGNT_trans','SBL-GNT_trans','TC-GNT_trans','RP-GNT_trans',
    'BrLXX_trans','UHB_trans','Luth_trans','ClVg_trans',
    'Wycl_mod','TNT_mod','Cvdl_mod','Gnva_mod','Bshps_mod','KJB-1611_mod','KJB-1769_mod','RV_mod'];

function hide_show_transliterations() {
    if (window.OBDSettings) {
        OBDSettings.set('parTranslit', OBDSettings.get('parTranslit') === 'hide' ? 'show' : 'hide');
        return;
    }
    // Legacy fallback for pages without theme.js: toggle inline, as before.
    let topBtn = document.getElementById('TopTransliterationsButton');
    let btmBtn = document.getElementById('BottomNavsTransliterationsButton');
    if (topBtn && topBtn.textContent === 'ⱦ') {
        for (let cl of transliteration_classes) {
            let elements_to_adjust = document.getElementsByClassName(cl);
            for (let i=0; i<elements_to_adjust.length; i++) {
                elements_to_adjust[i].style.display = 'none';
                }
            }
        if (topBtn) topBtn.textContent = 't'; if (btmBtn) btmBtn.textContent = 't';
        if (topBtn) topBtn.title = 'Show transliterations, etc.'; if (btmBtn) btmBtn.title = 'Show transliterations, etc.';
        if (topBtn) topBtn.style.backgroundColor = 'lightSkyBlue'; if (btmBtn) btmBtn.style.backgroundColor = 'lightSkyBlue';
        } else {
            for (let cl of transliteration_classes) {
                let elements_to_adjust = document.getElementsByClassName(cl);
                for (let i=0; i<elements_to_adjust.length; i++) {
                    elements_to_adjust[i].style.display = 'revert';
                }
            }
        if (topBtn) topBtn.textContent = 'ⱦ'; if (btmBtn) btmBtn.textContent = 'ⱦ';
        if (topBtn) topBtn.title = 'Hide transliterations, etc.'; if (btmBtn) btmBtn.title = 'Hide transliterations, etc.';
        if (topBtn) topBtn.style.backgroundColor = null; if (btmBtn) btmBtn.style.backgroundColor = null;
    }
}

function hide_show_colours() {
    if (window.OBDSettings) {
        OBDSettings.set('parColours', colours_hidden() ? 'shown' : 'hidden');
        return;
    }
    // Legacy fallback for pages without theme.js: toggle inline, as before.
    if (colours_hidden()) {
        show_grammatical_colours();
        remember_colours_shown();
    } else { // it wasn't already coloured
        hide_grammatical_colours();
        remember_colours_hidden();
    }
}

// Was the grammatical colouring turned off? Prefer the shared settings object
// managed by theme.js (localStorage key obd-settings, mirroring the settings
// panel); if that is unavailable, fall back to the older obd-colours key and
// then to the button's own highlighted state.
function colours_hidden() {
    if (window.OBDSettings) {
        var shared = OBDSettings.get('parColours');
        if (shared === 'hidden' || shared === 'shown') return shared === 'hidden';
    }
    try {
        var saved = localStorage.getItem('obd-colours');
        if (saved === 'hidden' || saved === 'shown') return saved === 'hidden';
    } catch (e) { /* local storage unavailable -- fall back below */ }
    var btn = document.getElementById('coloursButton');
    return !!(btn && btn.style.backgroundColor === 'orange');
}

function hide_grammatical_colours() {
    if (window.OBDSettings) {
        // theme.js + common.css handle the spans via data-par-colours; here we
        // just mirror the state onto the button as before.
        var btn = document.getElementById('coloursButton');
        if (btn) {
            btn.style.backgroundColor = 'orange';
            btn.title = 'Show grammatical colours above';
        }
        return;
    }
    var classes_to_adjust = ['.grkNom','.grkAcc','.grkGen','.grkDat', '.grkVoc','.grkVrb','.grkNeg', '.hebVrb','.hebNeg','.hebEl','.hebYhwh'];
    for (let cl of classes_to_adjust) {
        var elements = document.querySelectorAll(cl);
        for (var i=0; i<elements.length; i++){
            elements[i].style.backgroundColor = 'white'; // What if we wanted a dark mode ???
        }
    }
    var btn = document.getElementById('coloursButton');
    if (btn) {
        btn.style.backgroundColor = 'orange';
        btn.title = 'Show grammatical colours above';
    }
}

function show_grammatical_colours() {
    if (window.OBDSettings) {
        // Removes the orange button highlight; the CSS data-par-colours
        // attribute is cleared by theme.js, restoring the backgrounds.
        var btn = document.getElementById('coloursButton');
        if (btn) {
            btn.style.backgroundColor = null;
            btn.title = 'Hide grammatical colours above';
        }
        return;
    }
    var classes_to_adjust = ['.grkNom','.grkAcc','.grkGen','.grkDat', '.grkVoc','.grkVrb','.grkNeg', '.hebVrb','.hebNeg','.hebEl','.hebYhwh'];
    for (let cl of classes_to_adjust) {
        var elements = document.querySelectorAll(cl);
        for (var i=0; i<elements.length; i++){
            elements[i].style.backgroundColor = null; // Seems to make it use the CSS again
        }
    }
    var btn = document.getElementById('coloursButton');
    if (btn) {
        btn.style.backgroundColor = null;
        btn.title = 'Hide grammatical colours above';
    }
}

function remember_colours_hidden() {
    try { localStorage.setItem('obd-colours', 'hidden'); } catch (e) { /* ignore */ }
}

function remember_colours_shown() {
    try { localStorage.removeItem('obd-colours'); } catch (e) { /* ignore */ }
}

// Restore the reader's saved colour preference once the page has been parsed.
function restore_colours() {
    if (colours_hidden()) hide_grammatical_colours();
}
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', restore_colours);
} else {
    restore_colours();
}
