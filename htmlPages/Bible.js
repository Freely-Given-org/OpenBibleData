function hide_show_marks() {
    // console.log('hide_show_marks()');
    ul_classes = ['ul', 'dom', 'untr']; //
    // ul_colours = ['darkGrey'];
    let btn = document.getElementById('marksButton');
    if (btn.textContent == 'Hide marks') {
        // console.log('It was hide');
        for (let cl of ul_classes) {
            // console.log(`  Hiding ${cl}`);
            let underlines = document.getElementsByClassName(cl);
            for (let i=0; i<underlines.length; i++) {
                if (cl == 'ul') underlines[i].style.color = 'white'; // We don't want to lose the space
                // else underlines[i].style.visibility = 'hidden';
                else underlines[i].style.display = 'none';
                }
        }
        btn.textContent = 'Show marks';
    } else {
        // console.log('It was show');
        for (let cl of ul_classes) {
            // console.log(`  Hiding ${cl}`);
            let underlines = document.getElementsByClassName(cl);
            for (let i=0; i<underlines.length; i++) {
                if (cl == 'ul') underlines[i].style.color = 'darkGrey';
                // else underlines[i].style.visibility = 'visible';
                else underlines[i].style.display = 'revert';
                }
        }
        btn.textContent = 'Hide marks';
    }
}
