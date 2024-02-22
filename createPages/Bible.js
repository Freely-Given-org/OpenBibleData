function hide_show_marks() {
    classes_to_adjust = ['ul', 'dom', 'untr']; //
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
    let divs = document.getElementsByClassName('hideables');
    console.assert(divs.length === 1); // We only expect one
    let div = divs[0];
    if (div.style.display==='' || div.style.display==='revert')
        div.style.display = 'none';
    else
        div.style.display = 'revert';
}

function hide_show_transliterations() {
    classes_to_adjust = ['SR-GNT_trans','UGNT_trans','SBL-GNT_trans','TC-GNT_trans','BrLXX_trans','UHB_trans',
                            'WYC_mod','TNT_mod','CB_mod','GNV_mod','BB_mod','KJB_mod',
                            'LUT_trans','CLV_trans'];
    let topBtn = document.getElementById('TopTransliterationsButton');
    let btmBtn = document.getElementById('BottomTransliterationsButton');
    if (topBtn.textContent === 'ⱦ') {
        topBtn.textContent = 't'; btmBtn.textContent = 't';
        topBtn.title = 'Show transliterations, etc.'; btmBtn.title = 'Show transliterations, etc.';
        for (let cl of classes_to_adjust) {
            let elements_to_adjust = document.getElementsByClassName(cl);
            for (let i=0; i<elements_to_adjust.length; i++) {
                elements_to_adjust[i].style.display = 'none';
                }
            }
    } else {
        topBtn.textContent = 'ⱦ'; btmBtn.textContent = 'ⱦ';
        topBtn.title = 'Hide transliterations, etc.'; btmBtn.title = 'Hide transliterations, etc.';
        for (let cl of classes_to_adjust) {
            let elements_to_adjust = document.getElementsByClassName(cl);
            for (let i=0; i<elements_to_adjust.length; i++) {
                elements_to_adjust[i].style.display = 'revert';
                }
            }
    }
}

function hide_show_colours() {
    classes_to_adjust = ['.greekNom', '.greekAcc', '.greekGen', '.greekDat', '.greekVoc', '.greekVrb', '.greekNeg'];
    let btn = document.getElementById('coloursButton');
    if (btn.style.backgroundColor === 'orange') {
        btn.style.backgroundColor = null;
        for (let cl of classes_to_adjust) {
            var elements = document.querySelectorAll(cl);
            for(var i=0; i<elements.length; i++){
                elements[i].style.backgroundColor = null; // Seems to make it use the CSS again
            }
        }
    } else { // it wasn't already coloured
        btn.style.backgroundColor = 'orange';
        for (let cl of classes_to_adjust) {
            var elements = document.querySelectorAll(cl);
            for(var i=0; i<elements.length; i++){
                elements[i].style.backgroundColor = 'white'; // What if we wanted a dark mode ???
            }
        }
    }
}
