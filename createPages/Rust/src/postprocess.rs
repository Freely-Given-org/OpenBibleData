//! Post-processing string helpers ported from hot inner Python loops.
//!
//! These functions were among the most frequently-called pure-string helpers
//! in the page builders (called once per verse, per word, or per section
//! page):
//!
//!   * `remove_verse_punctuation_for_comparison` — from
//!     `createParallelVersePages.removeVersePunctuationForComparison`
//!     (it was even redefined on every verse iteration!).
//!   * `remove_greek_punctuation` — from
//!     `createParallelVersePages.removeGreekPunctuation`.
//!   * `split_oet_lv_interlinear_words` / `split_oet_rv_interlinear_words` —
//!     the per-entry clean/word-splitting chains in
//!     `createOETInterlinearPages.createOETInterlinearVerseInner`.
//!   * `remove_duplicate_c_vids` / `remove_duplicate_fnids` — from `html.py`
//!     (per-section-page duplicate-id removal for parallel verse pages).
//!   * `build_interlinear_word_rows` — the per-word interlinear row builder
//!     from `createOETInterlinearPages.createOETInterlinearVerseInner`
//!     (called for every verse of OET-LV: ~31K OT + NT verses × ~20 words).
//!
//! All ports must produce byte-identical output to the Python originals.
//!
//! Changelog:
//!  2026-09-09: Initial port of the helpers listed above.

use std::collections::HashMap;

/// Byte-identical port of `removeVersePunctuationForComparison`
/// (createParallelVersePages.py).  The `.replace` chain order matters.
pub fn remove_verse_punctuation_for_comparison(html_text: &str) -> String {
    html_text
        .replace(',', "")
        .replace('.', "")
        .replace(':', "")
        .replace(';', "")
        .replace('!', "")
        .replace('?', "")
        .replace('-', "")
        .replace('“', "")
        .replace('”', "")
        .replace('‘', "")
        .replace('’', "")
        .replace('(', "")
        .replace(')', "")
        .replace("¶ ", "")
        .replace('¶', "")
        .replace("  ", " ")
}

/// Byte-identical port of `removeGreekPunctuation`
/// (createParallelVersePages.py).  Unicode-aware lowercase, then the
/// punctuation chain (order matters), then strip.
pub fn remove_greek_punctuation(greek_text: &str) -> String {
    let s = greek_text
        .to_lowercase()
        .replace(',', "")
        .replace('.', "")
        .replace('!', "")
        .replace('?', "")
        .replace(';', "")
        .replace(';', "")
        .replace('·', "")
        .replace('·', "")
        .replace(':', "")
        .replace('(', "")
        .replace(')', "")
        .replace('[', "")
        .replace(']', "")
        .replace('“', "")
        .replace('”', "")
        .replace('‘', "")
        .replace('’', "")
        .replace('⸀', "")
        .replace('⸂', "")
        .replace('⸃', "")
        .replace('⸁', "")
        .replace('⸄', "")
        .replace('⸅', "")
        .replace('⟦', "")
        .replace('⟧', "")
        .replace('ʼ', "")
        .replace('˚', "")
        .replace('—', " ")
        .replace('–', " ")
        .replace('…', " ")
        .replace("   ", " ")
        .replace("  ", " ");
    s.trim().to_string()
}

/// Byte-identical port of the OET-LV English-word splitting chain in
/// `createOETInterlinearVerseInner`:
///
/// ```python
/// cleanLVText
///     .replace(',','').replace('.','').replace(':','').replace('?','')
///     .replace('>','').replace('<','')
///     .replace('/messiah¦', ' messiah¦')
///     .replace('_',' ').replace('=',' ').replace('÷',' ')
///     .replace('   ',' ').replace('  ',' ')
///     .strip().split( ' ' )
/// ```
///
/// Python's `str.split(' ')` keeps zero-length pieces, so a caller that logs
/// "zero-length word" messages (as the interlinear builder does) still sees
/// them — behaviour is preserved exactly.
pub fn split_oet_lv_interlinear_words(clean_text: &str) -> Vec<String> {
    let s = clean_text
        .replace(',', "")
        .replace('.', "")
        .replace(':', "")
        .replace('?', "")
        .replace('>', "")
        .replace('<', "")
        .replace("/messiah¦", " messiah¦")
        .replace('_', " ")
        .replace('=', " ")
        .replace('÷', " ")
        .replace("   ", " ")
        .replace("  ", " ");
    s.trim().split(' ').map(|w| w.to_string()).collect()
}

