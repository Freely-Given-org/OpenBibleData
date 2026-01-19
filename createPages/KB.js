// Adapted from https://ralzohairi.medium.com/adding-custom-keyboard-shortcuts-to-your-website-b4151fda2e7a
//  and from https://stackoverflow.com/questions/53192433/how-to-detect-swipe-in-javascript
//
// Last modified by RJH: 2026-01-17

var initialX = null;
var initialY = null;
const container = document.querySelector(".container");
// console.log(`${typeof container} container=${container}`);

if (container != null) {
    container.addEventListener("touchstart", startTouch, false);
    container.addEventListener("touchmove", moveTouch, false);
}

function startTouch(e) {
    initialX = e.touches[0].clientX;
    initialY = e.touches[0].clientY;
};

function moveTouch(e) {
    if (initialX === null) {
        return;
    }
    if (initialY === null) {
        return;
    }

    var currentX = e.touches[0].clientX;
    var currentY = e.touches[0].clientY;

    var diffX = initialX - currentX;
    var diffY = initialY - currentY;

  // Swipe Up / Down / Left / Right
  if (Math.abs(diffX) > Math.abs(diffY)) {
    // sliding horizontally
    if (diffX < 0) {
      // swiped left
      // console.log("swiped left");
      handleChange( 'Previous' );
    } else {
      // swiped right
      // console.log("swiped right");
      handleChange( 'Next' );
    }
  // } else {
  //   // sliding vertically
  //   if (diffY > 0) {
  //     // swiped up
  //     console.log("swiped up");
  //   } else {
  //     // swiped down
  //     console.log("swiped down");
  //   }
  }

  initialX = null;
  initialY = null;

  e.preventDefault();
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
    // console.log( `${direction} aLink=${aLink}` );
    // console.log( `aLink type=${typeof aLink}` );
    if (aLink != null) {
        aLinkStr = aLink.getAttribute('href');
        // console.log( `${direction} aLinkstr=${aLinkStr}` );
        // console.log( `aLinkStr type=${typeof aLinkStr}` );
        current = window.location.href;
        // console.log( `Current=${current} ${current.endsWith('#Top')}` );
        // Something was going wrong here (when pages load slowly) and ending up with multiple # parts
        // if (current.includes('#') && !current.endsWith('#Top')) {
        if ((current.match(/#/g)||[]).length===1 && !current.endsWith('#Top')) {
            ix = current.indexOf('#');
            fragment = current.substring(ix);
            aLinkStr = `{aLinkStr.substring(0, aLinkStr.length-4)}{fragment==="#vsLst"? "top" : fragment}`;
            // console.log( `aLinkStr=${aLinkStr}` );
            aLink.setAttribute('href', aLinkStr);
        }
        aLink.click();
    }
}

document.onkeydown = (keyDownEvent) => {

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

// window.onload = function() {
//     // var userImage = document.getElementById('imageOtherUser');
//     var hangoutButton = document.getElementById("hangoutButtonId");
//     // userImage.onclick = function() {
//     //    hangoutButton.click(); // this will trigger the click event
//     // };
// };
