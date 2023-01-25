function hide_show_underlines() {
    console.log('hide_show_underlines()');
    ul_classes = ['ul', 'dom'];
    // ul_colours = ['darkGrey'];
    let btn = document.getElementById('underlineButton');
    if (btn.textContent == 'Hide underlines') {
        console.log('It was hide');
        for (let cl of ul_classes) {
            console.log(`  Hiding ${cl}`);
            let underlines = document.getElementsByClassName(cl);
            for (let i=0; i<underlines.length; i++) {
                if (cl == 'ul') underlines[i].style.color = 'white';
                // else underlines[i].style.visibility = 'hidden';
                else underlines[i].style.display = 'none';
                }
        }
        btn.textContent = 'Show underlines';
    } else {
        console.log('It was show');
        for (let cl of ul_classes) {
            console.log(`  Hiding ${cl}`);
            let underlines = document.getElementsByClassName(cl);
            for (let i=0; i<underlines.length; i++) {
                if (cl == 'ul') underlines[i].style.color = 'darkGrey';
                // else underlines[i].style.visibility = 'visible';
                else underlines[i].style.display = 'revert';
                }
        }
        btn.textContent = 'Hide underlines';
    }
}
