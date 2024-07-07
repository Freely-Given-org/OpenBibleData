// Adapted from https://ralzohairi.medium.com/adding-custom-keyboard-shortcuts-to-your-website-b4151fda2e7a

// Keep track of clicked keys
var isKeyPressed = {
    'n': false,
    'p': false,
 // ... Other keys to check for custom key combinations
};
 
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
        let aLink = document.querySelector('a[title^="Previous "]') // Finds title BEGINNING WITH the given string
        // console.log( `p=Previous aLink=${aLink}` );
        if (aLink != null) aLink.click();
    }
    // Forward/Next uses first <a title="Previous something..." link
    else if (isKeyPressed['n']
        || isKeyPressed['f']
        || isKeyPressed['ArrowRight']) {
        let aLink = document.querySelector('a[title^="Next "]') // Finds title BEGINNING WITH the given string
        // console.log( `n=Next aLink=${aLink}` );
        if (aLink != null) aLink.click();
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
