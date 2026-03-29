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
    classes_to_adjust = ['.grkNom','.grkAcc','.grkGen','.grkDat', '.grkVoc','.grkVrb','.grkNeg', '.hebVrb','.hebNeg','.hebEl','.hebYhwh','.noLinkYet'];
    let btn = document.getElementById('coloursButton');
    if (btn.style.backgroundColor === 'orange') {
        for (let cl of classes_to_adjust) {
            var elements = document.querySelectorAll(cl);
            for(var i=0; i<elements.length; i++){
                elements[i].style.backgroundColor = null; // Seems to make it use the CSS again
                if (cl==='.noLinkYet') elements[i].style.color = 'white';
            }
        }
        btn.style.backgroundColor = null;
        btn.textContent = 'Hide verse colours';
    } else { // it wasn't already coloured
        for (let cl of classes_to_adjust) {
            var elements = document.querySelectorAll(cl);
            for(var i=0; i<elements.length; i++){
                elements[i].style.backgroundColor = 'white'; // What if we wanted a dark mode ???
                if (cl==='.noLinkYet') elements[i].style.color = 'black';
            }
        }
        btn.style.backgroundColor = 'orange';
        btn.textContent = 'Show verse colours';
    }
}
