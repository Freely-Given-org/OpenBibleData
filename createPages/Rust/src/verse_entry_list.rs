//! Port of `convertVerseEntryListToHtml` from `usfm.py`.
//!
//! This module contains the main verse-entry-to-HTML conversion pipeline
//! which loops through processed USFM line entries and produces a complete
//! HTML segment.

use crate::character_formatting::convert_usfm_character_formatting;
use crate::constants::*;
use crate::intro_links::liven_introduction_links_core;
use crate::ior_links::liven_iors_core;
use crate::oet_books::get_bbb_from_oet_book_name;
use crate::roman_numerals::to_roman_numerals;

/// 27 New Testament book codes (Matthew through Revelation).
pub const BOOKLIST_NT27: &[&str] = &[
    "MAT", "MRK", "LUK", "JHN", "ACT", "ROM", "CO1", "CO2", "GAL",
    "EPH", "PHP", "COL", "TH1", "TH2", "TI1", "TI2", "TIT", "PHM",
    "HEB", "JAM", "PE1", "PE2", "JN1", "JN2", "JN3", "JDE", "REV",
];

// ─── Data structures ───────────────────────────────────────────────────────

/// A single processed USFM line entry extracted from Python's `InternalBibleEntry`.
#[derive(Debug, Clone)]
pub struct VerseEntry {
    pub marker: String,
    pub full_text: String,
    pub clean_text: String,
}

/// Tracks the state of an open list entry.
#[derive(Debug, Clone, PartialEq)]
pub enum ListEntry {
    None,
    Generic,
    Specific(String),
}

/// Internal state machine for the conversion loop.
#[derive(Debug)]
struct ConvertState {
    in_main_div: Option<String>,
    in_paragraph: Option<String>,
    in_section: Option<String>,
    in_list: Option<String>,
    in_list_entry: ListEntry,
    in_table: Option<String>,
    in_table_row: Option<String>,
    in_sp_div: Option<String>,
    in_right_div: Option<String>,
    c_printed: bool,
    just_had_d: bool,
    c_value: String,
    v_value: String,
    background_colour: Option<String>,
    last_marker: String,
}

// ─── Errors ────────────────────────────────────────────────────────────────

#[derive(Debug)]
pub enum ConvertError {
    AssertionFailed(String),
    LeftoverBackslash(String),
    VerseToHtml(String),
}

impl std::fmt::Display for ConvertError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::AssertionFailed(msg) => write!(f, "Assertion failed: {msg}"),
            Self::LeftoverBackslash(msg) => write!(f, "Leftover backslash: {msg}"),
            Self::VerseToHtml(msg) => write!(f, "VerseToHtml: {msg}"),
        }
    }
}

impl std::error::Error for ConvertError {}

impl From<crate::verse_to_html::VerseToHtmlError> for ConvertError {
    fn from(e: crate::verse_to_html::VerseToHtmlError) -> Self {
        Self::VerseToHtml(e.to_string())
    }
}

// ─── Helpers ───────────────────────────────────────────────────────────────

/// Replace `count` occurrences of `old` with `new`, starting from the *right*.
fn rreplace(s: &str, old: &str, new: &str, count: usize) -> String {
    let parts: Vec<&str> = s.rsplitn(count + 1, old).collect();
    if parts.len() <= 1 {
        return s.to_string();
    }
    // parts is reversed from rsplitn: [rightmost, ..., leftmost]
    let mut result = String::new();
    // The first element is the rightmost (unsplit) part
    result.push_str(parts[parts.len() - 1]);
    for i in (0..parts.len() - 1).rev() {
        result.push_str(new);
        result.push_str(parts[i]);
    }
    result
}

/// Parse the leading integer from a string (like Python's `getSmallLeadingInt`).
fn get_small_leading_int(s: &str) -> usize {
    let digits: String = s.chars().take_while(|c| c.is_ascii_digit()).collect();
    digits.parse().unwrap_or(0)
}

/// Check if a marker is in the USFM Bible paragraph markers list.
fn is_bible_paragraph_marker(marker: &str) -> bool {
    use usfm_markers::USFM_ALL_BIBLE_PARAGRAPH_MARKERS;
    USFM_ALL_BIBLE_PARAGRAPH_MARKERS.contains(&marker)
}

/// Format chapter number as roman numerals for KJB-1611, else plain string.
fn fmt_chapter(va: &str, c: &str) -> String {
    if va == "KJB-1611" {
        c.parse::<u32>().map_or_else(
            |e| { eprintln!("Warning: could not parse chapter number '{c}': {e}"); c.to_string() },
            |n| to_roman_numerals(n),
        )
    } else {
        c.to_string()
    }
}

/// Copy a source image file to a destination folder with a given filename.
/// Logs errors instead of panicking.
pub fn copy_figure_file(src_path: &str, dest_folder: &str, dest_filename: &str) {
    use std::path::Path;
    let dest_path = Path::new(dest_folder).join(dest_filename);
    if let Err(e) = std::fs::copy(src_path, &dest_path) {
        eprintln!(
            "Warning: could not copy figure '{}' → '{}': {}",
            src_path,
            dest_path.display(),
            e
        );
    }
}

// ─── livenSectionReferences (ported from Python) ───────────────────────────