/// Byte-identical port of the OET-RV English-word splitting chain in
/// `createOETInterlinearVerseInner`:
///
/// ```python
/// fullRVText.replace(',','').replace('.','').replace(':','').replace('?','')
///     .replace('\\add >','').replace('\\add <','')
///     .replace('\\add ','').replace('\\add*','')
///     .replace('\\nd ','').replace('\\nd*','')
///     .replace('\\sup ','<sup>').replace('\\sup*','</sup>')
///     .replace('_',' ').replace('   ',' ').replace('  ',' ')
///     .strip().split( ' ' )
/// ```
pub fn split_oet_rv_interlinear_words(full_text: &str) -> Vec<String> {
    let s = full_text
        .replace(',', "")
        .replace('.', "")
        .replace(':', "")
        .replace('?', "")
        .replace("\\add >", "")
        .replace("\\add <", "")
        .replace("\\add ", "")
        .replace("\\add*", "")
        .replace("\\nd ", "")
        .replace("\\nd*", "")
        .replace("\\sup ", "<sup>")
        .replace("\\sup*", "</sup>")
        .replace('_', " ")
        .replace("   ", " ")
        .replace("  ", " ");
    s.trim().split(' ').map(|w| w.to_string()).collect()
}

// ── duplicate id removal (ports of html.removeDuplicateCVids/FNids) ────────

/// Byte-equivalent port of `html.removeDuplicateCVids`.
///
/// The Python original searches `html` with `str.find(needle, start)` where all
/// needles are ASCII, so byte offsets behave like Python's code-point offsets.
/// The forward/backward prefix comparisons near a found offset are done on raw
/// bytes (`as_bytes().get(..)`) so a multibyte UTF-8 character straddling a
/// slice boundary can never panic, while producing the same True/False result
/// as Python's character slicing (a match requires all-N-ASCII bytes).
pub fn remove_duplicate_c_vids(html_in: &str) -> String {
    let mut html = html_in.to_string();
    let mut end_ix = 0; // Where we start searching

    loop {
        let start_v_ix = match html.get(end_ix..).and_then(|tail| tail.find(" id=\"V")) {
            Some(ix) => end_ix + ix,
            None => 99_999_999,
        };
        let start_c_ix = match html.get(end_ix..).and_then(|tail| tail.find(" id=\"C")) {
            Some(ix) => end_ix + ix,
            None => 99_999_999,
        };
        let start_ix = start_v_ix.min(start_c_ix);
        if start_ix == 99_999_999 {
            break; // None / no more
        }

        // The end of the first id field found — any duplicates will be AFTER
        // this.  Python: `endIx = html.find( '>', startIx+8 )`.  All offsets
        // are fresh `find` results on the current `html` (a valid char/byte
        // boundary), and `end_ix` is only ever used for slicing that prefix,
        // which never changes across the inner loop.
        end_ix = start_ix + 8
            + html
                .get(start_ix + 8..)
                .and_then(|tail| tail.find('>'))
                .unwrap_or_else(|| {
                    // Python's find would return -1 here (never expected);
                    // clamp so slicing stays in bounds.
                    html.len().saturating_sub(start_ix + 8)
                });

        let id_contents = html[start_ix..end_ix].to_string();
        let mut end_html = html[end_ix..].to_string();

        // Remove the second id field in each case (which should be in the LV text).
        loop {
            let Some(end_html_start_ix) = end_html.find(id_contents.as_str()) else {
                break; // No duplicate found
            };
            if (id_contents.starts_with(" id=\"C") && !id_contents.contains('V'))
                || id_contents.starts_with(" id=\"V")
            {
                // Only in side-by-side chapters (not in entire books)
                let span_before = html_bytes(&end_html, end_html_start_ix.saturating_sub(5), end_html_start_ix)
                    == Some(b"<span".as_slice());
                let span_after = html_bytes(
                    &end_html,
                    end_html_start_ix + id_contents.len(),
                    end_html_start_ix + id_contents.len() + 8,
                ) == Some("></span>".as_bytes());
                let class_c_before = html_bytes(&end_html, end_html_start_ix.saturating_sub(15), end_html_start_ix)
                    == Some("<span class=\"c\"".as_bytes());

                if span_before && span_after {
                    // then from something like '<span id="C123"></span>', if we
                    // delete the id bit, we get useless '<span></span>' so let's
                    // delete the whole lot instead.
                    end_html = format!(
                        "{}{}",
                        &end_html[..end_html_start_ix - 5],
                        &end_html[end_html_start_ix + id_contents.len() + 8..]
                    );
                } else if class_c_before && end_html[end_html_start_ix..].starts_with(" id=\"C") {
                    end_html = format!(
                        "{}{}",
                        &end_html[..end_html_start_ix],
                        &end_html[end_html_start_ix + id_contents.len()..]
                    );
                } else {
                    end_html = format!(
                        "{}{}",
                        &end_html[..end_html_start_ix],
                        &end_html[end_html_start_ix + id_contents.len()..]
                    );
                }
                html = format!("{}{}", &html[..end_ix], end_html);
            } else {
                end_html = format!(
                    "{}{}",
                    &end_html[..end_html_start_ix],
                    &end_html[end_html_start_ix + id_contents.len()..]
                );
                html = format!("{}{}", &html[..end_ix], end_html);
            }
        }
    }

    html
}

