// SPDX-License-Identifier: CC0-1.0
//
// Adapted from https://ralzohairi.medium.com/adding-custom-keyboard-shortcuts-to-your-website-b4151fda2e7a
//  and from https://stackoverflow.com/questions/53192433/how-to-detect-swipe-in-javascript
//
// CHANGELOG:
//  2026-10-17 Require deliberate horizontal swipes and preserve vertical scrolling.
//  2026-11-01 Reset chapter/verse anchors when navigating, retaining version selections.
//  2026-11-01 Let readers use selection controls without activating page shortcuts.
// Last modified: 2026-11-01

// Distances are CSS pixels, independent of the phone's screen density.
const SWIPE_MIN_DISTANCE = 80;
const SWIPE_HORIZONTAL_RATIO = 2;
const SWIPE_SCROLL_LOCK_DISTANCE = 12;

var initialX = null;
var initialY = null;
const container = document.querySelector(".container");
// console.log(`${typeof container} container=${container}`);

if (container != null) {
    container.addEventListener("touchstart", startTouch, false);
    container.addEventListener("touchmove", moveTouch, { passive: false });
    container.addEventListener("touchend", resetTouch, false);
    container.addEventListener("touchcancel", resetTouch, false);
}

function startTouch(e) {
    // Pinching or any other multi-finger gesture must not change pages.
    if (e.touches.length !== 1) {
        resetTouch();
        return;
    }
    initialX = e.touches[0].clientX;
    initialY = e.touches[0].clientY;
};

function resetTouch() {
    initialX = null;
    initialY = null;
};

function moveTouch(e) {
    if (e.touches.length !== 1) {
        resetTouch();
        return;
    }
    if (initialX === null || initialY === null) {
        return;
    }

    var currentX = e.touches[0].clientX;
    var currentY = e.touches[0].clientY;

    var diffX = initialX - currentX;
    var diffY = initialY - currentY;
    var distanceX = Math.abs(diffX);
    var distanceY = Math.abs(diffY);

    // Once vertical or diagonal scrolling starts, ignore sideways drift until the next touch.
    if (distanceY >= SWIPE_SCROLL_LOCK_DISTANCE && distanceX < distanceY * SWIPE_HORIZONTAL_RATIO) {
        resetTouch();
        return;
    }

    // Keep measuring small movements, but allow the browser to scroll normally.
    if (distanceX < SWIPE_MIN_DISTANCE || distanceX < distanceY * SWIPE_HORIZONTAL_RATIO) {
        return;
    }

    // A rightward swipe goes back; a leftward swipe goes forward. Only once per touch.
    resetTouch();
    if (e.cancelable) {
        e.preventDefault();
    }
    handleChange( diffX < 0 ? 'Previous' : 'Next' );
};

// Keep track of clicked keys
var isKeyPressed = {
    'n': false,
    'p': false,
 // ... Other keys to check for custom key combinations
};


function handleChange( direction ) {
    // direction must be "Previous" or "Next"
    let aLink = document.querySelector(`a[title^="${direction} "]`) // Finds next anchor with title BEGINNING WITH the given string
    if (aLink != null) {
        const aLinkStr = aLink.getAttribute('href');
        const current = window.location.href;
        // Something was going wrong here (when pages load slowly) and ending up with multiple # parts
        if ((current.match(/#/g)||[]).length===1) {
            const fragment = current.substring(current.indexOf('#'));
            // Chapter/verse references belong to the current page. Version selections
            // such as #RV or #OET-LV can still be followed across parallel pages.
            const targetFragment = ['#chLst', '#vsLst'].includes(fragment) || /^#(?:C\d|V\d)/.test(fragment)
                ? '#Top' : fragment;
            // Replace the whole old fragment, which need not be four characters long.
            aLink.setAttribute('href', `${aLinkStr.split('#')[0]}${targetFragment}`);
        }
        aLink.click();
    }
}

document.onkeydown = (keyDownEvent) => {

    // Choosing a chapter/verse or typing must not also turn the Bible page.
    if (keyDownEvent.target?.closest('input, select, textarea, [contenteditable="true"]'))
        return;

    //Prevent default key actions, if desired
    // keyDownEvent.preventDefault();

    if (keyDownEvent.ctrlKey || keyDownEvent.altKey || keyDownEvent.metaKey || keyDownEvent.shiftKey)
        return;

    // Track key click
    isKeyPressed[keyDownEvent.key] = true;

    // Back/Previous uses first <a title="Previous something..." link
    if (isKeyPressed['p']
        || isKeyPressed['b']
        || isKeyPressed['ArrowLeft']) {
            handleChange( 'Previous' );
    }
    // Forward/Next uses first <a title="Next something..." link
    else if (isKeyPressed['n']
        || isKeyPressed['f']
        || isKeyPressed['ArrowRight']) {
            handleChange( 'Next' );
    };
    // else {
    //     console.log( `Other keyDown=${keyDownEvent.key}` );
    // };

    // Check described custom shortcut
    // if (isKeyPressed['a'] && isKeyPressed['b']) {} //for example we want to check if a and b are clicked at the same time
    //do something as custom shortcut (a & b) is clicked
};

document.onkeyup = (keyUpEvent) => {

    // Prevent default key actions, if desired
    // keyUpEvent.preventDefault();

    // Track key release
    isKeyPressed[keyUpEvent.key] = false;
};
