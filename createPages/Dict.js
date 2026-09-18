function hide_show_words() {
    classes_to_adjust = ['wordLine','lemmaLine','vRef'];
    other_classes_to_adjust = ['LVVerseText','RVVerseText'];
    let btn = document.getElementById('wordsButton');
    if (btn.style.backgroundColor === 'orange') {
        for (let cl of classes_to_adjust) {
            let elements_to_adjust = document.getElementsByClassName(cl);
            for (let i=0; i<elements_to_adjust.length; i++) {
                elements_to_adjust[i].style.display = 'revert';
                }
        }
        for (let cl of other_classes_to_adjust) {
            let elements_to_adjust = document.getElementsByClassName(cl);
            for (let i=0; i<elements_to_adjust.length; i++) {
                elements_to_adjust[i].style.marginTop = null; // Seems to make it use the CSS again
                elements_to_adjust[i].style.marginBottom = null; // Seems to make it use the CSS again
                elements_to_adjust[i].style.marginLeft = null; // Seems to make it use the CSS again
                elements_to_adjust[i].style.fontSize = null; // Seems to make it use the CSS again
                }
        }
        btn.textContent = btn.textContent.replace('Show', 'Hide');
        btn.style.backgroundColor = null; // Seems to make it use the CSS again
    } else {
        for (let cl of classes_to_adjust) {
            let elements_to_adjust = document.getElementsByClassName(cl);
            for (let i=0; i<elements_to_adjust.length; i++) {
                elements_to_adjust[i].style.display = 'none';
                }
        }
        for (let cl of other_classes_to_adjust) {
            let elements_to_adjust = document.getElementsByClassName(cl);
            for (let i=0; i<elements_to_adjust.length; i++) {
                elements_to_adjust[i].style.marginTop = cl==='LVVerseText' ? '1em' : '0.2em';
                elements_to_adjust[i].style.marginBottom = cl==='LVVerseText' ? '0.2em' : '1em';
                elements_to_adjust[i].style.marginLeft = '0';
                elements_to_adjust[i].style.fontSize = '1em';
                }
        }
        btn.textContent = btn.textContent.replace('Hide', 'Show');
        btn.style.backgroundColor = 'orange';
    }
}

function hide_show_verses() {
    classes_to_adjust = ['LVVerseText','RVVerseText'];
    let btn = document.getElementById('versesButton');
    let cbtn = document.getElementById('coloursButton');
    if (btn.textContent === 'Hide verses') {
        for (let cl of classes_to_adjust) {
            let elements_to_adjust = document.getElementsByClassName(cl);
            for (let i=0; i<elements_to_adjust.length; i++) {
                elements_to_adjust[i].style.display = 'none';
                }
        }
        btn.textContent = 'Show verses';
        btn.style.backgroundColor = 'orange';
        cbtn.style.display = 'none';
    } else {
        for (let cl of classes_to_adjust) {
            let elements_to_adjust = document.getElementsByClassName(cl);
            for (let i=0; i<elements_to_adjust.length; i++) {
                elements_to_adjust[i].style.display = 'revert';
                }
        }
        btn.textContent = 'Hide verses';
        btn.style.backgroundColor = null; // Seems to make it use the CSS again
        cbtn.style.display = 'revert';
    }
}

function hide_show_colours() {
    if (window.OBDSettings) {
        // theme.js owns the state: the settings panel, the CSS (data-par-colours)
        // and this button all agree and persist across pages and sessions.
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
    var btn = document.getElementById('coloursButton');
    if (window.OBDSettings) {
        // theme.js + common.css handle the spans via data-par-colours; here we
        // just mirror the state onto the button as before.
        if (btn) {
            btn.style.backgroundColor = 'orange';
            btn.textContent = 'Show verse colours';
        }
        return;
    }
    var classes_to_adjust = ['.grkNom','.grkAcc','.grkGen','.grkDat', '.grkVoc','.grkVrb','.grkNeg', '.hebVrb','.hebNeg','.hebEl','.hebYhwh','.noLinkYet'];
    for (let cl of classes_to_adjust) {
        var elements = document.querySelectorAll(cl);
        for (var i=0; i<elements.length; i++){
            elements[i].style.backgroundColor = 'white'; // What if we wanted a dark mode ???
            if (cl==='.noLinkYet') elements[i].style.color = 'black';
        }
    }
    if (btn) {
        btn.style.backgroundColor = 'orange';
        btn.textContent = 'Show verse colours';
    }
}

function show_grammatical_colours() {
    var btn = document.getElementById('coloursButton');
    if (window.OBDSettings) {
        // Removes the orange button highlight; the CSS data-par-colours
        // attribute is cleared by theme.js, restoring the backgrounds.
        if (btn) {
            btn.style.backgroundColor = null;
            btn.textContent = 'Hide verse colours';
        }
        return;
    }
    var classes_to_adjust = ['.grkNom','.grkAcc','.grkGen','.grkDat', '.grkVoc','.grkVrb','.grkNeg', '.hebVrb','.hebNeg','.hebEl','.hebYhwh','.noLinkYet'];
    for (let cl of classes_to_adjust) {
        var elements = document.querySelectorAll(cl);
        for (var i=0; i<elements.length; i++){
            elements[i].style.backgroundColor = null; // Seems to make it use the CSS again
            if (cl==='.noLinkYet') elements[i].style.color = 'white';
        }
    }
    if (btn) {
        btn.style.backgroundColor = null;
        btn.textContent = 'Hide verse colours';
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