/// Byte-identical port of `html.removeDuplicateFNids`.
pub fn remove_duplicate_fnids(_where: &str, html_in: &str) -> String {
    let mut html = html_in.to_string();
    let mut end_ix = 0; // Where we start searching

    loop {
        let Some(start_ix) = html.get(end_ix..).and_then(|tail| tail.find(" id=\"fn")) else {
            break; // None / no more
        };
        let start_ix = end_ix + start_ix;
        // The end of the first id field found -- any duplicates will be AFTER this
        end_ix = start_ix + 8
            + html
                .get(start_ix + 8..)
                .and_then(|tail| tail.find('>'))
                .unwrap_or_else(|| html.len().saturating_sub(start_ix + 8));

        let id_contents = html[start_ix..end_ix].to_string();
        let mut end_html = html[end_ix..].to_string();

        // Remove the second id field in each case
        // (which should be in the translated/transliterated footnote).
        loop {
            let Some(end_html_start_ix) = end_html.find(id_contents.as_str()) else {
                break; // No duplicate found
            };
            end_html = format!(
                "{}{}",
                &end_html[..end_html_start_ix],
                &end_html[end_html_start_ix + id_contents.len()..]
            );
            html = format!("{}{}", &html[..end_ix], end_html);
        }
    }

    html
}

/// Byte-range of `s` as a raw slice, or `None` when out of bounds.
#[inline]
fn html_bytes(s: &str, start: usize, end: usize) -> Option<&[u8]> {
    s.as_bytes().get(start..end)
}

// ── interlinear per-word row builder ───────────────────────────────────────

