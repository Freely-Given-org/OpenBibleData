//! Byte-identical ports of the per-version HTML customisations in `html.py`.
//!
//! These functions are the bulk-mutation pass applied to each version's
//! chapter/verse HTML before the page is assembled:
//!
//!   * `do_oet_rv_html_customisations` — OET-RV `/add` subfield markers and
//!     poetry parallelism symbols (port of `html.do_OET_RV_HTMLcustomisations`).
//!   * `do_oet_lv_html_customisations` — OET-LV sentence-per-line breaking with
//!     protection of fields like `../C2_V2.htm`, times, verse refs, footnote
//!     callers (port of `html.do_OET_LV_HTMLcustomisations`).
//!   * `do_lsv_html_customisations` — LSV's parallel-line `||` to `<br>`
//!     (port of `html.do_LSV_HTMLcustomisations`).
//!   * `do_t4t_html_customisations` — T4T figure-of-speech `[SIM]`-style codes
//!     (port of `html.do_T4T_HTMLcustomisations`).
//!   * `do_convert_adds_to_italics` — hardwires `/add` words in non-OET
//!     versions to italics (port of `html.convert_adds_to_italics`).
//!   * `do_handle_and_extract_footnotes` — splits off a verse's footnotes
//!     division, namespacing its footnote ids/hrefs per version and stripping
//!     the footnote callers from the footnote-free copy (port of
//!     `html.handleAndExtractFootnotes`).
//!
//! All `.replace()` chains preserve Python's `str.replace` semantics (replace
//! every non-overlapping occurrence, left-to-right) — Rust's `str::replace`
//! does exactly the same, so the chains below are drop-in identical.
//!
//! Python `assert` statements are transcribed as explicit checks gated on
//! `have_strict_checking_flag() || cfg!(debug_assertions)` (matching the
//! convention in `html_validation.rs`); real (non-assert) error paths such as
//! the `NOT_ENOUGH_LOOPS` `NameError` and out-of-range indexing are always
//! replicated, exactly as they behave under `python -O`.
//!
//! Error messages use `"AssertionError:"`, `"IndexError:"` and `"NameError:"`
//! prefixes so that `err_to_pyerr` in `lib.rs` raises the same Python
//! exception classes as the Python originals.
//!
//! Changelog:
//!   2026-09-16: Initial port of the four customisation functions.
//!   2026-09-17: Ported convert_adds_to_italics and handleAndExtractFootnotes.

use crate::html_validation::{check_html, py_repr};
use bos_internals::have_strict_checking_flag;
use once_cell::sync::Lazy;
use regex::Regex;

// ── T4T figure-of-speech codes (order matters for the replace chains) ───────
const T4T_FOS_TYPES: [(&str, &str); 18] = [
    ("APO", "apostrophe"),
    ("CHI", "chiasmus"),
    ("DOU", "doublet"),
    ("EUP", "euphemism"),
    ("HEN", "hendiadys"),
    ("HYP", "hyperbole"),
    ("IDM", "idiom"),
    ("IRO", "irony"),
    ("LIT", "litotes"),
    ("MET", "metaphor"),
    ("MTY", "metonymy"),
    ("PRS", "personification"),
    ("RHQ", "rhetorical question"),
    ("SIM", "simile"),
    ("SYM", "symbol"),
    ("SAR", "sarcasm"),
    ("SYN", "synecdoche"),
    ("TRI", "triple"),
];

// ── Shared helper ───────────────────────────────────────────────────────────
/// Replicate `html.checkHtml(where, htmlToCheck, segmentOnly=True)` for the
/// final validation inside the OET-RV/LV customisations: apply the Python
/// wrapper's wasted-`<br>` fix (which mutates its local copy) and then delegate
/// to the Rust `check_html` core.  Any error message from `check_html` maps to
/// a Python `ValueError` (the same exception `_rustCheckHtml` raises).
fn check_segment_like_python(where_: &str, html: &mut String) -> Result<(), String> {
    if html.contains("\n<br></p>") || html.contains("\n<br></span>") {
        *html = html
            .replace("\n<br></span></span></p>", "</span></span></p>")
            .replace("\n<br></span></p>", "</span></p>")
            .replace("\n<br></p>", "</p>");
    }
    check_html(html, where_, true)
}