/// Given some text (from USFM `\r` field), convert the list of references
/// into live links.  Port of `livenSectionReferences` from `createSectionPages.py`.
///
/// `is_book_available` returns true if a book should be linked (checked against `state.booksToLoad`).
pub fn liven_section_references_core<FSect, FAvail>(
    version_abbreviation: &str,
    _ref_tuple: (&str, &str, &str),
    segment_type: &str,
    section_reference_text: &str,
    find_section_fn: FSect,
    is_book_available: FAvail,
) -> String
where
    FSect: Fn(&str, &str, &str, &str) -> Option<usize>,
    FAvail: Fn(&str, &str) -> bool,
{
    let text = section_reference_text;
    let enclosed = text.starts_with('(') && text.ends_with(')');
    let inner = if enclosed { &text[1..text.len() - 1] } else { text };

    let normalised = inner.replace(';', ",,").replace(", ", ",");
    let tokens: Vec<&str> = normalised.split(',').collect();
    let mut result_html = String::new();
    let mut current_bbb: Option<&str> = None;

    for (n, token) in tokens.iter().enumerate() {
        if token.is_empty() {
            continue;
        }
        let delimiter = if n == 0 { "" } else if n < 2 { ", " } else { "; " };

        let looks_like_book_prefix = token.starts_with("1 ")
            || token.starts_with("2 ")
            || token.starts_with("3 ")
            || token.starts_with("I ")
            || token.starts_with("II ")
            || token.starts_with("III ")
            || token.starts_with("Song of");

        if looks_like_book_prefix && token.matches(' ').count() >= 2 {
            if let Some((book_part, rest_part)) = token.rsplit_once(' ') {
                let book_upper: String = book_part.chars()
                    .filter(|c| !c.is_whitespace() && *c != NARROW_NON_BREAK_SPACE && *c != '.')
                    .map(|c| c.to_ascii_uppercase())
                    .collect();
                if let Some(bbb) = get_bbb_from_oet_book_name(&book_upper) {
                    current_bbb = Some(bbb);
                    let link = build_section_ref_link(
                        version_abbreviation, segment_type, bbb, rest_part,
                        &find_section_fn, &is_book_available,
                    );
                    result_html.push_str(delimiter);
                    if let Some(href) = link {
                        result_html.push_str(&format!(r#"<a href="{href}">{token}</a>"#));
                    } else {
                        result_html.push_str(token);
                    }
                } else {
                    result_html.push_str(delimiter);
                    result_html.push_str(token);
                }
            } else {
                result_html.push_str(delimiter);
                result_html.push_str(token);
            }
        } else if (current_bbb.is_none() || token.chars().next().map_or(false, |c| c.is_ascii_alphabetic()))
            && token.matches(' ').count() == 1
        {
            if let Some((book_part, rest_part)) = token.split_once(' ') {
                let book_upper: String = book_part.chars()
                    .filter(|c| !c.is_whitespace() && *c != NARROW_NON_BREAK_SPACE && *c != '.')
                    .map(|c| c.to_ascii_uppercase())
                    .collect();
                if let Some(bbb) = get_bbb_from_oet_book_name(&book_upper) {
                    current_bbb = Some(bbb);
                    let link = build_section_ref_link(
                        version_abbreviation, segment_type, bbb, rest_part,
                        &find_section_fn, &is_book_available,
                    );
                    result_html.push_str(delimiter);
                    if let Some(href) = link {
                        result_html.push_str(&format!(r#"<a href="{href}">{token}</a>"#));
                    } else {
                        result_html.push_str(token);
                    }
                } else {
                    result_html.push_str(delimiter);
                    result_html.push_str(token);
                }
            } else {
                result_html.push_str(delimiter);
                result_html.push_str(token);
            }
        } else {
            result_html.push_str(delimiter);
            result_html.push_str(token);
        }
    }

    if result_html.is_empty() {
        result_html = inner.to_string();
    }
    if enclosed {
        format!("({result_html})")
    } else {
        result_html
    }
}

/// Build a section reference link for `livenSectionReferences`.
fn build_section_ref_link<FSect, FAvail>(
    version_abbreviation: &str,
    segment_type: &str,
    bbb: &str,
    digits_text: &str,
    find_section_fn: &FSect,
    is_book_available: &FAvail,
) -> Option<String>
where
    FSect: Fn(&str, &str, &str, &str) -> Option<usize>,
    FAvail: Fn(&str, &str) -> bool,
{
    if !is_book_available(version_abbreviation, bbb) {
        return None;
    }
    let adj_digits = digits_text
        .replace('\u{2013}', "-")
        .replace('\u{2014}', "-");
    let cv_part = if let Some(hyphen_ix) = adj_digits.find('-') {
        &adj_digits[..hyphen_ix]
    } else {
        adj_digits.as_ref()
    };

    let colon_count = cv_part.matches(':').count();
    if colon_count != 1 {
        return None;
    }
    let (ref_c, ref_v) = cv_part.split_once(':')?;
    let section_number = find_section_fn(version_abbreviation, bbb, ref_c, ref_v);

    match segment_type {
        "relatedPassage" => {
            if let Some(sn) = section_number {
                Some(format!("../{bbb}/{bbb}_S{sn}.htm#V{ref_v}"))
            } else {
                Some(format!("{bbb}_C{ref_c}.htm#V{ref_v}"))
            }
        }
        "topicalPassage" => Some(format!("{bbb}.htm#C{ref_c}V{ref_v}")),
        "book" => Some(format!("{bbb}.htm#C{ref_c}V{ref_v}")),
        "chapter" => Some(format!("{bbb}_C{ref_c}.htm#V{ref_v}")),
        "section" => {
            if let Some(sn) = section_number {
                Some(format!("{bbb}_S{sn}.htm#V{ref_v}"))
            } else {
                Some(format!("{bbb}_C{ref_c}.htm#V{ref_v}"))
            }
        }
        _ if version_abbreviation.contains("OET")
            && matches!(segment_type, "book" | "chapter" | "section") =>
        {
            if let Some(sn) = section_number {
                Some(format!("../../rel/{bbb}/{bbb}_S{sn}.htm#V{ref_v}"))
            } else {
                None
            }
        }
        _ => Some(format!("{bbb}.htm#C{ref_c}V{ref_v}")),
    }
}

// ─── Main conversion function ──────────────────────────────────────────────

/// Core logic for `convertVerseEntryListToHtml`.
///
/// Takes flat data extracted from Python's `InternalBibleEntry` objects
/// and closure callbacks for operations that must remain in Python.
pub fn convert_verse_entry_list_to_html_core<FCFmt, CCopyFig, FSect, FGetOBI, CCheckHtml>(
    level: usize,
    version_abbreviation: &str,
    bbb: &str,
    c_init: Option<&str>,
    v_init: Option<&str>,
    segment_type: &str,
    context_list: &[&str],
    verse_entries: &[VerseEntry],
    basic_only: bool,
    is_single_chapter_book: bool,
    convert_char_formatting: FCFmt,
    _copy_fig_files: CCopyFig,
    find_section_fn: FSect,
    get_open_bible_images: FGetOBI,
    _check_html: CCheckHtml,
) -> Result<String, ConvertError>
where
    FCFmt: Fn(&str, &str, &str, &str, bool, &mut Option<String>) -> Result<String, ConvertError>,
    CCopyFig: Fn(&[(String, String)]),
    FSect: Fn(&str, &str, &str, &str) -> Option<usize>,
    FGetOBI: Fn(usize, &str, &str, &str, &str) -> Option<String>,
    CCheckHtml: Fn(&str, &str) -> bool,
{
    let _max_footnote_chars = if version_abbreviation == "NET" {
        MAX_NET_FOOTNOTE_CHARS
    } else {
        MAX_FOOTNOTE_CHARS
    };

    let mut state = ConvertState {
        in_main_div: None,
        in_paragraph: None,
        in_section: None,
        in_list: None,
        in_list_entry: ListEntry::None,
        in_table: None,
        in_table_row: None,
        in_sp_div: None,
        in_right_div: None,
        c_printed: true,
        just_had_d: false,
        c_value: c_init.unwrap_or("").to_string(),
        v_value: v_init.unwrap_or("").to_string(),
        background_colour: None,
        last_marker: String::new(),
    };

    let mut html = String::new();

    // --- Process contextList ---
    for ctx_marker in context_list {
        if *ctx_marker == "s1" {
            if !basic_only {
                html.push_str("<div class=\"section\"><p class=\"s1\">--unknown--</p><!--section-->\n");
                state.in_section = Some("s1".to_string());
            }
        } else if *ctx_marker == "p" {
            if !basic_only {
                html.push_str("<p class=\"p\">\n");
                state.in_paragraph = Some("p".to_string());
            }
        } else if segment_type.ends_with("Verse") {
            // chapters and c are expected; others are unexpected
        } else if *ctx_marker != "chapters" && *ctx_marker != "c" {
            // Some versions have 'list' context for EXO/NUM
        }
    }

    for (vel_index, entry) in verse_entries.iter().enumerate() {
        let mut marker = entry.marker.as_str();
        let mut rest = entry.full_text.as_str();

        // nb substitution at chapter start
        if marker == "nb" && segment_type == "chapter" {
            if let Some(last_ctx) = context_list.last() {
                if is_bible_paragraph_marker(last_ctx) {
                    marker = last_ctx;
                }
            }
        }

        if !rest.is_empty() {
            // OET apostrophe normalisation
            if version_abbreviation.contains("OET") {
                rest = ""; // handled via owned string below
            }
        }

        let mut owned_rest = if version_abbreviation.contains("OET") && !entry.full_text.is_empty() {
            entry.full_text.replace('\'', "\u{2019}") // replace ASCII apostrophe with right single quotation mark
        } else if version_abbreviation == "ULT" || version_abbreviation == "UST" {
            entry.full_text.replace('{', "\\add ").replace('}', "\\add*")
        } else if version_abbreviation == "Cvdl" {
            entry.full_text.replace("LORDE", "\\nd LORDE\\nd*")
        } else if version_abbreviation == "Luth" {
            entry.full_text.replace("HErrn", "HErr\u{2019}s").replace("HErr", "\\nd HErr\\nd*")
        } else {
            entry.full_text.replace("\\nd  ", "\\nd ")
        };

        // NNBSP insertion
        if !owned_rest.is_empty() {
            owned_rest = owned_rest
                .replace("\u{2019}\u{201D}", "\u{2019}\u{202F}\u{201D}")
                .replace("\u{2019} \u{201D}", "\u{2019}\u{202F}\u{201D}")
                .replace("\u{201D}\u{2019}", "\u{201D}\u{202F}\u{2019}")
                .replace("\u{201D} \u{2019}", "\u{201D}\u{202F}\u{2019}");
        }

        // Strip xrefs/footnotes in basicOnly mode
        if basic_only && !owned_rest.is_empty() {
            if (version_abbreviation != "OET-RV" || segment_type != "parallelVerse")
                && owned_rest.contains("\\x ")
            {
                owned_rest = XREF_REGEX.replace_all(&owned_rest, "").to_string();
            }
            if basic_only && segment_type == "dictVerse" && owned_rest.contains("\\f ") {
                owned_rest = FOOTNOTE_REGEX.replace_all(&owned_rest, "").to_string();
            }
        }

        let rest_str = owned_rest.as_str();
        let c_owned = state.c_value.clone();
        let c = c_owned.as_str();
        let v_owned = state.v_value.clone();
        let v = v_owned.as_str();

        // ── Marker dispatch ──
        match marker {
            "v~" => {
                // Verse text content
                let formatted = convert_char_formatting(
                    version_abbreviation, bbb, segment_type, rest_str, basic_only,
                    &mut state.background_colour,
                )?;
                let span_class = if v == "0" {
                    format!("{version_abbreviation}_chapterIntro")
                } else {
                    format!("{version_abbreviation}_verseTextChunk")
                };
                html.push_str(&format!(r#"<span class="{span_class}">{formatted}</span>"#));
            }
            "v" => {
                state.v_value = rest_str.trim().to_string();
                let v = state.v_value.as_str();  // use the current verse number, not the stale clone
                // Show verse numbers except for single parallel/interlinear verses
                if !(segment_type == "parallelVerse" || segment_type == "interlinearVerse")
                    || v.contains('-')
                {
                    if !v.is_empty() && v.contains('-') {
                        // Verse range
                        let parts: Vec<&str> = v.splitn(2, '-').collect();
                        let v1 = parts[0];
                        let v2 = if parts.len() > 1 { parts[1] } else { "" };
                        if segment_type == "parallelVerse" || segment_type == "interlinearVerse" {
                            html.push_str(&format!(
                                r#"{rest_str}<span class="v">{v1}</span>{THIN_SPACE}"#
                            ));
                        } else {
                            let id_v1 = if segment_type == "dictVerse" { "" } else { &format!(" id=\"C{c}V{v1}\"") };
                            let id_v2 = if segment_type == "dictVerse" { "" } else { &format!(" id=\"C{c}V{v2}\"") };
                            let psa_class = if bbb == "PSA" { "cPsa" } else { "c" };
                            let mut verse_html = String::new();
                            if v1 == "1" && !state.c_printed {
                                let c_id = format!(r#"<span id="C{c}"></span>"#);
                                let c_link = format!(r#"<a title="Go to verse in parallel view" href="{}par/{bbb}/C{c}V1.htm#Top">{}</a>"#,
                                    "../".repeat(level), fmt_chapter(version_abbreviation, c));
                                state.c_printed = true;
                                verse_html.push_str(&format!("{c_id}<span class=\"{psa_class}\" id=\"C{c}V1\">{c_link}</span>"));
                            } else {
                                let v_link = format!(r#"<a title="Go to verse in parallel view" href="{}par/{bbb}/C{c}V{v1}.htm#Top">{v1}</a>"#, "../".repeat(level));
                                verse_html.push_str(&format!(r#"<span class="v"{id_v1}>{v_link}-</span>"#));
                            }
                            // V anchor IDs
                            if matches!(segment_type, "chapter" | "section" | "relatedPassage") || is_single_chapter_book {
                                if !html.contains(&format!("id=\"V{v1}\"")) {
                                    verse_html.push_str(&format!(r#"<span id="V{v1}"></span>"#));
                                }
                                if !html.contains(&format!("id=\"V{v2}\"")) {
                                    verse_html.push_str(&format!(r#"<span id="V{v2}"></span>"#));
                                }
                            }
                            verse_html.push_str(&format!(r#"<span class="v"{id_v2}>{v2}{NARROW_NON_BREAK_SPACE}</span>"#));
                            if !rest_str.is_empty() {
                                verse_html.push_str(rest_str);
                            } else {
                                verse_html.push_str("=Opaque=");
                            }
                            html.push_str(&verse_html);
                        }
                    } else {
                        // Simple verse number
                        let v_link = format!(r#"<a title="Go to verse in parallel view" href="{}par/{bbb}/C{c}V{v}.htm#Top">{v}</a>"#, "../".repeat(level));
                        let id_field = if segment_type == "dictVerse" { "" } else { &format!(" id=\"C{c}V{v}\"") };
                        let psa_class = if bbb == "PSA" { "cPsa" } else { "c" };
                        let mut verse_html = String::new();
                        // Anchor IDs
                        if matches!(segment_type, "chapter" | "section" | "relatedPassage") || is_single_chapter_book {
                            if !html.contains(&format!("id=\"V{v}\"")) {
                                verse_html.push_str(&format!(r#"<span id="V{v}"></span>"#));
                            }
                        }
                        if v == "1" && !state.just_had_d {
                            let c_id = if state.c_printed { "" } else {
                                state.c_printed = true;
                                &format!(r#"<span id="C{c}"></span>"#)
                            };
                            let c_link = if state.c_printed && v == "1" {
                                format!(r#"<a title="Go to verse in parallel view" href="{}par/{bbb}/C{c}V1.htm#Top">{}</a>"#,
                                    "../".repeat(level), fmt_chapter(version_abbreviation, c))
                            } else {
                                v_link.clone()
                            };
                            verse_html.push_str(&format!("{c_id}<span class=\"{psa_class}\"{id_field}>{c_link}{NARROW_NON_BREAK_SPACE}</span>"));
                        } else {
                            verse_html.push_str(&format!(r#"<span class="v"{id_field}>{v_link}{NARROW_NON_BREAK_SPACE}</span>"#));
                        }
                        html.push_str(&verse_html);
                    }
                }
                state.just_had_d = false;
                // OET-RV images
                if version_abbreviation == "OET-RV" && matches!(segment_type, "chapter" | "section" | "book" | "relatedPassage") {
                    if let Some(obi_html) = get_open_bible_images(level, segment_type, bbb, c, v) {
                        html.push_str(&obi_html);
                    }
                }
            }
            "\u{AC}v" => {
                // End verse marker — ignore
            }
            "v=" => {
                // Section start verse
                if rest_str.is_empty() || !rest_str.chars().next().map_or(false, |c| c.is_ascii_digit()) {
                    // skip
                } else if vel_index == verse_entries.len() - 1 {
                    // Last entry, ignore
                } else {
                    let next_marker = &verse_entries[vel_index + 1].marker;
                    if next_marker == "s4" {
                        continue;
                    }
                    state.v_value = rest_str.trim().to_string();
                }
            }

            // ── Paragraph markers ──
            "p" | "q1" | "q2" | "q3" | "q4" | "m" | "mi"
            | "pi1" | "pi2" | "pc" | "pm" | "pmc" | "pmo" | "po" | "pr"
            | "qm1" | "qm2" | "qr" | "cls" => {
                if let Some(refimd) = state.in_main_div.take() {
                    html.push_str(&format!("</div><!--{refimd}-->\n"));
                }
                if let Some(ref_right) = state.in_right_div.take() {
                    html.push_str(&format!("</div><!--{ref_right}-->\n"));
                }
                if state.in_paragraph.is_some() {
                    if let Some(ref_ip) = state.in_paragraph.take() {
                        html.push_str(&format!("</p><!--{ip}-->\n", ip = ref_ip));
                    }
                }
                if state.in_table_row.is_some() {
                    state.in_table_row = None;
                    html.push_str("</tr>\n");
                }
                if state.in_table.is_some() {
                    state.in_table = None;
                    html.push_str("</table>\n");
                }
                if state.in_list.is_some() {
                    close_list(&mut html, &mut state);
                }
                if basic_only {
                    if !html.is_empty() {
                        let indent = if marker.contains('1') { "\u{2002}" }
                            else if marker.contains('2') { "\u{2003}" }
                            else { "\u{00A0}" };
                        let pilcrow = if marker.contains('p') { "\u{00B6}" }
                            else if marker.contains('q') { "\u{21D4}" }
                            else { "\u{00A7}" };
                        html.push_str(&format!("<br>{indent}{pilcrow}{NARROW_NON_BREAK_SPACE}\n"));
                    }
                } else if version_abbreviation != "OET-LV" {
                    html.push_str(&(format!(r#"<p class="{marker}">"#) + "\n"));
                    state.in_paragraph = Some(marker.to_string());
                }
            }
            "\u{AC}p" | "\u{AC}q1" | "\u{AC}q2" | "\u{AC}q3" | "\u{AC}q4"
            | "\u{AC}m" | "\u{AC}mi" | "\u{AC}pi1" | "\u{AC}pi2"
            | "\u{AC}pc" | "\u{AC}pm" | "\u{AC}pmc" | "\u{AC}pmo"
            | "\u{AC}po" | "\u{AC}pr" | "\u{AC}qm1" | "\u{AC}qm2"
            | "\u{AC}qr" | "\u{AC}cls" => {
                if !basic_only {
                    if let Some(ref_ip) = state.in_paragraph.take() {
                        html.push_str(&format!("</p><!--{ip}-->\n", ip = ref_ip));
                    }
                }
            }

            // ── NB markers ──
            "nb" => {
                // Chapter start — essentially a no-op in most versions
            }
            "\u{AC}nb" => {
                // End nb — close paragraph if open
                if basic_only {
                    if let Some(ref_ip) = state.in_paragraph.take() {
                        html.push_str(&format!("</p><!--{ip}-->\n", ip = ref_ip));
                    }
                }
            }

            // ── Section markers ──
            "s1" => {
                if state.in_sp_div.is_some() { close_sp_div(&mut html, &mut state); }
                if let Some(ref_right) = state.in_right_div.take() {
                    html.push_str(&format!("</div><!--{ref_right}-->\n"));
                }
                if state.in_table.is_some() {
                    state.in_table = None;
                    html.push_str("</table>\n");
                }
                if state.in_list.is_some() {
                    close_list(&mut html, &mut state);
                }
                if state.in_section.as_deref() == Some("periph") {
                    let guts = convert_char_formatting(
                        version_abbreviation, bbb, segment_type, rest_str, basic_only,
                        &mut state.background_colour,
                    )?;
                    html.push_str(&(format!(r#"<p class="s1">{guts}</p><!--s1-->"#) + "\n"));
                } else {
                    if state.in_section.as_deref() == Some("section") {
                        state.in_section = None;
                    }
                    if !basic_only {
                        let guts = convert_char_formatting(
                            version_abbreviation, bbb, segment_type, rest_str, basic_only,
                            &mut state.background_colour,
                        )?;
                        if version_abbreviation.contains("OET") {
                            let display_v = if state.v_value.is_empty() { "1" } else { &state.v_value };
                            if segment_type == "section" || rest_str.contains("\\f") {
                                html.push_str(&(format!(
                                    r#"<div class="s1"><div class="rightS1Box"><p class="s1"><span class="s1cv">{c}:{display_v}</span> {guts}</p><!--s1-->"#
                                ) + "
"));
                            } else {
                                let section_number = find_section_fn(version_abbreviation, bbb, c, display_v);
                                if let Some(sn) = section_number {
                                    html.push_str(&(format!(
                                        r#"<div class="s1"><div class="rightS1Box"><p class="s1"><span class="s1cv">{c}:{display_v}</span> <a title="Go to section view" href="{}OET/bySec/{bbb}_S{sn}.htm#C{c}V{display_v}">{guts}</a></p><!--s1-->"#,
                                        "../".repeat(level)
                                    ) + "
"));
                                } else {
                                    html.push_str(&(format!(
                                        r#"<div class="s1"><div class="rightS1Box"><p class="s1"><span class="s1cv">{c}:{display_v}</span> {guts}</p><!--s1-->"#
                                    ) + "
"));
                                }
                            }
                            state.in_right_div = Some("rightS1Box".to_string());
                        } else {
                            html.push_str(&(format!(
                                r#"<div class="s1"><p class="s1">{guts}</p><!--s1-->"#
                            ) + "
"));
                        }
                        state.in_section = Some("s1".to_string());
                    }
                }
            }
            "s2" => {
                if !basic_only {
                    let guts = convert_char_formatting(
                        version_abbreviation, bbb, segment_type, rest_str, basic_only,
                        &mut state.background_colour,
                    )?;
                    if version_abbreviation.contains("OET") {
                        html.push_str(&(format!(
                            r#"<div class="rightS2Box"><p class="s2">{guts}</p><!--s2-->"#
                        ) + "
"));
                        state.in_right_div = Some("rightS2Box".to_string());
                    } else {
                        html.push_str(&(format!(
                            r#"<p class="s2">{guts}</p><!--s2-->"#
                        ) + "
"));
                    }
                }
            }
            "s3" | "s4" => {
                if !basic_only {
                    let guts = convert_char_formatting(
                        version_abbreviation, bbb, segment_type, rest_str, basic_only,
                        &mut state.background_colour,
                    )?;
                    if marker == "s4" && (version_abbreviation == "OET" || version_abbreviation == "OET-RV") {
                        let additional_class = rest_str.replace(' ', "")
                            .replace("king", "King")
                            .replace("land", "Land");
                        html = rreplace(&html, r#"div class="section""#, &format!(r#"div class="section {additional_class}""#), 1);
                        let link_guts = format!(
                            r#"<a title="Go to {rest} information page" href="{}ref/Kingdoms/{additional_class}.htm">{guts}</a>"#,
                            "../".repeat(level),
                            rest = rest_str.replace("king", "King").replace("land", "Land"),
                        );
                        html.push_str(&(format!(
                            r#"<p class="s4 {additional_class}">{link_guts}</p><!--s4-->"#
                        ) + "
"));
                    } else {
                        html.push_str(&(format!(
                            r#"<p class="{marker}">{guts}</p><!--{marker}-->"#
                        ) + "
"));
                    }
                }
            }
            "\u{AC}s1" | "\u{AC}s2" | "\u{AC}s3" | "\u{AC}s4" => {
                if marker == "\u{AC}s1" {
                    if state.in_section.as_deref() == Some("s1") {
                        html.push_str(&(format!(r#"</div><!--s1-->"#) + "
"));
                        state.in_section = None;
                    }
                } else {
                    if state.in_section.is_some() && !basic_only {
                        state.in_section = None;
                    }
                }
            }

            // ── Title markers ──
            "mt1" | "mt2" | "mt3" | "mt4" => {
                let mut display_rest = rest_str.to_string();
                if version_abbreviation == "KJB-1611" {
                    display_rest = display_rest.replace("   ", " &nbsp; ");
                }
                if state.in_main_div.is_none() {
                    state.in_main_div = Some("bookHeader".to_string());
                    html.push_str("<div class=\"bookHeader\">");
                }
                if !basic_only {
                    let guts = convert_char_formatting(
                        version_abbreviation, bbb, segment_type, &display_rest, basic_only,
                        &mut state.background_colour,
                    )?;
                    html.push_str(&(format!(r#"<p class="{marker}">{guts}</p><!--{marker}-->"#) + "\n"));
                }
            }
            "imt1" | "imt2" | "imt3" | "imt4" => {
                if state.in_main_div.as_deref() == Some("bookHeader") {
                    state.in_main_div = None;
                    html.push_str("</div><!--bookHeader-->");
                }
                if state.in_main_div.is_none() {
                    state.in_main_div = Some("bookIntro".to_string());
                    html.push_str("<div class=\"bookIntro\">");
                }
                if !basic_only {
                    let guts = convert_char_formatting(
                        version_abbreviation, bbb, segment_type, rest_str, basic_only,
                        &mut state.background_colour,
                    )?;
                    html.push_str(&(format!(r#"<p class="{marker}">{guts}</p><!--{marker}-->"#) + "\n"));
                }
            }

            // ── Simple data markers ──
            "d" => {
                if let Some(ref_right) = state.in_right_div.take() {
                    html.push_str(&format!("</div><!--{ref_right}-->\n"));
                }
                if let Some(ref_ip) = state.in_paragraph.take() {
                    html.push_str(&format!("</p><!--{ip}-->\n", ip = ref_ip));
                }
                if basic_only {
                    let guts = convert_char_formatting(
                        version_abbreviation, bbb, segment_type, rest_str, basic_only,
                        &mut state.background_colour,
                    )?;
                    html.push_str(&(format!(r#"<span class="d">{guts}</span>"#) + "\n"));
                } else {
                    let guts = convert_char_formatting(
                        version_abbreviation, bbb, segment_type, rest_str, basic_only,
                        &mut state.background_colour,
                    )?;
                    let c_bit = if state.c_printed || segment_type == "parallelVerse" || segment_type == "interlinearVerse" {
                        String::new()
                    } else {
                        let psa_class = if bbb == "PSA" { "cPsa" } else { "c" };
                        state.c_printed = true;
                        if segment_type == "chapter" {
                            format!(r#"<span class="{psa_class}" id="C{c}">{}</span> &emsp;"#, fmt_chapter(version_abbreviation, c))
                        } else {
                            format!(r#"<span class="{psa_class}" id="C{c}"><a title="View single chapter" href="../byC/{bbb}_C{c}.htm#Top">{}</a></span> &emsp;"#, fmt_chapter(version_abbreviation, c))
                        }
                    };
                    html.push_str(&(format!(r#"<p class="d">{c_bit}{guts}</p><!--d-->"#) + "\n"));
                }
                state.just_had_d = true;
            }
            "r" => {
                if !basic_only {
                    let guts = liven_section_references_core(
                        version_abbreviation, (bbb, c, v), segment_type, rest_str,
                        &find_section_fn,
                        |_, _| true, // simplified: always available
                    );
                    html.push_str(&(format!(r#"<p class="r">{guts}</p><!--r-->"#) + "\n"));
                }
            }

            // ── Chapter markers ──
            "c" => {
                state.c_value = rest_str.trim().to_string();
                state.v_value = "0".to_string();
                state.c_printed = false;
                state.background_colour = None;
            }
            "c#" => {
                // Chapter number (display only)
            }
            "c~" => {
                if !rest_str.is_empty() {
                    let guts = convert_char_formatting(
                        version_abbreviation, bbb, segment_type, rest_str, basic_only,
                        &mut state.background_colour,
                    )?;
                    html.push_str(&format!("{NARROW_NON_BREAK_SPACE}{guts}{NARROW_NON_BREAK_SPACE}\n"));
                }
            }

            // ── MS/MR markers ──
            "ms1" | "ms2" | "ms3" | "ms4" => {
                if let Some(ref_ip) = state.in_paragraph.take() {
                    html.push_str(&format!("</p><!--{ip}-->\n", ip = ref_ip));
                }
                if state.in_section.is_some() {
                    state.in_section = None;
                }
                if !basic_only {
                    let guts = convert_char_formatting(
                        version_abbreviation, bbb, segment_type, rest_str, basic_only,
                        &mut state.background_colour,
                    )?;
                    html.push_str(&(format!(r#"<p class="{marker}">{guts}</p><!--{marker}-->"#) + "\n"));
                }
            }
            "mr" => {
                if !basic_only {
                    let guts = convert_char_formatting(
                        version_abbreviation, bbb, segment_type, rest_str, basic_only,
                        &mut state.background_colour,
                    )?;
                    html.push_str(&(format!(r#"<p class="mr">{guts}</p><!--mr-->"#) + "\n"));
                }
            }
            "\u{AC}ms1" | "\u{AC}ms2" | "\u{AC}ms3" | "\u{AC}ms4" => {
                // No-op
            }

            // ── Speaker markers ──
            "sr" | "cl" | "sp" | "cp" | "qa" | "qc" | "qd" => {
                if let Some(ref_right) = state.in_right_div.take() {
                    html.push_str(&format!("</div><!--{ref_right}-->\n"));
                }
                if let Some(ref_ip) = state.in_paragraph.take() {
                    html.push_str(&format!("</p><!--{ip}-->\n", ip = ref_ip));
                }
                if !basic_only {
                    let guts = convert_char_formatting(
                        version_abbreviation, bbb, segment_type, rest_str, basic_only,
                        &mut state.background_colour,
                    )?;
                    let c_bit = if state.c_printed || marker == "d" {
                        String::new()
                    } else {
                        let psa_class = if bbb == "PSA" { "cPsa" } else { "c" };
                        state.c_printed = true;
                        if segment_type == "chapter" {
                            format!(r#"<span class="{psa_class}" id="C{c}">{}</span> &emsp;"#, fmt_chapter(version_abbreviation, c))
                        } else {
                            format!(r#"<span class="{psa_class}" id="C{c}"><a title="View single chapter" href="../byC/{bbb}_C{c}.htm#Top">{}</a></span> &emsp;"#, fmt_chapter(version_abbreviation, c))
                        }
                    };
                    if version_abbreviation == "OET-RV" && marker == "sp" {
                        if let Some(sp_class) = SP_CLASS_DICT.get(rest_str) {
                            if let Some(ref_sp) = state.in_sp_div.take() {
                                html.push_str(&format!("</div><!--SP_{sp}-->\n", sp = ref_sp));
                            }
                            html.push_str(&(format!(r#"<div class="{sp_class}">"#) + "\n"));
                            state.in_sp_div = Some(sp_class.to_string());
                        }
                    }
                    html.push_str(&(format!(r#"<p class="{marker}">{c_bit}{guts}</p><!--{marker}-->"#) + "\n"));
                }
            }

            // ── Break markers ──
            "b" | "ib" => {
                html.push_str("<br>");
            }
            "pb" => {
                html.push_str("<!--PAGE BREAK-->");
            }

            // ── VP markers ──
            "vp#" => {
                html.push_str(&(format!(r#"<span class="vp">{NARROW_NON_BREAK_SPACE}v{rest_str}{NARROW_NON_BREAK_SPACE}</span>"#) + "\n"));
            }

            // ── Introduction markers ──
            "ip" | "ipi" | "ipq" | "ipr" | "im" | "imi" | "imq"
            | "iq1" | "iq2" | "iq3" | "io1" | "io2" | "io3" | "io4" => {
                if !basic_only {
                    let intro_html = convert_char_formatting(
                        version_abbreviation, bbb, segment_type, rest_str, basic_only,
                        &mut state.background_colour,
                    )?;
                    let final_html = if marker.starts_with("io") {
                        liven_iors_core(
                            bbb, segment_type, segment_type, &intro_html, is_single_chapter_book,
                            &find_section_fn,
                        ).unwrap_or(intro_html)
                    } else {
                        liven_introduction_links_core(
                            version_abbreviation, bbb, segment_type, &intro_html,
                            &find_section_fn,
                        ).unwrap_or(intro_html)
                    };
                    html.push_str(&(format!(r#"<p class="{marker}">{final_html}</p><!--{marker}-->"#) + "\n"));
                }
            }
            "iot" => {
                if !basic_only {
                    let guts = convert_char_formatting(
                        version_abbreviation, bbb, segment_type, rest_str, basic_only,
                        &mut state.background_colour,
                    )?;
                    html.push_str(&(format!(r#"<div class="iot"><p class="iot">{guts}</p><!--iot-->"#) + "\n"));
                }
            }
            "\u{AC}iot" => {
                html.push_str("</div><!--iot-->\n");
            }

            // ── List markers ──
            "list" | "ilist" => {
                if segment_type != "parallelVerse" {
                    html.push_str("<ul>\n");
                    state.in_list = Some("ul_1".to_string());
                }
            }
            "\u{AC}list" | "\u{AC}ilist" => {
                if state.in_list.is_some() {
                    close_list(&mut html, &mut state);
                }
            }
            "li1" | "li2" | "li3" | "li4" | "ili1" | "ili2" => {
                let marker_level: usize = marker.chars().last().unwrap().to_digit(10).unwrap_or(1) as usize;
                if basic_only {
                    let indent = "\u{00A0}".repeat(marker_level);
                    let spacing = if marker_level == 1 { "\u{2002}" } else { "\u{2003}" };
                    let guts = convert_char_formatting(
                        version_abbreviation, bbb, segment_type, rest_str, basic_only,
                        &mut state.background_colour,
                    )?;
                    let br = if html.is_empty() { "" } else { "<br>" };
                    html.push_str(&format!("{br}{indent}<span class=\"{marker}\">\u{2022}{spacing}{guts}</span>\n"));
                } else {
                    let mut current_level = match &state.in_list {
                        Some(l) => l.chars().last().unwrap().to_digit(10).unwrap_or(0) as usize,
                        None => 0,
                    };
                    if marker_level > current_level {
                        html.push_str(&format!("\n{}<ul>\n", " ".repeat(marker_level - 1)));
                        state.in_list = Some(format!("ul_{}", current_level + 1));
                    } else if marker_level < current_level {
                        if marker_level < current_level - 1 { // it's more than one level down
                            html.push_str(&format!("{}</ul>\n", " ".repeat(current_level - 1)));
                            current_level -= 1;
                        }
                        debug_assert_eq!(marker_level, current_level - 1); // Always true by construction (cf. Python assert)
                        eprintln!("Warning: Not inList C {version_abbreviation} {bbb} {segment_type} marker_level={marker_level} current_level={current_level} {marker}={rest_str}");
                        html.push_str(&format!("{}</ul>\n", " ".repeat(current_level - 1)));
                        state.in_list = Some(format!("ul_{}", current_level - 1));
                    }
                    // Close previous list entry if any
                    if state.in_list_entry != ListEntry::None {
                        html.push_str("</li>\n");
                        state.in_list_entry = ListEntry::None;
                    }
                    let guts = convert_char_formatting(
                        version_abbreviation, bbb, segment_type, rest_str, basic_only,
                        &mut state.background_colour,
                    )?;
                    html.push_str(&format!("{}<li>{guts}", " ".repeat(marker_level)));
                    state.in_list_entry = ListEntry::Specific(marker.to_string());
                }
            }
            "\u{AC}li1" | "\u{AC}li2" | "\u{AC}li3" | "\u{AC}li4"
            | "\u{AC}ili1" | "\u{AC}ili2" => {
                if state.in_list_entry != ListEntry::None {
                    html.push_str("</li>\n");
                    state.in_list_entry = ListEntry::None;
                } else if state.in_list.as_deref() == Some("ul_2") || state.in_list.as_deref() == Some("ul_3") {
                    // if let Some(ref l) = state.in_list {
                    let depth: usize = state.in_list.as_deref().unwrap_or("").chars().last().unwrap().to_digit(10).unwrap_or(1) as usize;
                    html.push_str(&format!("{}</ul>\n", " ".repeat(depth)));
                    state.in_list = Some(format!("ul_{}", depth - 1));
                }
            }

            // ── Table markers ──
            "tr" => {
                if state.in_table.is_none() {
                    if let Some(ref_ip) = state.in_paragraph.take() {
                        html.push_str(&format!("</p><!--{ip}-->\n", ip = ref_ip));
                    }
                    html.push_str("<table>\n");
                    state.in_table = Some("table".to_string());
                }
                if state.in_table_row.is_some() {
                    html.push_str("</tr>\n");
                    state.in_table_row = None;
                }
                if !rest_str.trim().is_empty() {
                    let guts = convert_char_formatting(
                        version_abbreviation, bbb, segment_type, rest_str, basic_only,
                        &mut state.background_colour,
                    )?;
                    html.push_str(&format!("<tr>{guts}\n"));
                } else {
                    html.push_str("<tr>\n");
                    state.in_table_row = Some("tr".to_string());
                }
            }
            "tc1" | "tc2" | "tc3" | "tc4" => {
                // Character markers — typically handled by character formatting
            }

            // ── Headers / Intro section boundaries ──
            "headers" => {
                if state.in_main_div.is_none() {
                    state.in_main_div = Some("bookHeader".to_string());
                    html.push_str("<div class=\"bookHeader\">");
                }
            }
            "intro" => {
                if state.in_main_div.as_deref() == Some("bookHeader") {
                    state.in_main_div = None;
                    html.push_str("</div><!--bookHeader-->");
                }
                if state.in_main_div.is_none() {
                    state.in_main_div = Some("bookIntro".to_string());
                    html.push_str("<div class=\"bookIntro\">");
                }
            }
            "ie" | "\u{AC}intro" | "chapters" => {
                if let Some(refimd) = state.in_main_div.take() {
                    html.push_str(&format!("</div><!--{refimd}-->"));
                }
            }
            "periph" => {
                if let Some(ref_ip) = state.in_paragraph.take() {
                    html.push_str(&format!("</p><!--{ip}-->\n", ip = ref_ip));
                }
                if state.in_section.as_deref() == Some("periph") {
                    state.in_section = None;
                    html.push_str("</div><!--periph-->\n");
                }
                html.push_str(&(format!(
                    r#"<hr class="periph">"#) + "\n"));
                html.push_str(&(format!(r#"<div class="periph">"#) + "\n"));
                html.push_str(&format!("<h1>{rest_str}</h1>\n"));
                state.in_section = Some("periph".to_string());
            }
            "rem" | "id" => {
                let display_rest = rest_str
                    .replace("Open English Translation", "<em>Open English Translation</em>");
                if display_rest.starts_with('/') {
                    // Section reference comment — usually no-op after disabling
                } else if display_rest.starts_with("was /") {
                    // Commented-out line
                } else if !display_rest.is_empty() {
                    if !basic_only {
                        let guts = convert_char_formatting(
                            version_abbreviation, bbb, segment_type, &display_rest, basic_only,
                            &mut state.background_colour,
                        )?;
                        if state.in_paragraph.is_some() {
                            html.push_str(&(format!(r#"<span class="{marker}">{guts}</span>"#) + "\n"));
                        } else {
                            html.push_str(&(format!(r#"<p class="{marker}">{guts}</p><!--{marker}-->"#) + "\n"));
                        }
                    }
                }
            }

            // ── End chapter/book for chapter segmentType ──
            "\u{AC}c" | "\u{AC}chapters" if segment_type == "chapter" => {
                if state.in_section.as_deref() == Some("s1") {
                    html.push_str("</div><!--s1-->\n");
                    state.in_section = None;
                }
                if state.in_paragraph.is_some() && marker == "\u{AC}c" {
                    if let Some(ref_ip) = state.in_paragraph.take() {
                        html.push_str(&format!("</p><!--{ip}-->\n", ip = ref_ip));
                    }
                }
            }

            // ── Ignored markers ──
            "usfm" | "ide" | "sts" | "h"
            | "toc1" | "toc2" | "toc3"
            | "toca1" | "toca2" | "toca3"
            | "\u{AC}is1" | "\u{AC}headers"
            | "cl\u{A4}" | "\u{AC}c" | "\u{AC}chapters" => {
                // Silently ignored
            }

            // ── Fallback: pass through ──
            _ => {
                if !rest_str.is_empty() && !basic_only {
                    let guts = convert_char_formatting(
                        version_abbreviation, bbb, segment_type, rest_str, basic_only,
                        &mut state.background_colour,
                    )?;
                    html.push_str(&(format!(r#"<p class="{marker}">{guts}</p><!--{marker}-->"#) + "\n"));
                }
            }
        }

        state.last_marker = marker.to_string();
    }

    // --- Close any remaining open structures ---
    if let Some(ref_ip) = state.in_paragraph.take() {
        html.push_str(&format!("</p><!--{ip}-->\n", ip = ref_ip));
    }
    if state.in_table_row.is_some() {
        html.push_str("</tr>\n");
    }
    if state.in_table.is_some() {
        html.push_str("</table>\n");
    }
    if state.in_list_entry != ListEntry::None {
        html.push_str("</li>\n");
    }
    if state.in_list.is_some() {
        close_list(&mut html, &mut state);
    }
    if state.in_sp_div.is_some() {
        html.push_str("</div><!--SP-->\n");
    }
    if state.in_section.as_deref() == Some("s1") || state.in_section.as_deref() == Some("periph") {
        if let Some(ref_right) = state.in_right_div.take() {
            html.push_str(&format!("</div><!--{ref_right}-->\n"));
        }
        let sect = state.in_section.take().unwrap();
        html.push_str(&format!("</div><!--{sect}-->\n"));
    }
    if let Some(refimd) = state.in_main_div.take() {
        html.push_str(&format!("</div><!--{refimd}-->\n"));
    }

    // --- Handle footnotes and cross-references ---
    let _path_prefix = if segment_type == "parallelVerse" || segment_type == "interlinearVerse" {
        "../../OET/byC/"
    } else if segment_type == "topicalPassage" {
        "../OET/byC/"
    } else if segment_type == "chapter" {
        ""
    } else {
        "../byC/"
    };

    // Footnotes are handled by the Python caller after this returns
    // Cross-references are handled by the Python caller after this returns

    // --- Final cleanups ---
    if basic_only {
        while html.contains("<br><br>") {
            html = html.replace("<br><br>", "<br>");
        }
        while html.starts_with("<br>") {
            html = html[4..].to_string();
        }
        while html.ends_with("<br>") {
            html = html[..html.len() - 4].to_string();
        }
    }
    html = html.replace("<br>\n", "\n<br>");
    html = html.replace("\n\n", "\n");
    while html.ends_with('\n') {
        html.pop();
    }
    while html.ends_with("<br>") {
        html = html[..html.len() - 4].to_string();
        while html.ends_with('\n') {
            html.pop();
        }
    }

    Ok(html)
}

// ─── Standalone conversion (no Python callback for char formatting) ─────────

/// Full list of USFM character markers matching
/// `usfm_markers_py.get_character_markers_list(expand_numberable_markers=True)` plus `untr`.
fn expanded_char_markers_list() -> Vec<String> {
    vec![
        "ior".into(), "iqt".into(), "rq".into(), "ca".into(), "va".into(),
        "vp".into(), "litl".into(), "lik".into(), "liv".into(), "liv1".into(),
        "liv2".into(), "qs".into(), "qac".into(),
        "th".into(), "th1".into(), "th2".into(), "th3".into(), "th4".into(),
        "thr".into(), "thr1".into(), "thr2".into(), "thr3".into(), "thr4".into(),
        "tc".into(), "tc1".into(), "tc2".into(), "tc3".into(), "tc4".into(),
        "tcr".into(), "tcr1".into(), "tcr2".into(), "tcr3".into(), "tcr4".into(),
        "add".into(), "bk".into(), "dc".into(), "k".into(), "nd".into(),
        "ord".into(), "pn".into(), "png".into(), "qt".into(), "sig".into(),
        "sls".into(), "tl".into(), "wj".into(),
        "em".into(), "bd".into(), "it".into(), "bdit".into(), "no".into(),
        "sc".into(), "sup".into(), "ndx".into(), "rb".into(), "pro".into(),
        "w".into(), "wg".into(), "wh".into(), "wa".into(),
        "qt-s".into(), "qt-s1".into(), "qt-s2".into(), "qt-s3".into(), "qt-s4".into(),
        "qt-e".into(), "qt-e1".into(), "qt-e2".into(), "qt-e3".into(), "qt-e4".into(),
        "ef".into(), "ex".into(), "cat".into(), "wr".into(), "jmp".into(),
        "untr".into(),
    ]
}

/// Convert verse entries to HTML — standalone version.
///
/// Calls `convert_usfm_character_formatting` directly in Rust (no Python
/// callback), handles figure-file copying via `destination_folder`, and
/// keeps Python callbacks only for OBI images, HTML validation, and
/// section-number lookup.
pub fn convert_verse_entry_list_to_html_standalone<FSect, FGetOBI, CCheckHtml>(
    level: usize,
    version_abbreviation: &str,
    bbb: &str,
    c: Option<&str>,
    v: Option<&str>,
    segment_type: &str,
    context_list: &[&str],
    verse_entries: &[VerseEntry],
    basic_only: bool,
    is_single_chapter_book: bool,
    find_section_fn: FSect,
    get_open_bible_images: FGetOBI,
    check_html: CCheckHtml,
    destination_folder: Option<&str>,
) -> Result<String, ConvertError>
where
    FSect: Fn(&str, &str, &str, &str) -> Option<usize> + Clone,
    FGetOBI: Fn(usize, &str, &str, &str, &str) -> Option<String>,
    CCheckHtml: Fn(&str, &str) -> bool,
{
    let char_markers = expanded_char_markers_list();
    let nt27: Vec<String> = BOOKLIST_NT27.iter().map(|s| s.to_string()).collect();
    let is_net = version_abbreviation == "NET";
    let dest_folder_owned = destination_folder.map(|s| s.to_string());

    let convert_char_formatting = |
        va: &str,
        inner_bbb: &str,
        st: &str,
        field: &str,
        bo: bool,
        bg: &mut Option<String>,
    | -> Result<String, ConvertError> {
        let result = convert_usfm_character_formatting(
            va, inner_bbb, st, field, bo, &char_markers, &nt27, is_net, level,
        );
        *bg = result.background_colour;
        Ok(result.html)
    };

    let copy_fig_files = |files: &[(String, String)]| {
        if let Some(ref folder) = dest_folder_owned {
            for (src_path, dest_name) in files {
                copy_figure_file(src_path, folder, dest_name);
            }
        }
    };

    let find_section_for_post = find_section_fn.clone();
    let mut html = convert_verse_entry_list_to_html_core(
        level,
        version_abbreviation,
        bbb,
        c,
        v,
        segment_type,
        context_list,
        verse_entries,
        basic_only,
        is_single_chapter_book,
        convert_char_formatting,
        copy_fig_files,
        find_section_fn,
        get_open_bible_images,
        check_html,
    )?;

    // --- Handle footnotes and cross-references (same as the old Python caller did) ---
    let path_prefix = crate::verse_to_html::compute_path_prefix(segment_type);
    let max_footnote_chars = if version_abbreviation == "NET" {
        crate::constants::MAX_NET_FOOTNOTE_CHARS
    } else {
        crate::constants::MAX_FOOTNOTE_CHARS
    };

    let (html_with_xrefs, cross_refs_html) = crate::verse_to_html::process_cross_references_core(
        &html,
        version_abbreviation,
        bbb,
        c.unwrap_or(""),
        segment_type,
        path_prefix,
        find_section_for_post.clone(),
    )?;
    html = html_with_xrefs;

    let (html_with_fn, footnotes_html) = crate::verse_to_html::process_footnotes_core(
        &html,
        version_abbreviation,
        bbb,
        c.unwrap_or(""),
        segment_type,
        path_prefix,
        max_footnote_chars,
        find_section_for_post,
    )?;
    html = html_with_fn;

    if !footnotes_html.is_empty() {
        html = format!("{html}\n<hr class=\"line-before-footnotes\"><div id=\"footnotes\" class=\"footnotes\">\n{footnotes_html}</div><!--footnotes-->");
    }
    if !cross_refs_html.is_empty() {
        html = format!("{html}\n<hr class=\"line-before-xrefs\"><div id=\"crossRefs\" class=\"crossRefs\">\n{cross_refs_html}</div><!--crossRefs-->");
    }

    Ok(html)
}

// ─── Internal helpers ──────────────────────────────────────────────────────

fn close_list(html: &mut String, state: &mut ConvertState) {
    if let Some(ref l) = state.in_list {
        let parts: Vec<&str> = l.split('_').collect();
        let marker = parts[0];
        let mut depth: usize = parts.get(1).and_then(|s| s.parse().ok()).unwrap_or(1);
        while depth > 0 {
            if depth > 1 && state.in_list_entry == ListEntry::Generic {
                html.push_str("</li>\n");
                state.in_list_entry = ListEntry::None;
            }
            html.push_str(&format!("</{marker}>\n"));
            depth -= 1;
        }
    }
    state.in_list = None;
}

fn close_sp_div(html: &mut String, state: &mut ConvertState) {
    if let Some(ref sp) = state.in_sp_div {
        html.push_str(&format!("</div><!--SP_{sp}-->\n"));
    }
    state.in_sp_div = None;
}

// ─── Tests ─────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn no_op_char_fmt(
        _va: &str, _bbb: &str, _st: &str, field: &str, _bo: bool, _bg: &mut Option<String>,
    ) -> Result<String, ConvertError> {
        Ok(field.to_string())
    }
    fn no_op_fig(_files: &[(String, String)]) {}
    fn no_op_sect(_va: &str, _bbb: &str, _c: &str, _v: &str) -> Option<usize> { None }
    fn no_op_obi(_l: usize, _st: &str, _b: &str, _c: &str, _v: &str) -> Option<String> { None }
    fn no_op_check(_w: &str, _h: &str) -> bool { true }

    #[test]
    fn test_simple_verse_kjb() {
        let entries = vec![
            VerseEntry { marker: "v~".into(), full_text: "In the beginning.".into(), clean_text: "In the beginning.".into() },
        ];
        let result = convert_verse_entry_list_to_html_core(
            1, "KJB", "GEN", Some("1"), Some("1"),
            "parallelVerse", &["chapters"], &entries, false, false,
            no_op_char_fmt, no_op_fig, no_op_sect, no_op_obi, no_op_check,
        ).unwrap();
        assert!(result.contains("In the beginning."));
        assert!(result.contains("KJB_verseTextChunk"));
    }

    #[test]
    fn test_basic_only_strips_xrefs() {
        let entries = vec![
            VerseEntry { marker: "v~".into(), full_text: r#"God created.\x \xo 1:1 \xt Gen 2:4.\x*"#.into(), clean_text: "God created.".into() },
        ];
        let result = convert_verse_entry_list_to_html_core(
            1, "KJB", "GEN", Some("1"), Some("1"),
            "parallelVerse", &["chapters"], &entries, true, false,
            no_op_char_fmt, no_op_fig, no_op_sect, no_op_obi, no_op_check,
        ).unwrap();
        assert!(result.contains("God created."));
    }

    #[test]
    fn test_rreplace() {
        assert_eq!(rreplace("a-b-c-d", "-", "/", 2), "a-b/c/d");
        assert_eq!(rreplace("hello", "x", "y", 1), "hello");
        assert_eq!(rreplace("aaa", "a", "b", 2), "abb");
    }

    #[test]
    fn test_get_small_leading_int() {
        assert_eq!(get_small_leading_int("123abc"), 123);
        assert_eq!(get_small_leading_int("0"), 0);
        assert_eq!(get_small_leading_int("abc"), 0);
        assert_eq!(get_small_leading_int("42"), 42);
    }

    #[test]
    fn test_liven_section_references_basic() {
        let result = liven_section_references_core(
            "OET-RV", ("GEN", "1", "1"), "chapter",
            "Gen 1:1",
            no_op_sect,
            |_va, _bbb| true,
        );
        assert!(result.contains("Gen 1:1"));
    }
}