/// Byte-identical port of the per-word interlinear row builder in
/// `createOETInterlinearVerseInner` (the `if NT: … else: # OT` word rows).
///
/// Given the pre-split tab-separated fields of each word-table row for one
/// verse (plus the parallel word numbers, the per-word interlinear page
/// filenames, and the OET-LV / OET-RV English-word dictionaries), returns the
/// joined HTML for the whole list (title row + one `<li>` per word), ready to
/// append straight into `ivHtml` (Python then joins with `\n`).
pub fn build_interlinear_word_rows(
    level: usize,
    nt: bool,
    rows: &[Vec<String>],
    word_numbers: &[usize],
    wordpage_filenames: &[String],
    lv_english: &HashMap<usize, Vec<String>>,
    rv_english: &HashMap<usize, Vec<String>>,
) -> String {
    let mut parts: Vec<String> = Vec::new();
    let prefix_up = "../".repeat(level);

    if nt {
        parts.push(
            "<li><ol class=\"titles\">\n  <li lang=\"el\">Greek word</li>\n  <li lang=\"el_LEMMA\">Greek lemma</li>\n  <li lang=\"en_TRANS\"><b>OET-LV words</b></li>\n  <li lang=\"en_TRANS\"><b>OET-RV words</b></li>\n  <li lang=\"en_STRONGS\">Strongs</li>\n  <li lang=\"en_MORPH\">Role/Morphology</li>\n  <li lang=\"en_GLOSS\">OET Gloss</li>\n  <li lang=\"en_GLOSS\">VLT Gloss</li>\n  <li lang=\"en_CAPS\">CAPS codes</li>\n  <li lang=\"en_PERCENT\">Confidence</li>\n  <li lang=\"en_TAGS\">OET tags</li>\n  <li lang=\"en_WORDNUM\">OET word #</li>\n</ol><!--titles--></li>"
                .to_string(),
        );
        for (row, (&word_number, wpf)) in rows.iter().zip(word_numbers.iter().zip(wordpage_filenames)) {
            let tags_html = build_tags_html(row.get(11).map(String::as_str).unwrap_or_default(), &prefix_up);
            let word_class = if row.get(7).map(String::as_str).unwrap_or_default() == "X" {
                "word"
            } else {
                "variant"
            };
            let lt_words = join_english_words(lv_english.get(&word_number));
            let rv_words = join_english_words(rv_english.get(&word_number));
            let vlt_gloss = row.get(4).map(String::as_str).unwrap_or_default();
            let untr_open = if vlt_gloss.starts_with('¬') {
                "<span class=\"untr\" title=\"Word typically omitted from English translations\">"
            } else {
                "<b>"
            };
            let untr_close = if vlt_gloss.starts_with('¬') { "</span>" } else { "</b>" };
            let caps = opt_or_dash(row.get(6).map(String::as_str).unwrap_or_default());
            let row8 = row.get(8).map(String::as_str).unwrap_or_default();
            // Python: `row[8][:-1]` (drops a trailing G/S suffix from the
            // Strongs #, leaving the number for the BibleHub link).
            let row8_link = if row8.is_empty() { "" } else { &row8[..row8.len() - 1] };
            parts.push(format!(
                "<li><ol class=\"{}\">\n  <li lang=\"el\">{}</li>\n  <li lang=\"el_LEMMA\">{}</li>\n  <li lang=\"en_TRANS\">{}{}{}</li>\n  <li lang=\"en_TRANS\"><b>{}</b></li>\n  <li lang=\"en_STRONGS\"><a href=\"https://BibleHub.com/greek/{}.htm\">{}</a></li>\n  <li lang=\"en_MORPH\">{}{}</li>\n  <li lang=\"en_GLOSS\">{}</li>\n  <li lang=\"en_GLOSS\">{}</li>\n  <li lang=\"en_CAPS\">{}</li>\n  <li lang=\"en_TAGS\">{}</li>\n  <li lang=\"en_WORDNUM\"><a title=\"View word details\" href=\"{}ref/GrkWrd/{}#Top\">{}</a></li>\n</ol><!--{}--></li>",
                word_class,
                row.get(1).map(String::as_str).unwrap_or_default(),
                row.get(2).map(String::as_str).unwrap_or_default(),
                untr_open,
                lt_words,
                untr_close,
                rv_words,
                row8_link,
                row8,
                row.get(9).map(String::as_str).unwrap_or_default(),
                row.get(10).map(String::as_str).unwrap_or_default(),
                row.get(5).map(String::as_str).unwrap_or_default(),
                vlt_gloss,
                caps,
                tags_html,
                prefix_up,
                wpf,
                word_number,
                word_class,
            ));
        }
    } else {
        parts.push(
            "<li><ol class=\"titles\">\n  <li lang=\"he\">Hebrew word</li>\n  <li lang=\"he_LEMMA\">Hebrew lemma</li>\n  <li lang=\"en_TRANS\"><b>OET-LV words</b></li>\n  <li lang=\"en_TRANS\"><b>OET-RV words</b></li>\n  <li lang=\"en_STRONGS\">Strongs</li>\n  <li lang=\"en_MORPH\">Role/Morphology</li>\n  <li lang=\"en_GLOSS\">Gloss</li>\n  <li lang=\"en_CAPS\">CAPS codes</li>\n  <li lang=\"en_TAGS\">OET tags</li>\n  <li lang=\"en_WORDNUM\">OET word #</li>\n</ol><!--titles--></li>"
                .to_string(),
        );
        for (row, &word_number) in rows.iter().zip(word_numbers) {
            let tags_html = build_tags_html(row.get(18).map(String::as_str).unwrap_or_default(), &prefix_up);
            let gloss = pick_gloss(row);
            let strongs_list: Vec<String> = row
                .get(4)
                .into_iter()
                .flat_map(|strongs| strongs.split(','))
                .filter(|nn| !nn.is_empty() && nn.chars().all(|ch| ch.is_ascii_digit()))
                .map(|nn| format!("<a href=\"https://BibleHub.com/hebrew/{}.htm\">{}</a>", nn, nn))
                .collect();
            let caps = opt_or_dash(row.get(12).map(String::as_str).unwrap_or_default());
            parts.push(format!(
                "<li><ol class=\"word\">\n  <li lang=\"he\">{}</li>\n  <li lang=\"he_LEMMA\">{}</li>\n  <li lang=\"en_TRANS\"><b>{}</b></li>\n  <li lang=\"en_TRANS\"><b>{}</b></li>\n  <li lang=\"en_STRONGS\">{}</li>\n  <li lang=\"en_MORPH\">{}-{}</li>\n  <li lang=\"en_GLOSS\">{}</li>\n  <li lang=\"en_CAPS\">{}</li>\n  <li lang=\"en_TAGS\">{}</li>\n  <li lang=\"en_WORDNUM\"><a title=\"View word details\" href=\"{}ref/HebWrd/{}.htm#Top\">{}</a></li>\n</ol><!--word--></li>",
                row.get(7).map(String::as_str).unwrap_or_default(),
                row.get(2).map(String::as_str).unwrap_or_default(),
                join_english_words(lv_english.get(&word_number)),
                join_english_words(rv_english.get(&word_number)),
                strongs_list.join(","),
                row.get(16).map(String::as_str).unwrap_or_default(),
                row.get(5).map(String::as_str).unwrap_or_default(),
                gloss,
                caps,
                tags_html,
                prefix_up,
                word_number,
                word_number,
            ));
        }
    }

    parts.join("\n")
}

