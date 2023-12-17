function hide_show_marks() {
    // console.log('hide_show_marks()');
    classes_to_adjust = ['ul', 'dom', 'untr']; //
    // ul_colours = ['darkGrey'];
    let btn = document.getElementById('marksButton');
    if (btn.textContent == 'Hide marks') {
        // console.log('It was hide');
        for (let cl of classes_to_adjust) {
            // console.log(`  Hiding ${cl}`);
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
        // console.log('It was show');
        for (let cl of classes_to_adjust) {
            // console.log(`  Hiding ${cl}`);
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