// ── do_OET_RV_HTMLcustomisations ────────────────────────────────────────────
/// Byte-identical port of `html.do_OET_RV_HTMLcustomisations`.
///
/// Returns an error (with a Python-compatible message prefix) instead of
/// panicking; the Python originals raise the corresponding exception.
pub fn do_oet_rv_html_customisations(where_: &str, html: &str) -> Result<String, String> {
    let strict = have_strict_checking_flag() || cfg!(debug_assertions);
    if strict && html.contains("<span class=\"add\">=") {
        return Err("AssertionError: ".to_string()); // Only expected in OET-LV
    }

    // -- Adjust specialised OET-RV /add markers and parallelism markers --
    let result = html
        .replace(
            r#"<span class="add">?<a title="#,
            r#"<span class="RVadd unsure" title="added info (less certain)"><a title="#,
        )
        .replace(
            r#"<span class="add">?<span"#,
            r#"<span class="RVadd unsure" title="added info (less certain)"><span"#,
        )
        .replace(
            r#"<span class="add">?<"#,
            r#"<span class="addDirectObject unsure" title="added direct object (less certain)">"#,
        )
        .replace(r#"<span class="add"><span "#, "__PROTECT_SPAN__")
        .replace(r#"<span class="add"><a title"#, "__PROTECT_A__")
        .replace(
            r#"<span class="add"><"#,
            r#"<span class="addDirectObject" title="added direct object">"#,
        )
        .replace("__PROTECT_A__", r#"<span class="add"><a title"#)
        .replace("__PROTECT_SPAN__", r#"<span class="add"><span "#)
        .replace(
            r#"<span class="add">?>"#,
            r#"<span class="addExtra unsure" title="added implied info (less certain)">"#,
        )
        .replace(
            r#"<span class="add">>"#,
            r#"<span class="addExtra" title="added implied info">"#,
        )
        .replace(
            r#"<span class="add">?+"#,
            r#"<span class="addArticle unsure" title="added article (less certain)">"#,
        )
        .replace(r#"<span class="add">+"#, r#"<span class="addArticle" title="added article">"#)
        .replace(
            r#"<span class="add">?≡"#,
            r#"<span class="addElided unsure" title="added elided info (less certain)">"#,
        )
        .replace(r#"<span class="add">≡"#, r#"<span class="addElided" title="added elided info">"#)
        .replace(
            r#"<span class="add">?&"#,
            r#"<span class="addOwner unsure" title="added ‘owner’ (less certain)">"#,
        )
        .replace(r#"<span class="add">&"#, r#"<span class="addOwner" title="added ‘owner’">"#)
        .replace(
            r#"<span class="add">?@"#,
            r#"<span class="addReferent unsure" title="inserted referent (less certain)">"#,
        )
        .replace(r#"<span class="add">@"#, r#"<span class="addReferent" title="inserted referent">"#)
        .replace(
            r#"<span class="add">?*"#,
            r#"<span class="addPronoun unsure" title="used pronoun (less certain)">"#,
        )
        .replace(r#"<span class="add">*"#, r#"<span class="addPronoun" title="used pronoun">"#)
        .replace(
            r#"<span class="add">?#"#,
            r#"<span class="addNumberChange unsure" title="changed number (less certain)">"#,
        )
        .replace(r#"<span class="add">#"#, r#"<span class="addNumberChange" title="changed number">"#)
        .replace(
            r#"<span class="add">?%"#,
            r#"<span class="addPersonChange unsure" title="changed person (less certain)">"#,
        )
        .replace(r#"<span class="add">%"#, r#"<span class="addPersonChange" title="changed person">"#)
        .replace(
            r#"<span class="add">?^"#,
            r#"<span class="addNegated unsure" title="negated (less certain)">"#,
        )
        .replace(r#"<span class="add">^"#, r#"<span class="addNegated" title="negated">"#)
        .replace(
            r#"<span class="add">?≈"#,
            r#"<span class="addReword unsure" title="reworded (less certain)">"#,
        )
        .replace(r#"<span class="add">≈"#, r#"<span class="addReword" title="reworded">"#)
        .replace(r#"<span class="add">?"#, r#"<span class="RVadd unsure" title="added info (less certain)">"#)
        .replace(r#"<span class="add">"#, r#"<span class="RVadd" title="added info">"#)
        .replace(
            "≈",
            "<span class=\"synonParr\" title=\"synonymous parallelism\">≈\u{202F}</span>",
        )
        .replace(
            "^",
            "<span class=\"antiParr\" title=\"antithetic parallelism\">^\u{202F}</span>",
        )
        .replace(
            "→",
            "<span class=\"synthParr\" title=\"synthetic parallelism\">→\u{202F}</span>",
        );

    // -- Check the text just past each '<span class="RVadd">' span --
    // (Python searches with character indices, so work on a Vec<char>.)
    let chars: Vec<char> = result.chars().collect();
    let needle_len = r#"<span class="RVadd">"#.chars().count();
    let mut start_search_index = 0usize;
    let mut broke_out = false;
    for _ in 0..3_000 {
        // Match r#"<span class="RVadd">"# at/after start_search_index (char index).
        let mut match_start = None;
        if start_search_index + needle_len <= chars.len() {
            'outer: for i in start_search_index..=(chars.len() - needle_len) {
                for (k, expected) in r#"<span class="RVadd">"#.chars().enumerate() {
                    if chars[i + k] != expected {
                        continue 'outer;
                    }
                }
                match_start = Some(i);
                break;
            }
        }
        let Some(match_start) = match_start else {
            broke_out = true;
            break;
        };
        start_search_index = match_start + needle_len;
        let next_chars = &chars[start_search_index..];
        let next_starts_with = |prefix: &str| {
            let p: Vec<char> = prefix.chars().collect();
            next_chars.starts_with(&p[..])
        };
        if !(next_starts_with("<a title")
            || next_starts_with(r#"<span class="wj">"#)
            || next_starts_with(r#"<span class="nominaSacra">"#))
        {
            // nextChar = result[startSearchIndex]  (raises IndexError if absent)
            let next_char = chars.get(start_search_index).ok_or_else(|| {
                "IndexError: string index out of range".to_string()
            })?;
            if strict {
                let ok = next_char.is_alphabetic()
                    || "(,\u{2018}\u{2019}\u{2014}123\u{263A}".contains(*next_char);
                if !ok {
                    let snippet: String =
                        chars[match_start..(match_start + 80).min(chars.len())].iter().collect();
                    return Err(format!(
                        "AssertionError: startSearchIndex={start_search_index} nextChar='{next_char}' {snippet}"
                    ));
                }
            }
        }
    }
    if !broke_out {
        // Python: `else: NOT_ENOUGH_LOOPS` → NameError (fires even under -O)
        return Err("NameError: name 'NOT_ENOUGH_LOOPS' is not defined".to_string());
    }

    //
    if strict {
        let mut check_copy = result.clone();
        check_segment_like_python(where_, &mut check_copy)?;
    }
    Ok(result)
}

// ── do_OET_LV_HTMLcustomisations ────────────────────────────────────────────
/// Byte-identical port of `html.do_OET_LV_HTMLcustomisations`.
pub fn do_oet_lv_html_customisations(where_: &str, html: &str) -> Result<String, String> {
    let strict = have_strict_checking_flag() || cfg!(debug_assertions);
    if strict {
        if html.contains("<br>\n") {
            return Err("AssertionError: ".to_string());
        }
        if html.contains("\n<br></p>") || html.contains("\n<br></span>") {
            return Err(format!(
                "AssertionError: Wasted <br> in OET_LV_html='{html}'"
            ));
        }
    }

    // -- Preserve the colon in times like 12:30 and in C:V and v0.1 fields --
    // (Python works with character indices; replicate exactly with a Vec<char>.)
    let mut chars: Vec<char> = html.chars().collect();
    let mut search_start_index = 0usize;
    loop {
        let mut match_start = None;
        if search_start_index + 2 < chars.len() {
            for i in search_start_index..=(chars.len() - 3) {
                if chars[i].is_ascii_digit()
                    && (chars[i + 1] == ':' || chars[i + 1] == '.')
                    && chars[i + 2].is_ascii_digit()
                {
                    match_start = Some(i);
                    break;
                }
            }
        }
        let Some(i) = match_start else { break };
        // guts is always 3 chars here; the pattern guarantees exactly one of : or .
        let punct = chars[i + 1];
        let mut new_chars = Vec::with_capacity(chars.len() + 9);
        new_chars.extend_from_slice(&chars[..i]);
        new_chars.push(chars[i]);
        if punct == ':' {
            new_chars.extend("~~COLON~~".chars());
        } else {
            new_chars.extend("~~PERIOD~~".chars());
        }
        new_chars.push(chars[i + 2]);
        new_chars.extend_from_slice(&chars[i + 3..]);
        chars = new_chars;
        search_start_index = (i + 3) + 8; // We've added that many characters
    }
    let oet_lv_html: String = chars.into_iter().collect();

    if strict {
        // Only expected in OET-RV
        for marker in ["-", "*", "@", "~", "≈", "?"] {
            let needle = format!("<span class=\"add\">{marker}");
            if oet_lv_html.contains(&needle) {
                return Err("AssertionError: ".to_string());
            }
        }
    }

    // -- Protect fields we need to preserve, then make each sentence start a
    //    new line, then adjust specialised add markers, then underlines --
    let oet_lv_html = oet_lv_html
        .replace("_V", "~~ULINE~~V")
        .replace("_verseText", "~~ULINE~~verseText")
        .replace("<!--", "~~COMMENT~~")
        .replace("../", "~~PERIOD~~~~PERIOD~~/") // Protect paths like ../../somewhere.htm
        .replace(".htm", "~~PERIOD~~htm")
        .replace("https:", "https~~COLON~~")
        .replace(".org", "~~PERIOD~~org")
        .replace(".tsv", "~~PERIOD~~tsv")
        // .replace("v0.", "v0~~PERIOD~~")
        .replace(r".\f*", "~~PERIOD~~\\f*")
        .replace("Note:", "Note~~COLON~~")
        .replace(".\"", "~~PERIOD~~\"") // These last two are inside the footnote callers
        // In <hr>
        .replace("width:", "width~~COLON~~")
        .replace("margin-left:", "margin-left~~COLON~~")
        .replace("margin-top:", "margin-top~~COLON~~")
        // Make each sentence start a new line
        .replace('.', ".\n<br>")
        .replace('?', "?\n<br>")
        .replace('!', "!\n<br>")
        .replace(':', ":\n<br>")
        // Adjust specialised add markers
        .replace(r#"<span class="add">+"#, r#"<span class="addArticle">"#)
        .replace(r#"<span class="add">="#, r#"<span class="addCopula">"#)
        .replace(r#"<span class="add"><a title"#, "~~PROTECT~~")
        .replace(r#"<span class="add"><"#, r#"<span class="addDirectObject">"#)
        .replace("~~PROTECT~~", r#"<span class="add"><a title"#)
        .replace(r#"<span class="add">>"#, r#"<span class="addExtra">"#)
        .replace(r#"<span class="add">&"#, r#"<span class="addOwner">"#)
        // Put all underlines into a span with a class (then a button can hide them)
        .replace("=\"", "~~EQUAL\"") // Protect class=, id=, etc.
        .replace('=', "_")
        .replace('÷', "_") // For OT morphemes
        .replace("~~EQUAL\"", "=\"") // Unprotect class=, id=, etc.
        .replace('_', "<span class=\"ul\">_</span>") // THIS IS ONE THAT CAN OVERREACH
        // Now unprotect everything again
        .replace("--fnUNDERLINE--", "_")
        .replace("--fnEQUAL--", "=")
        .replace("--fnCOLON--", ":")
        .replace("--fnPERIOD--", ".") // Unprotect sanitised footnotes (see usfm.py)
        .replace("~~COMMENT~~", "<!--")
        .replace("~~ULINE~~", "_")
        .replace("~~COLON~~", ":")
        .replace("~~PERIOD~~", ".")
        // TODO: Not sure that this is the best place to do this next one for the OT
        .replace(" DOM ", " <span class=\"dom\">DOM</span> ")
        .to_string();

    // -- Move sentence-ending <br>s out of the way of closing tags --
    let oet_lv_html = oet_lv_html
        .replace("\n<br></span></span></p>", "</span></span></p>")
        .replace("\n<br></span></p>", "</span></p>")
        .replace("\n<br></p>", "</p>")
        .replace("\n<br></span>", "</span>\n<br>")
        .replace("\n<br></div><!--verseText-->", "</div><!--verseText-->\n<br>")
        .replace("\n<br>\n", "\n")
        .to_string();

    // Tidyup
    let mut oet_lv_html = oet_lv_html;
    if oet_lv_html.ends_with('\n') {
        oet_lv_html.pop(); // We don't end our html with a newline
    }
    if oet_lv_html.ends_with("<br>") {
        oet_lv_html.truncate(oet_lv_html.len() - 4); // We don't end our html with a newline
        if oet_lv_html.ends_with('\n') {
            oet_lv_html.pop(); // We don't end our html with a newline
        }
    }

    if strict {
        let where_label = format!("do_OET_LV_HTMLcustomisations where='{where_}'");
        let mut check_copy = oet_lv_html.clone();
        check_segment_like_python(&where_label, &mut check_copy)?;
    }
    Ok(oet_lv_html)
}

// ── do_LSV_HTMLcustomisations ───────────────────────────────────────────────
/// Byte-identical port of `html.do_LSV_HTMLcustomisations`: change the two
/// parallel lines (` || `) to `<br>`.
pub fn do_lsv_html_customisations(_where_: &str, html: &str) -> String {
    html.replace(" || ", "<br>").replace("||", "<br>") // Second one catches any source inconsistencies
}

// ── do_T4T_HTMLcustomisations ───────────────────────────────────────────────
/// Byte-identical port of `html.do_T4T_HTMLcustomisations`.
pub fn do_t4t_html_customisations(where_: &str, html: &str) -> Result<String, String> {
    let strict = have_strict_checking_flag() || cfg!(debug_assertions);
    let mut t4t_html = html.to_string();
    if t4t_html.contains('[') || t4t_html.contains(']') {
        t4t_html = t4t_html
            .replace("[SIL]", "[SIM]") // Error in Psa 63:1
            .replace("birth MET]", "birth [MET]"); // Error in Mat 24:8
        for (fos, fos_type) in T4T_FOS_TYPES {
            let full_fos = format!("[{fos}]");
            let replacement = format!(
                "<span class=\"t4tFoS\" title=\"{fos_type} (figure of speech)\">LEFTBRACKET{fos}RIGHTBRACKET</span>"
            );
            t4t_html = t4t_html.replace(&full_fos, &replacement);
        }
        if t4t_html.contains('[') {
            // still (we don't want to run these nested loops unnecessarily)
            for (fos1, fos_type1) in T4T_FOS_TYPES {
                for (fos2, fos_type2) in T4T_FOS_TYPES {
                    if fos2 != fos1 {
                        // T4T is not consistent here in use of commas and forward slashes
                        let full_foss = format!("[{fos1}, {fos2}]");
                        let replacement = format!(
                            "LEFTBRACKET<span class=\"t4tFoS\" title=\"{fos_type1} (figure of speech)\">{fos1}</span>, <span class=\"t4tFoS\" title=\"{fos_type2} (figure of speech)\">{fos2}</span>RIGHTBRACKET"
                        );
                        t4t_html = t4t_html.replace(&full_foss, &replacement);
                        let full_foss = format!("[{fos1}/{fos2}]");
                        let replacement = format!(
                            "LEFTBRACKET<span class=\"t4tFoS\" title=\"{fos_type1} (figure of speech)\">{fos1}</span>/<span class=\"t4tFoS\" title=\"{fos_type2} (figure of speech)\">{fos2}</span>RIGHTBRACKET"
                        );
                        t4t_html = t4t_html.replace(&full_foss, &replacement);
                    }
                }
            }
            // Double-check that we got them all
            if strict {
                for (fos1, _fos_type1) in T4T_FOS_TYPES {
                    for (fos2, _fos_type2) in T4T_FOS_TYPES {
                        if fos2 != fos1 {
                            let pat1 = format!("[{fos1}");
                            if t4t_html.contains(&pat1) {
                                return Err(format!("AssertionError: [{fos1} {where_} {t4t_html}"));
                            }
                            let pat2 = format!("{fos2}]");
                            if t4t_html.contains(&pat2) {
                                return Err(format!("AssertionError: {fos2}] {where_} {t4t_html}"));
                            }
                        }
                    }
                }
            }
        }
        t4t_html = t4t_html.replace("LEFTBRACKET", "[").replace("RIGHTBRACKET", "]");
    }
    Ok(t4t_html.replace('◄', "<span title=\"alternative translation\">◄</span>"))
}

// ── convert_adds_to_italics ──────────────────────────────────────────────────
/// Port of `html.convert_adds_to_italics`: hardwires added words (`<add>`) in
/// non-OET versions to italics.
///
/// The Python `for … else: not_enough_loops` trip fires a `NameError` whenever
/// 30+ `<span class="add">` fields survive the loop (the `else` runs only if
/// the loop never found `ix == -1`).  Like the `NOT_ENOUGH_LOOPS` error it is a
/// plain runtime error, not an assert, so it fires in every build mode.
pub fn do_convert_adds_to_italics(html_segment: &str) -> Result<String, String> {
    // Py for _cati_safetyCheck in range(30):
    //     ix = htmlSegment.find('<span class="add">')
    //     if ix == -1: break
    //     htmlSegment = htmlSegment.replace('<span class="add">', '<i>', 1)
    //     htmlSegment = f"{htmlSegment[:ix]}{htmlSegment[ix:].replace('</span>','</i>',1)}"
    // else: not_enough_loops
    let mut result = html_segment.to_string();
    let mut loop_exhausted = true;
    for _ in 0..30 {
        let Some(ix) = result.find("<span class=\"add\">") else {
            loop_exhausted = false;
            break;
        };
        // Python's replace(..., 1) replaces only the first occurrence; so does
        // Rust's replacen(..., 1).
        result = result.replacen("<span class=\"add\">", "<i>", 1);
        // Replace the first '</span>' at/after `ix` — this add's own closing
        // tag — with '</i>'.  `ix` is a character boundary (it points at the
        // ASCII '<'), so byte slicing lines up with Python's char indexing,
        // and every '<' '</span>' marker is ASCII, so byte == char for them.
        // An unterminated add leaves a plain no-op, exactly as in Python.
        if let Some(jx) = result[ix..].find("</span>") {
            result.replace_range(ix + jx..ix + jx + 7, "</i>");
        }
    }
    if loop_exhausted {
        Err("NameError: name 'not_enough_loops' is not defined".to_string())
    } else {
        Ok(result)
    }
}

// ── handleAndExtractFootnotes ────────────────────────────────────────────────
/// Python `re` engine: `<span class="fnCaller">.+?</span>` — `.` excludes `\n`
/// and `+` is lazy, which is exactly `regex`'s default (non-DOTALL) dot.  Both
/// engines walk left-to-right over non-overlapping matches.
static FNCALLER_REGEX: Lazy<Regex> =
    Lazy::new(|| Regex::new(r#"<span class="fnCaller">.+?</span>"#).expect("fnCaller regex"));

/// Port of `html.handleAndExtractFootnotes`: given a verse's HTML that may
/// contain a footnotes division, separates out the footnotes and returns
/// `(verse_html, footnote_free_verse_html, footnotes_html)`.
///
/// The Python `assert`s here are substantive data-integrity checks (footnote
/// `<hr ` / `<div` balance, stray-`<hr` detection, the "We want to stop here"
/// trap), so they are gated on strict checking exactly like the Python
/// originals: OBD enables them with `-c/--strict` (`BibleOrgSysGlobals`
/// `setStrictCheckingFlag()` → `set_rust_strict_checking(True)`), and they
/// stay inert otherwise to match `python -O`.
pub fn do_handle_and_extract_footnotes(
    version_abbreviation: &str,
    verse_html_input: &str,
) -> Result<(String, String, String), String> {
    let strict = have_strict_checking_flag() || cfg!(debug_assertions);
    let mut verse_html = verse_html_input.to_string();

    if verse_html.contains("<div id=\"footnotes\" class=\"footnotes\">") {
        let hr_count = verse_html.matches("<hr ").count();
        if strict {
            // Py: assert verseHtml.count('<hr ') >= 1, f'{versionAbbreviation} ({...}) {verseHtml=}'
            if hr_count < 1 {
                return Err(format!(
                    "AssertionError: {version_abbreviation} ({hr_count}) verseHtml={}",
                    py_repr(&verse_html)
                ));
            }
            // Py: assert '<div id="crossRefs" class="crossRefs">' in verseHtml, ...
            if hr_count > 1 && !verse_html.contains("<div id=\"crossRefs\" class=\"crossRefs\">") {
                return Err(format!(
                    "AssertionError: {version_abbreviation} ({hr_count}) verseHtml={}",
                    py_repr(&verse_html)
                ));
            }
            // Py: assert verseHtml.count('</div>') == verseHtml.count('<div ')
            if verse_html.matches("</div>").count() != verse_html.matches("<div ").count() {
                return Err("AssertionError:".to_string());
            }
        }

        // Namespace this verse's footnote ids/hrefs per version so the same
        // fn1 doesn't collide across versions on a parallel page.
        verse_html = verse_html
            .replace(
                "id=\"footnotes",
                &format!("id=\"footnotes{version_abbreviation}"),
            )
            .replace("id=\"fn", &format!("id=\"fn{version_abbreviation}"))
            .replace("href=\"#fn", &format!("href=\"#fn{version_abbreviation}"));

        // Py: verseHtml, footnoteHtml = verseHtml.split( '<hr ', 1 )
        let split_at = verse_html.find("<hr ").ok_or_else(|| {
            // Never an assert: under python -O this is the same ValueError that
            // split() raises when the '<hr ' separator is missing.
            "ValueError: not enough values to unpack (expected 2, got 1)".to_string()
        })?;
        let footnote_html = verse_html[split_at + "<hr ".len()..].to_string();
        verse_html = verse_html[..split_at].to_string();

        // Py: verseHtml.rstrip()
        verse_html = verse_html.trim_end().to_string();

        // Py: footnoteFreeVerseHtml, numFootnotesRemoved = footnoteRegex.subn( '', verseHtml )
        //     (the removal count is computed but never used)
        let footnote_free_verse_html = FNCALLER_REGEX.replace_all(&verse_html, "").to_string();

        Ok((verse_html, footnote_free_verse_html, format!("<hr {footnote_html}")))
    } else {
        if verse_html.contains("class=\"footnotes\"") {
            // Py: print( "{versionAbbreviation} {verseHtml=}" ); assert False, "We want to stop here"
            eprintln!("{{versionAbbreviation}} {{verseHtml=}}");
            if strict {
                return Err("AssertionError: We want to stop here".to_string());
            }
        }
        if strict && version_abbreviation != "OET-RV" && verse_html.contains("<hr ") {
            // Py: assert '<hr ' not in verseHtml, f'{versionAbbreviation=} {verseHtml=}'
            return Err(format!(
                "AssertionError: versionAbbreviation={} verseHtml={}",
                py_repr(version_abbreviation),
                py_repr(&verse_html)
            ));
        }
        Ok((verse_html.clone(), verse_html, String::new()))
    }
}

// ── Unit tests ──────────────────────────────────────────────────────────────
// Expected outputs below were captured from the Python originals
// (Python asserts active → every "Ok" fixture also passes a strict
// `checkHtml(..., segmentOnly=True)`).
#[cfg(test)]
mod tests {
    use super::*;

    fn rv(input: &str) -> String {
        do_oet_rv_html_customisations("T", input).expect("RV customisation should succeed")
    }
    fn lv(input: &str) -> String {
        do_oet_lv_html_customisations("T", input).expect("LV customisation should succeed")
    }

    // -- OET-RV --
    #[test]
    fn rv_plain_add() {
        assert_eq!(
            rv(r#"<span class="add">word</span>"#),
            r#"<span class="RVadd" title="added info">word</span>"#
        );
    }

    #[test]
    fn rv_add_link_and_span_protection() {
        let input = r#"<span class="add"><a title="x" href="y.htm">w</a></span> <span class="add"><span class="noLinkYet">s</span></span>"#;
        let expected = r#"<span class="RVadd" title="added info"><a title="x" href="y.htm">w</a></span> <span class="RVadd" title="added info"><span class="noLinkYet">s</span></span>"#;
        assert_eq!(rv(input), expected);
    }

    #[test]
    fn rv_unsure_add() {
        assert_eq!(
            rv(r#"<span class="add">?<a title="x">w</a></span>"#),
            r#"<span class="RVadd unsure" title="added info (less certain)"><a title="x">w</a></span>"#
        );
    }

    #[test]
    fn rv_direct_object() {
        assert_eq!(
            rv(r#"<span class="add"><strong>x</strong></span>"#),
            r#"<span class="addDirectObject" title="added direct object">strong>x</strong></span>"#
        );
    }

    #[test]
    fn rv_add_symbol_chain() {
        // Each symbol replaces (consumes) its '<span class="add">' opener; the
        // closers pass through unchanged, keeping the snippet strict-check-clean.
        let input = r#"<span class="add">?><span class="add">><span class="add">?+<span class="add">+</span></span></span></span>"#;
        let expected = r#"<span class="addExtra unsure" title="added implied info (less certain)"><span class="addExtra" title="added implied info"><span class="addArticle unsure" title="added article (less certain)"><span class="addArticle" title="added article"></span></span></span></span>"#;
        assert_eq!(rv(input), expected);
    }

    #[test]
    fn rv_parallelism_markers() {
        let input = "≈ and ^ and → and plain ≈tail";
        let expected = "<span class=\"synonParr\" title=\"synonymous parallelism\">≈\u{202F}</span> and <span class=\"antiParr\" title=\"antithetic parallelism\">^\u{202F}</span> and <span class=\"synthParr\" title=\"synthetic parallelism\">→\u{202F}</span> and plain <span class=\"synonParr\" title=\"synonymous parallelism\">≈\u{202F}</span>tail";
        assert_eq!(rv(input), expected);
    }

    // Pre-existing `<span class="RVadd">` spans exercise the scan-loop escape
    // prefixes (`<a title`, `<span class="wj">`, `<span class="nominaSacra">`)
    // and the allowed-next-character check.
    #[test]
    fn rv_scan_escapes_and_charset() {
        let cases = [
            (
                r#"<span class="RVadd"><span class="wj">w</span></span>"#,
                r#"<span class="RVadd"><span class="wj">w</span></span>"#,
            ),
            (
                r#"<span class="RVadd">RAW-alpha</span>"#,
                r#"<span class="RVadd">RAW-alpha</span>"#,
            ),
            (
                r#"<span class="RVadd">123☺</span>"#,
                r#"<span class="RVadd">123☺</span>"#,
            ),
            (
                r#"<span class="RVadd"><a title="x">w</a></span>"#,
                r#"<span class="RVadd"><a title="x">w</a></span>"#,
            ),
            (
                r#"<span class="RVadd"><span class="nominaSacra">w</span></span>"#,
                r#"<span class="RVadd"><span class="nominaSacra">w</span></span>"#,
            ),
        ];
        for (input, expected) in cases {
            assert_eq!(rv(input), expected, "for input {input:?}");
        }
    }

    #[test]
    fn rv_rejects_equals_add() {
        // Py: assert '<span class="add">=' not in OET_RV_html  (OET-LV only)
        let err = do_oet_rv_html_customisations(
            "T",
            r#"<span class="add">=copula</span>"#,
        )
        .unwrap_err();
        assert!(err.contains("AssertionError"), "got {err:?}");
    }

    #[test]
    fn rv_rejects_bad_next_char_after_rvadd() {
        // Py: assert nextChar.isalpha() or nextChar in '(，‘’—123☺'
        let err = do_oet_rv_html_customisations("T", r#"<span class="RVadd">=</span>"#)
            .unwrap_err();
        assert!(err.contains("AssertionError"), "got {err:?}");
    }

    // -- OET-LV --
    #[test]
    fn lv_protects_digit_punct_digit() {
        // 12:30, JOB_1:2, v0.1 and "GEN_1:1" must survive the punctuation
        // replacement (the digit-punct loop runs with character indices).
        assert_eq!(
            lv(r#"12:30 and JOB_1:2 and v0.1 and "GEN_1:1""#),
            r#"12:30 and JOB<span class="ul">_</span>1:2 and v0.1 and "GEN<span class="ul">_</span>1:1""#
        );
    }

    #[test]
    fn lv_protects_digit_punct_with_multibyte() {
        // Multibyte chars before the match must not shift the char-index
        // semantics of the protect loop.
        assert_eq!(
            lv("אב 12:30 ג JOB_1:2 ד and v0.1 tail"),
            "אב 12:30 ג JOB<span class=\"ul\">_</span>1:2 ד and v0.1 tail"
        );
    }

    #[test]
    fn lv_sentences_break() {
        assert_eq!(
            lv("First sentence. Second? Third! Fourth: end."),
            "First sentence.\n<br> Second?\n<br> Third!\n<br> Fourth:\n<br> end."
        );
    }

    #[test]
    fn lv_protects_paths_and_backslash_f() {
        assert_eq!(
            lv(r"../x.htm and ../../y.org/index.html and data.tsv and z.\f*"),
            r"../x.htm and ../../y.org/index.html and data.tsv and z.\f*"
        );
    }

    #[test]
    fn lv_dom_span() {
        assert_eq!(
            lv("THE DOM field"),
            "THE <span class=\"dom\">DOM</span> field"
        );
    }

    #[test]
    fn lv_equals_divide_to_underlines() {
        assert_eq!(
            lv(r#"a="b" c=d e÷f and x=y"#),
            r#"a="b" c<span class="ul">_</span>d e<span class="ul">_</span>f and x<span class="ul">_</span>y"#
        );
    }

    #[test]
    fn lv_add_markers() {
        let input = r#"<span class="add">+art</span><span class="add">=cop</span><span class="add"><a title="x">deep</a></span><span class="add"><x></span><span class="add">>extra</span><span class="add">&own</span>"#;
        let expected = r#"<span class="addArticle">art</span><span class="addCopula">cop</span><span class="add"><a title="x">deep</a></span><span class="addDirectObject">x></span><span class="addExtra">extra</span><span class="addOwner">own</span>"#;
        assert_eq!(lv(input), expected);
    }

    #[test]
    fn lv_footnote_caller() {
        let input = r##"<span class="fnCaller"><a title="Note: K אחד" href="#fnUHB4">fn</a></span>For Example: one." end."##;
        let expected = r##"<span class="fnCaller"><a title="Note: K אחד" href="#fnUHB4">fn</a></span>For Example:
<br> one." end."##;
        assert_eq!(lv(input), expected);
    }

    #[test]
    fn lv_verse_text_chunk_closing_span_before_br() {
        let input = r#"<span id="V1"></span><span class="v" id="C2V1"><a href="x.htm">1</a></span><span class="OET-LV_verseTextChunk">And they came.</span> "#;
        let expected = r#"<span id="V1"></span><span class="v" id="C2V1"><a href="x.htm">1</a></span><span class="OET-LV_verseTextChunk">And they came.</span>
<br> "#;
        assert_eq!(lv(input), expected);
    }

    #[test]
    fn lv_hr_styles_untouched() {
        assert_eq!(
            lv("<hr width:50px margin-left:10px margin-top:5px />"),
            "<hr width:50px margin-left:10px margin-top:5px />"
        );
    }

    #[test]
    fn lv_fn_codes_and_underlines() {
        assert_eq!(
            lv("--fnUNDERLINE----fnEQUAL----fnCOLON----fnPERIOD-- and v_text_v and _Vat"),
            "_=:. and v<span class=\"ul\">_</span>text<span class=\"ul\">_</span>v and _Vat"
        );
    }

    #[test]
    fn lv_sequential_digit_punct() {
        assert_eq!(lv("v1.20 v0.5"), "v1.20 v0.5");
    }

    #[test]
    fn lv_rejects_wasted_br_input() {
        // Py: assert '\n<br></p>' not in OET_LV_html ...
        let err = do_oet_lv_html_customisations("T", "line.\n<br></p>done.").unwrap_err();
        assert!(err.contains("AssertionError: Wasted <br>"), "got {err:?}");
    }

    // -- LSV --
    #[test]
    fn lsv_double_pipes() {
        assert_eq!(
            do_lsv_html_customisations("T", "a || b and ||c|| and d || e"),
            "a<br>b and <br>c<br> and d<br>e"
        );
        assert_eq!(do_lsv_html_customisations("T", "||x||"), "<br>x<br>");
    }

    // -- T4T --
    #[test]
    fn t4t_single_fos() {
        let input = "Say [EUP], and [SIL] and [birth MET],";
        let expected = "Say <span class=\"t4tFoS\" title=\"euphemism (figure of speech)\">[EUP]</span>, and <span class=\"t4tFoS\" title=\"simile (figure of speech)\">[SIM]</span> and [birth <span class=\"t4tFoS\" title=\"metaphor (figure of speech)\">[MET]</span>,";
        assert_eq!(
            do_t4t_html_customisations("T", input).expect("T4T should succeed"),
            expected
        );
    }

    #[test]
    fn t4t_pair_fos() {
        let input = "It was [EUP, MTY] like [EUP/MTY] and a ◄ alt";
        let expected = "It was [<span class=\"t4tFoS\" title=\"euphemism (figure of speech)\">EUP</span>, <span class=\"t4tFoS\" title=\"metonymy (figure of speech)\">MTY</span>] like [<span class=\"t4tFoS\" title=\"euphemism (figure of speech)\">EUP</span>/<span class=\"t4tFoS\" title=\"metonymy (figure of speech)\">MTY</span>] and a <span title=\"alternative translation\">◄</span> alt";
        assert_eq!(
            do_t4t_html_customisations("T", input).expect("T4T should succeed"),
            expected
        );
    }

    #[test]
    fn t4t_multiple_pairs() {
        let input = "[APO, CHI],[DOU/EUP],[HEN, HYP]";
        let expected = "[<span class=\"t4tFoS\" title=\"apostrophe (figure of speech)\">APO</span>, <span class=\"t4tFoS\" title=\"chiasmus (figure of speech)\">CHI</span>],[<span class=\"t4tFoS\" title=\"doublet (figure of speech)\">DOU</span>/<span class=\"t4tFoS\" title=\"euphemism (figure of speech)\">EUP</span>],[<span class=\"t4tFoS\" title=\"hendiadys (figure of speech)\">HEN</span>, <span class=\"t4tFoS\" title=\"hyperbole (figure of speech)\">HYP</span>]";
        assert_eq!(
            do_t4t_html_customisations("T", input).expect("T4T should succeed"),
            expected
        );
    }

    #[test]
    fn t4t_leaves_plain_text_and_alt_marker() {
        assert_eq!(
            do_t4t_html_customisations("T", "No figures here. ◄")
                .expect("plain text should succeed"),
            "No figures here. <span title=\"alternative translation\">◄</span>"
        );
    }

    #[test]
    fn t4t_rejects_leftover_fos_pair() {
        // Py: assert f'{FoS2}]' not in T4T_html  (leaves an 'EUP]' behind)
        let err = do_t4t_html_customisations("T", "divided [EUP, MTY/EUP] mid").unwrap_err();
        assert!(err.contains("AssertionError"), "got {err:?}");
    }

    // -- convert_adds_to_italics --
    #[test]
    fn cati_plain_add() {
        assert_eq!(
            do_convert_adds_to_italics(r#"<span class="add">word</span>"#).expect("no-op"),
            r#"<i>word</i>"#
        );
    }

    #[test]
    fn cati_multiple_adds() {
        assert_eq!(
            do_convert_adds_to_italics(
                r#"a<span class="add">one</span>b<span class="add">two</span>c"#
            )
            .expect("no-op"),
            r#"a<i>one</i>b<i>two</i>c"#
        );
    }

    #[test]
    fn cati_multibyte_before_add() {
        // ix is a byte index found by find(); the slice result[ix..] must not
        // split a UTF-8 sequence when multibyte chars precede the marker.
        assert_eq!(
            do_convert_adds_to_italics("בְּרֵאשִׁית <span class=\"add\">x</span>")
                .expect("no-op"),
            "בְּרֵאשִׁית <i>x</i>"
        );
    }

    #[test]
    fn cati_unterminated_add_keeps_markers() {
        // No closing '</span>' → Python's inner replace is a no-op; so is ours.
        assert_eq!(
            do_convert_adds_to_italics("x<span class=\"add\">y").expect("no-op"),
            "x<i>y"
        );
    }

    #[test]
    fn cati_twenty_nine_adds_ok() {
        let input = r#"<span class="add">a</span>"#.repeat(29);
        let out = do_convert_adds_to_italics(&input).expect("29 adds is fine");
        assert_eq!(out, "<i>a</i>".repeat(29));
    }

    #[test]
    fn cati_thirty_adds_fires_name_error() {
        // Py: `for-else: not_enough_loops` — a plain NameError (not an assert),
        // so it fires even under python -O / non-strict builds.
        let input = r#"<span class="add">a</span>"#.repeat(30);
        let err = do_convert_adds_to_italics(&input).unwrap_err();
        assert_eq!(err, "NameError: name 'not_enough_loops' is not defined");
    }

    // -- handleAndExtractFootnotes --
    fn han(input: &str) -> (String, String, String) {
        do_handle_and_extract_footnotes("ABC", input).expect("should succeed")
    }

    #[test]
    fn han_no_footnotes_div_passthrough() {
        assert_eq!(
            han("plain verse text"),
            ("plain verse text".to_string(), "plain verse text".to_string(), String::new())
        );
    }

    #[test]
    fn han_full_split_and_namespacing() {
        let input = concat!(
            "text <span class=\"fnCaller\">[<a title=\"K\" href=\"#fnUHB1\">fn</a>]</span>\n",
            "<div id=\"footnotes\" class=\"footnotes\">\n",
            "<hr class=\"none\">\n",
            "<div id=\"fnUHB1\">1</div>\n",
            "</div>\n",
        );
        let (verse_html, footnote_free, footnotes_html) = han(input);
        // fnCaller stays in the main text; footnote ids/hrefs are namespaced.
        assert_eq!(
            verse_html,
            concat!(
                "text <span class=\"fnCaller\">[<a title=\"K\" href=\"#fnABCUHB1\">fn</a>]</span>\n",
                "<div id=\"footnotesABC\" class=\"footnotes\">",
            )
        );
        // The free-text copy has the callers stripped…
        assert_eq!(
            footnote_free,
            concat!("text \n", "<div id=\"footnotesABC\" class=\"footnotes\">",)
        );
        assert_eq!(footnotes_html, "<hr class=\"none\">\n<div id=\"fnABCUHB1\">1</div>\n</div>\n");
    }

    #[test]
    fn han_fncaller_across_newline_not_removed() {
        // Python's '.' excludes '\n', so a caller spanning lines is untouched.
        let input = concat!(
            "a<span class=\"fnCaller\">one\ntwo</span>b\n",
            "<div id=\"footnotes\" class=\"footnotes\">\n<hr x>\n</div>\n",
        );
        let (verse_html, footnote_free, _footnotes_html) = han(input);
        assert!(verse_html.contains("<span class=\"fnCaller\">one\ntwo</span>"), "got {verse_html:?}");
        assert!(footnote_free.contains("<span class=\"fnCaller\">one\ntwo</span>"), "got {footnote_free:?}");
    }

    #[test]
    fn han_missing_hr_fires_assert() {
        // Py: assert verseHtml.count('<hr ') >= 1, f'{versionAbbreviation} ({...}) {verseHtml=}'
        //     (fires here in strict mode; under python -O this same input reaches the
        //     split's ValueError — covered by the non-strict Python harness)
        let err = do_handle_and_extract_footnotes(
            "ABC",
            "<div id=\"footnotes\" class=\"footnotes\">\n</div>\n",
        )
        .unwrap_err();
        assert_eq!(
            err,
            "AssertionError: ABC (0) verseHtml='<div id=\"footnotes\" class=\"footnotes\">\\n</div>\\n'"
        );
    }

    #[test]
    fn han_unbalanced_divs_fires_assert() {
        // Py: assert verseHtml.count('</div>') == verseHtml.count('<div ')
        let err = do_handle_and_extract_footnotes(
            "ABC",
            "<div id=\"footnotes\" class=\"footnotes\">\n<hr x>\n</div></div>\n",
        )
        .unwrap_err();
        assert_eq!(err, "AssertionError:");
    }

    #[test]
    fn han_stray_hr_in_non_oetrv_fires_assert() {
        // Py: assert '<hr ' not in verseHtml, f'{versionAbbreviation=} {verseHtml=}'
        let err = do_handle_and_extract_footnotes("ABC", "stray <hr here").unwrap_err();
        assert_eq!(
            err,
            "AssertionError: versionAbbreviation='ABC' verseHtml='stray <hr here'"
        );
    }

    #[test]
    fn han_stray_hr_in_oetrv_allowed() {
        // The stray-'<hr' assert is skipped for OET-RV.
        assert_eq!(
            do_handle_and_extract_footnotes("OET-RV", "stray <hr here")
                .expect("OET-RV allows stray hr"),
            ("stray <hr here".to_string(), "stray <hr here".to_string(), String::new())
        );
    }

    #[test]
    fn han_we_want_to_stop_here_trap() {
        // 'class="footnotes"' present but the full footnotes-div is not.
        let err = do_handle_and_extract_footnotes("ABC", "x class=\"footnotes\" y").unwrap_err();
        assert_eq!(err, "AssertionError: We want to stop here");
    }
}