/// Port of the `gloss = row[11] if row[11] else row[10] if row[10] else
/// row[9] if row[9] else row[8]` chain for Hebrew word-table rows.
fn pick_gloss(row: &[String]) -> String {
    for ix in [11_usize, 10, 9, 8] {
        if let Some(field) = row.get(ix) {
            if !field.is_empty() {
                return field.clone();
            }
        }
    }
    String::new()
}

/// Port of the Person=/Location= tag linking block.
///
/// ```python
/// if row[11] (NT) / row[18] (OT):
///     tags = row[N].split( ';' )
///     for t,tag in enumerate( tags ):
///         tagPrefix, tag = tag[0], tag[1:]
///         if tagPrefix == 'P': tags[t] = f'''Person=<a …>{tag}</a>'''
///         elif tagPrefix == 'L': tags[t] = f'''Location=<a …>{tag}</a>'''
///     tagsHtml = '; '.join( tags )
/// else: tagsHtml = '-'
/// ```
fn build_tags_html(raw_tags: &str, prefix_up: &str) -> String {
    if raw_tags.is_empty() {
        return "-".to_string();
    }
    let mut tags: Vec<String> = raw_tags.split(';').map(|t| t.to_string()).collect();
    for tag in tags.iter_mut() {
        let Some(first) = tag.chars().next() else {
            continue;
        };
        let rest = &tag[first.len_utf8()..];
        if first == 'P' {
            *tag = format!(
                "Person=<a title=\"View person details\" href=\"{}ref/Per/{}.htm#Top\">{}</a>",
                prefix_up, rest, rest
            );
        } else if first == 'L' {
            *tag = format!(
                "Location=<a title=\"View place details\" href=\"{}ref/Loc/{}.htm#Top\">{}</a>",
                prefix_up, rest, rest
            );
        }
    }
    tags.join("; ")
}

/// Port of `' '.join(lvEnglishWordDict[wordNumber]) if lvEnglishWordDict[wordNumber] else '-'`.
fn join_english_words(words: Option<&Vec<String>>) -> String {
    match words {
        Some(words) if !words.is_empty() => words.join(" "),
        _ => "-".to_string(),
    }
}

/// Port of `row[6] if row[6] else '-'` (and CAPS equivalents).
#[inline]
fn opt_or_dash(field: &str) -> &str {
    if field.is_empty() {
        "-"
    } else {
        field
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn verse_punctuation_for_comparison() {
        // No space collapse in this one (single spaces only):
        assert_eq!(
            remove_verse_punctuation_for_comparison("2Sam 4:10 is (a) test."),
            "2Sam 410 is a test"
        );
        // The '¶ ' removal leaves one space; then '  ' is not present:
        assert_eq!(
            remove_verse_punctuation_for_comparison("¶  2Sam 4:10 is (a) test."),
            " 2Sam 410 is a test"
        );
        // Double space collapse (from removed brackets ¶ e.g. 2Sam 4:10):
        assert_eq!(
            remove_verse_punctuation_for_comparison("a ¶  b"),
            "a b"
        );
    }

    #[test]
    fn greek_punctuation() {
        // Python: '᾿' (U+1FBF) is NOT removed — only 'ʼ' (U+02BC);
        // ἈΡΧΗ lowercases to ἀρχη; the '…' and '—' collapse to single spaces.
        assert_eq!(
            remove_greek_punctuation("Ἀπὸ ΚΑΘʼ (ἀρχῇ)… — ἘΝ ἈΡΧΗ·"),
            "ἀπὸ καθ ἀρχῇ ἐν ἀρχη"
        );
    }

    #[test]
    fn greek_punctuation_strips_spaces() {
        assert_eq!(remove_greek_punctuation("  a  b  "), "a b");
    }

    #[test]
    fn lv_splitwords() {
        assert_eq!(
            split_oet_lv_interlinear_words("Say, hello: /messiah¦ 123_GOD"),
            ["Say", "hello", "messiah¦", "123", "GOD"]
        );
    }

    #[test]
    fn rv_splitwords() {
        assert_eq!(
            split_oet_rv_interlinear_words("\\nd YAHWEH\\nd* (\\add said\\add*) — \\sup 2\\sup*_times"),
            ["YAHWEH", "(said)", "—", "<sup>2</sup>", "times"]
        );
    }

    #[test]
    fn duplicate_c_vids_side_by_side() {
        // RV and LV both emit a <span id="V1"></span>; the second duplicate is
        // removed together with its empty span wrapper.
        let input = "<p><span id=\"V1\"></span>RVLINK<span id=\"V1\"></span></p>";
        let expected = "<p><span id=\"V1\"></span>RVLINK</p>";
        assert_eq!(remove_duplicate_c_vids(input), expected);
    }

    #[test]
    fn duplicate_c_vids_class_c() {
        // Whole-book pattern '<span class="c" id="C1">': only the duplicate id
        // attribute is removed, leaving the span in place.
        let input = "<p><span class=\"c\" id=\"C1\">hi<span class=\"c\" id=\"C1\">lo</span></p>";
        let expected = "<p><span class=\"c\" id=\"C1\">hi<span class=\"c\">lo</span></p>";
        assert_eq!(remove_duplicate_c_vids(input), expected);
    }

    #[test]
    fn duplicate_c_vids_plain_removal() {
        // Non-span duplicates just drop the duplicate id attribute.
        let input = "x id=\"V3\">y id=\"V3\">z";
        let expected = "x id=\"V3\">y>z";
        assert_eq!(remove_duplicate_c_vids(input), expected);
    }

    #[test]
    fn duplicate_fnids_removal() {
        let input = "<p class=\"fn\" id=\"fnL1V2\">one<p class=\"fn\" id=\"fnL1V2\">two";
        assert_eq!(
            remove_duplicate_fnids("test", input),
            "<p class=\"fn\" id=\"fnL1V2\">one<p class=\"fn\">two"
        );
    }

    #[test]
    fn interlinear_rows_nt() {
        // One Greek row: GreekWord λόγος, SR lemma, GreekLemma, VLT gloss,
        // OET gloss, caps, probability, strongs, role, morphology, tags.
        let rows = vec![vec![
            "MRKc1v1w1".to_string(),
            "λόγος".to_string(),
            "λόγος".to_string(),
            "λόγος".to_string(),
            "VLTword".to_string(),
            "OETword".to_string(),
            "".to_string(),      // GlossCaps
            "X".to_string(),     // Probability → class="word"
            "G3056".to_string(),
            "Noun".to_string(),
            "NomMasc".to_string(),
            "P001;L002".to_string(),
        ]];
        let numbers = vec![1];
        let filenames = vec!["MRKc1v1w1.htm".to_string()];
        let mut lv = HashMap::new();
        lv.insert(1, vec!["In".to_string(), "beginning".to_string()]);
        let mut rv = HashMap::new();
        rv.insert(1, vec!["In".to_string(), "beginning".to_string()]);
        let out = build_interlinear_word_rows(2, true, &rows, &numbers, &filenames, &lv, &rv);
        for expected_fragment in [
            "<ol class=\"titles\">",
            "<li lang=\"el\">λόγος</li>",
            "<b>In beginning</b>",
            "https://BibleHub.com/greek/G305.htm",
            "Person=<a title=\"View person details\" href=\"../../ref/Per/001.htm#Top\">001</a>; Location=<a title=\"View place details\" href=\"../../ref/Loc/002.htm#Top\">002</a>",
            "../../ref/GrkWrd/MRKc1v1w1.htm#Top",
        ] {
            assert!(out.contains(expected_fragment), "missing {expected_fragment:?} in {out}");
        }
    }

    #[test]
    fn interlinear_rows_ot() {
        let rows = vec![vec![
            "GENc1v1w1".to_string(),
            "RowType".to_string(),
            "לְ".to_string(), // lemma (ix 2)
            "MorphemeRowList".to_string(),
            "7225,xxxx,yyyy".to_string(), // strongs, non-digit filtered
            "Morph".to_string(),
            "בְּרֵאשִׁית".to_string(), // word (ix 6)
            "בראשית".to_string(), // NoCantillations (ix 7) → displayed
            "m".to_string(),
            "cw".to_string(),
            "wg".to_string(),
            "ctxgloss".to_string(), // 11 → chosen gloss
            "".to_string(),          // 12 → CAPS dash
            "".to_string(),
            "".to_string(),
            "".to_string(),
            "Role".to_string(), // 16
            "Nesting".to_string(),
            "L123".to_string(), // tags
        ]];
        let out = build_interlinear_word_rows(3, false, &rows, &[55], &[], &HashMap::new(), &HashMap::new());
        for expected_fragment in [
            "<ol class=\"titles\">",
            "<li lang=\"he\">בראשית</li>",
            "https://BibleHub.com/hebrew/7225.htm",
            "<li lang=\"en_MORPH\">Role-Morph</li>",
            "<li lang=\"en_GLOSS\">ctxgloss</li>",
            "<li lang=\"en_CAPS\">-</li>",
            "Location=<a title=\"View place details\" href=\"../../../ref/Loc/123.htm#Top\">123</a>",
            "</ol><!--word--></li>",
            "<li lang=\"en_TRANS\"><b>-</b></li>",
            "<li lang=\"en_WORDNUM\"><a title=\"View word details\" href=\"../../../ref/HebWrd/55.htm#Top\">55</a></li>",
        ] {
            assert!(out.contains(expected_fragment), "missing {expected_fragment:?} in {out}");
        }
    }
}