// SPDX-License-Identifier: GPL-3.0-or-later
//! Logic for livening cross-reference fields in USFM/HTML text.
//!
//! Port of `livenXRefField` from `usfm.py`.
//!
//! CHANGELOG:
//!  2026-10-23: Separate note origins from target context; retain conjunctions and
//!              verse lists, and disambiguate KJB-1611 Psalm/Proverb shorthand.

use std::collections::HashMap;
use std::sync::LazyLock;
use regex::Regex;

use crate::oet_books::get_bbb_from_oet_book_name;

// ---------------------------------------------------------------------------
// Static data
// ---------------------------------------------------------------------------

/// KJB-1611 abbreviation → bos_book_code lookup table (non-commented entries from Python).
static KJB_1611_XREF_TABLE: LazyLock<HashMap<&'static str, &'static str>> = LazyLock::new(|| {
    let pairs: &[(&str, &str)] = &[
        ("Actes", "ACT"), ("actes", "ACT"),
        ("Apoc", "REV"), ("apoc", "REV"),
        ("hest", "EST"),
        ("exe", "EXO"),
        ("Ezech", "EZE"), ("ezech", "EZE"), ("Exek", "EZE"), ("ezec", "EZE"),
        ("eszr", "EZR"),
        ("Abacuc", "HAB"), ("Habac", "HAB"), ("habac", "HAB"), ("Abak", "HAB"), ("Abac", "HAB"), ("abac", "HAB"),
        ("Hagge", "HAG"), ("Agge", "HAG"), ("agge", "HAG"), ("agg", "HAG"),
        ("Osee", "HOS"), ("Ose", "HOS"), ("ose", "HOS"), ("Os", "HOS"), ("os", "HOS"),
        ("Esai", "ISA"), ("Esa", "ISA"), ("esa", "ISA"), ("Esay", "ISA"), ("esay", "ISA"), ("esai", "ISA"), ("Isay", "ISA"),
        ("Iames", "JAM"), ("iames", "JAM"), ("Iam", "JAM"), ("iam", "JAM"),
        ("Iude", "JDE"), ("iude", "JDE"), ("Iud", "JDE"), ("iud", "JDE"),
        ("iudges", "JDG"), ("iuges", "JDG"), ("Iudg", "JDG"), ("iudg", "JDG"),
        ("iudith", "JDT"), ("iudit", "JDT"), ("iudet", "JDT"),
        ("Ier", "JER"), ("ier", "JER"), ("Ierem", "JER"), ("Iere", "JER"), ("iere", "JER"), ("ierem", "JER"), ("Iee", "JER"),
        ("Ioh", "JHN"), ("ioh", "JHN"), ("Iohn", "JHN"), ("iohn", "JHN"),
        ("1.Iohn", "JN1"), ("1.iohn", "JN1"), ("I.Iohn", "JN1"), ("1.Ioh", "JN1"), ("1.ioh", "JN1"),
        ("ionas", "JNA"), ("Iona", "JNA"), ("ion", "JNA"),
        ("Iob", "JOB"), ("iob", "JOB"),
        ("Ioel", "JOL"), ("ioel", "JOL"),
        ("Iosh", "JOS"), ("iosh", "JOS"), ("Ios", "JOS"), ("Iosu", "JOS"),
        ("1.Reg", "KI1"),
        ("4.Esdr", "LES"), ("4.Esd", "LES"),
        ("Leuit", "LEV"), ("leuit", "LEV"), ("Leui", "LEV"), ("leui", "LEV"), ("Leu", "LEV"),
        ("Luc", "LUK"), ("luc", "LUK"),
        ("Marke", "MRK"), ("marke", "MRK"), ("Marc", "MRK"),
        ("naum", "NAH"),
        ("nnm", "NUM"),
        ("psalme", "PSA"),
        ("Prou", "PRO"), ("prou", "PRO"),
        ("Reuel", "REV"), ("reuel", "REV"), ("Reue", "REV"), ("reue", "REV"), ("Reu", "REV"), ("reu", "REV"),
        ("Sophan", "ZEP"),
        ("Zach", "ZEC"), ("zach", "ZEC"), ("Zac", "ZEC"), ("zac", "ZEC"),
    ];
    pairs.iter().copied().collect()
});

/// Book + Chapter + Verse reference regex.
/// Matches e.g. "Gen 25:9-10", "1 Kings 1:2", "Exod 17.5"
static BCV_REF_REGEX: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?: ?and)?( ?[1234I]?[ .]?[A-Za-z][a-z]{1,12})\.? ?([1-9][0-9]{0,2}|ver)[:.–] ?([1-9][0-9]{0,2})").unwrap()
});

/// Book + Verse reference regex (single-chapter book or whole chapter).
static BV_REF_REGEX: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"([1234I]?[ .]?[A-Za-z][a-z]{0,12})\.? ?(?:ver)?\.? ?([1-9][0-9]{0,2})").unwrap()
});

/// Chapter + Verse reference regex.
static CV_REF_REGEX: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"([1-9][0-9]{0,2})[:.]([1-9][0-9]{0,2})").unwrap()
});

/// A few KJB-1611 continuations omit the chapter/verse dot: "and 115 2".
static KJB_SPACED_CV_REGEX: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r" ?(?:and|&) +([1-9][0-9]{0,2}) +([1-9][0-9]{0,2})\b").unwrap()
});

/// Continuation reference: a verse list, or another C:V after a conjunction.
/// Keep the separator so it cannot be discarded before interpreting the number.
static NEXT_V_REF_REGEX: LazyLock<Regex> = LazyLock::new(|| {
    // No whitespace after a dot: in ",15. 1.Mac. 2.24" the 1 begins a book name.
    Regex::new(r"(?:,\s*(?:(?:and|&)\s*)?|(?:\band\b|&)\s*)([1-9][0-9]{0,2})(?:[:.]([1-9][0-9]{0,2}))?[abc]?\b").unwrap()
});

static THIS_CHAPTER_REGEX: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)^[.\s]*(?:of|in) this chapter\b").unwrap()
});

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

/// Errors that can occur during cross-reference field livening.
#[derive(Debug, PartialEq, Eq)]
pub enum XRefError {
    InvalidFieldType(String),
    InvalidSegmentType(String),
    Custom(String),
}

impl std::fmt::Display for XRefError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            XRefError::InvalidFieldType(ft) => write!(f, "Invalid fieldType: {ft}"),
            XRefError::InvalidSegmentType(seg) => write!(f, "Invalid or unsupported segmentType: {seg}"),
            XRefError::Custom(msg) => write!(f, "{msg}"),
        }
    }
}

impl std::error::Error for XRefError {}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Characters that can appear in a verse/chapter range tail.
const RANGE_CHARS: &str = "-–1234567890abc:";

/// Check if a character is part of a verse range tail.
fn is_range_char(c: char) -> bool {
    RANGE_CHARS.contains(c)
}

/// Ambiguous historical shorthand cannot always be resolved by punctuation.
/// Key exceptions by origin AND complete source field so ordinary verse lists
/// (including verse 119) and revised source texts retain the general rules.
enum AbbreviatedTarget {
    Chapter(&'static str, &'static str),
    Verse(&'static str, &'static str, &'static str),
    Unresolved,
}

fn kjb_1611_abbreviated_target(
    source_book: &str, source_ref: &str, field: &str, number: &str,
) -> Option<AbbreviatedTarget> {
    match (source_book, source_ref, field.trim(), number) {
        ("PSA", "25:4", "Psa.27.11. & 86.11. & 119.", "119")
        | ("PSA", "27:11", "Psal. 25.4 and 86.11 and 119.", "119") => {
            Some(AbbreviatedTarget::Chapter("PSA", "119"))
        }
        ("PRO", "28:12", "Iohn 11.10. eccles. 10.6 and ver. 28.", "28") => {
            Some(AbbreviatedTarget::Verse("PRO", "28", "28"))
        }
        // These source numbers exceed the target chapter's length. Preserve
        // their wording without inventing a correction or creating a dead link.
        ("SA1", "7:3", "Iosh. 14.15,23.", "23")
        | ("PSA", "43:5", "Psal. 42.6. and 12.", "12")
        | ("JER", "4:6", "Chap. 1.13, 14, 23. chap. 6.26.", "23") => {
            Some(AbbreviatedTarget::Unresolved)
        }
        _ => None,
    }
}

// ---------------------------------------------------------------------------
// Core implementation
// ---------------------------------------------------------------------------

/// Core logic for livening a cross-reference (or footnote xt) field.
///
/// - `field_type`: `"f"` (footnote) or `"x"` (cross-reference)
/// - `version_abbreviation`: e.g. `"KJB-1611"`, `"OET-RV"`, `"RV"`, etc.
/// - `bos_book_code`: the BOS book code of the *current* book (where the xref appears)
/// - `c`, `v`: current chapter and verse (as strings)
/// - `segment_type`: the segment type string
/// - `path_prefix`: HTML path prefix for links
/// - `xo_text`: the `\xo` reference text (e.g. `"1:1"`)
/// - `xref_original_middle`: the `\xt` content (may contain `\xo`/`\xt` markers)
/// - `find_section_fn`: optional callback `(version_abbrev, bos_book_code, c, v) -> Option<usize>` for OET-RV section lookup
pub fn liven_xref_field_core<F>(
    field_type: &str,
    version_abbreviation: &str,
    bos_book_code: &str,
    c: &str,
    _v: &str,
    segment_type: &str,
    path_prefix: &str,
    xo_text: &str,
    xref_original_middle: &str,
    find_section_fn: F,
) -> Result<String, XRefError>
where
    F: Fn(&str, &str, &str, &str) -> Option<usize>,
{
    if field_type != "f" && field_type != "x" {
        return Err(XRefError::InvalidFieldType(field_type.to_string()));
    }

    let mut xref_live_middle = xref_original_middle.to_string();

    // --- Version-specific normalisations ---
    if version_abbreviation == "RV" {
        xref_live_middle = xref_live_middle
            .replace(" iii ", " iii.")
            .replace("xxxix.", "39.").replace("xxxviii.", "38.").replace("xxxvii.", "37.")
            .replace("xxxvi.", "36.").replace("xxxv.", "35.").replace("xxxiv.", "34.")
            .replace("xxxiii.", "33.").replace("xxxii.", "32.").replace("xxxi.", "31.").replace("xxx.", "30.")
            .replace("xxix.", "29.").replace("xxviii.", "28.").replace("xxvii.", "27.").replace("xxvi.", "26.")
            .replace("xxv.", "25.").replace("xxiv.", "24.").replace("xxiii.", "23.").replace("xxii.", "22.")
            .replace("xxi.", "21.").replace("xx.", "20.")
            .replace("xix.", "19.").replace("xviii.", "18.").replace("xvii.", "17.").replace("xvi.", "16.")
            .replace("xv.", "15.").replace("xiv.", "14.").replace("xiii.", "13.").replace("xii.", "12.")
            .replace("xi.", "11.").replace("x.", "10.")
            .replace("ix.", "9.").replace("viii.", "8.").replace("vii.", "7.").replace("vi.", "6.")
            .replace("iv.", "4.").replace("v.", "5.").replace("iii.", "3.").replace("ii.", "2.").replace("i.", "1.");
    } else if version_abbreviation == "KJB-1611" {
        xref_live_middle = xref_live_middle.replace("A&s", "Acts");
    }

    // --- Main loop ---
    let mut re_start_ix: usize = 0;
    // Whole-book and multi-chapter views need the note's own origin, not the
    // page's first chapter. Never overwrite it with a cross-reference target.
    let source_c = xo_text.split_once(':')
        .map(|(chapter, _)| chapter)
        .filter(|chapter| !chapter.is_empty() && chapter.chars().all(|c| c.is_ascii_digit()))
        .unwrap_or(c);
    let mut last_xr_bos_book_code = bos_book_code.to_string();
    let mut last_xc = source_c.to_string();
    let mut last_was_chapter = false;

    let loop_limit: usize = if segment_type == "book" { 599 } else { 50 };

    for _safety_count in 0..loop_limit {
        if re_start_ix >= xref_live_middle.len().saturating_sub(1) {
            break;
        }

        let slice = &xref_live_middle[re_start_ix..];

        // Find explicit and abbreviated references without discarding separators.
        let cap_bcv = BCV_REF_REGEX.captures(slice);
        let cap_bv  = BV_REF_REGEX.captures(slice);
        let cap_cv  = CV_REF_REGEX.captures(slice);
        let cap_v   = NEXT_V_REF_REGEX.captures(slice);
        let cap_spaced_cv = if version_abbreviation == "KJB-1611" {
            KJB_SPACED_CV_REGEX.captures(slice)
        } else {
            None
        };

        // Determine which match starts earliest.  Among ties prefer the longer span.
        #[derive(Clone, Copy, PartialEq, Eq)]
        enum Kind { BCV, BV, CV, V, SpacedCV }

        let mut best: Option<(usize, usize, Kind)> = None; // (start_in_slice, end_in_slice, kind)

        macro_rules! consider {
            ($cap:expr, $kind:expr) => {
                if let Some(ref c) = $cap {
                    let s = c.get(0).unwrap().start();
                    let e = c.get(0).unwrap().end();
                    match best {
                        None => best = Some((s, e, $kind)),
                        Some((bs, be, _)) if s < bs || (s == bs && e > be) => best = Some((s, e, $kind)),
                        _ => {}
                    }
                }
            };
        }
        consider!(cap_bcv, Kind::BCV);
        consider!(cap_bv,  Kind::BV);
        consider!(cap_cv,  Kind::CV);
        consider!(cap_v,   Kind::V);
        consider!(cap_spaced_cv, Kind::SpacedCV);

        let (best_start, best_end, kind) = match best {
            Some(t) => t,
            None => break,
        };

        // Grab the winning captures
        let captures = match kind {
            Kind::BCV => cap_bcv.unwrap(),
            Kind::BV  => cap_bv.unwrap(),
            Kind::CV  => cap_cv.unwrap(),
            Kind::V   => cap_v.unwrap(),
            Kind::SpacedCV => cap_spaced_cv.unwrap(),
        };

        let first_start = best_start + re_start_ix;
        let first_end   = best_end   + re_start_ix;
        let full_match = captures.get(0).unwrap().as_str().trim_start();
        let before_match = xref_live_middle[..first_start].trim_end();
        let joined = full_match.starts_with("and ")
            || before_match.split_whitespace().next_back() == Some("and")
            || before_match.ends_with('&');
        let this_chapter = THIS_CHAPTER_REGEX.is_match(&xref_live_middle[first_end..]);

        // --- Determine xBBB, xC, xV from the match ---
        let mut xr_bos_book_code: Option<String> = None;
        let mut xc = last_xc.clone();
        let mut xv = String::new();
        let mut xb_name = String::new();
        let mut is_chapter = false;
        let mut abbreviated_number = None;

        match kind {
            Kind::V => {
                let number = captures.get(1).unwrap().as_str();
                xr_bos_book_code = Some(last_xr_bos_book_code.clone());
                if let Some(verse) = captures.get(2) {
                    xc = number.to_string();
                    xv = verse.as_str().to_string();
                } else {
                    abbreviated_number = Some(number);
                    is_chapter = last_was_chapter;
                    if is_chapter {
                        xc = number.to_string();
                        xv = "1".to_string();
                    } else {
                        xv = number.to_string();
                        if version_abbreviation == "BrTr" && bos_book_code == "JDG" {
                            xc = "1".to_string();
                        }
                    }
                }
            }
            Kind::CV | Kind::SpacedCV => {
                xc = captures.get(1).unwrap().as_str().to_string();
                xv = captures.get(2).unwrap().as_str().to_string();
                xr_bos_book_code = Some(last_xr_bos_book_code.clone());
            }
            Kind::BV => {
                xb_name = captures.get(1).unwrap().as_str().trim().to_string();
                let number = captures.get(2).unwrap().as_str();
                let x_cor_v = number.to_string();
                abbreviated_number = Some(number);

                // Check for verse-like words
                let xb_lower = xb_name.to_lowercase();
                if xb_lower == "and" {
                    xr_bos_book_code = Some(last_xr_bos_book_code.clone());
                    is_chapter = last_was_chapter;
                    if is_chapter {
                        xc = x_cor_v;
                        xv = "1".to_string();
                    } else {
                        xv = x_cor_v;
                    }
                } else if matches!(xb_lower.as_str(), "verses" | "verse" | "vers" | "ver" | "v") {
                    xr_bos_book_code = Some(if joined && !this_chapter {
                        last_xr_bos_book_code.clone()
                    } else {
                        xc = source_c.to_string();
                        bos_book_code.to_string()
                    });
                    xv = x_cor_v;
                } else if matches!(xb_lower.as_str(), "chapter" | "chap" | "cha" | "c" | "ca") {
                    xr_bos_book_code = Some(if joined { &last_xr_bos_book_code } else { bos_book_code }.to_string());
                    xc = x_cor_v;
                    xv = "1".to_string();
                    is_chapter = true;
                } else {
                    // Try single-chapter book lookup
                    if let Some(found_bos_book_code) = resolve_book_name(&xb_name, version_abbreviation, bos_book_code) {
                        if bos_books_codes::is_single_chapter_book(&found_bos_book_code) {
                            xc = "1".to_string();
                            xv = x_cor_v;
                        } else {
                            xc = x_cor_v;
                            xv = "1".to_string();
                            is_chapter = true;
                        }
                        xr_bos_book_code = Some(found_bos_book_code);
                    }
                }
            }
            Kind::BCV => {
                xb_name = captures.get(1).unwrap().as_str().trim().to_string();
                xc = captures.get(2).unwrap().as_str().to_string();
                xv = captures.get(3).unwrap().as_str().to_string();

                // If en-dash in the full match, it's a chapter range → use v1
                let full_match = captures.get(0).unwrap().as_str();
                if full_match.contains('–') {
                    xv = "1".to_string();
                    is_chapter = true;
                }

                xr_bos_book_code = resolve_book_name(&xb_name, version_abbreviation, bos_book_code).map(|s| s.to_string());
                let xb_lower = xb_name.to_lowercase();
                if xb_lower == "and" {
                    xr_bos_book_code = Some(last_xr_bos_book_code.clone());
                    if xc == "ver" {
                        abbreviated_number = Some(captures.get(3).unwrap().as_str());
                        xc = last_xc.clone();
                        if this_chapter {
                            xr_bos_book_code = Some(bos_book_code.to_string());
                            xc = source_c.to_string();
                        }
                    }
                } else if matches!(xb_lower.as_str(), "chapter" | "chap" | "cha" | "c" | "ca") {
                    xr_bos_book_code = Some(if joined { &last_xr_bos_book_code } else { bos_book_code }.to_string());
                }
            }
        }

        // --- KJB-1611 special handling for book name words ---
        if version_abbreviation == "KJB-1611" && kind == Kind::BCV {
            let xb_lower = xb_name.to_lowercase();
            if matches!(xb_lower.as_str(), "ant" | "antiq" | "as" | "in" | "lambes" | "lib" | "see" | "the" | "to" | "called" | "araunah" | "dodo" | "elishua" | "vzziah" | "esdr" | "ez") {
                // Skip this word
                re_start_ix = if xb_name == "to" { first_end } else { first_start + captures.get(1).unwrap().as_str().len() };
                continue;
            }
            if matches!(xb_lower.as_str(), "verse" | "vers" | "ver") {
                xr_bos_book_code = Some(bos_book_code.to_string());
                xc = source_c.to_string();
            }
            // Special: "A&s" already replaced above
        }

        // --- KJB-1611 book lookup fallback ---
        if xr_bos_book_code.is_none() && kind == Kind::BCV {
            if version_abbreviation == "KJB-1611" {
                if let Some(found) = KJB_1611_XREF_TABLE.get(xb_name.as_str()) {
                    xr_bos_book_code = Some(found.to_string());
                } else {
                    // Fix KJB-1611 spellings
                    let adj_xb = xb_name
                        .replace("1.", "1 ").replace("2.", "2 ").replace("3.", "3 ").replace("4.", "4 ")
                        .replace("I.", "1 ")
                        .replace("Ie", "Je")
                        .replace("Io", "Jo");
                    xr_bos_book_code = get_bbb_from_oet_book_name(&adj_xb).map(|s| s.to_string());
                }
            } else {
                xr_bos_book_code = get_bbb_from_oet_book_name(&xb_name).map(|s| s.to_string());
            }
        }

        // If we still don't have xBBB, try resolving via get_bbb_from_oet_book_name
        if xr_bos_book_code.is_none() && !xb_name.is_empty() && kind != Kind::V && kind != Kind::CV {
            xr_bos_book_code = get_bbb_from_oet_book_name(&xb_name).map(|s| s.to_string());
        }

        // --- KJB-1611 special post-processing ---
        if version_abbreviation == "KJB-1611" {
            if xc == "ver" || xc == "Ver" {
                if let Some(ref b) = xr_bos_book_code {
                    if bos_books_codes::is_single_chapter_book(b) {
                        xc = "1".to_string();
                    } else if xb_name == "and" {
                        xc = last_xc.clone();
                    } else {
                        xc = source_c.to_string();
                    }
                }
            }
            if xref_original_middle == "Nehem." {
                xr_bos_book_code = Some("NEH".to_string());
                xc = "1".to_string();
                xv = "1".to_string();
            }
            if let Some(number) = abbreviated_number {
                if let Some(target) = kjb_1611_abbreviated_target(
                    bos_book_code, xo_text, xref_original_middle, number,
                ) {
                    let (book, chapter, verse) = match target {
                        AbbreviatedTarget::Chapter(book, chapter) => {
                            is_chapter = true;
                            (book, chapter, "1")
                        }
                        AbbreviatedTarget::Verse(book, chapter, verse) => {
                            is_chapter = false;
                            (book, chapter, verse)
                        }
                        AbbreviatedTarget::Unresolved => {
                            re_start_ix = first_end;
                            continue;
                        }
                    };
                    xr_bos_book_code = Some(book.to_string());
                    xc = chapter.to_string();
                    xv = verse.to_string();
                }
            }
        }

        // --- Validate xBBB ---
        let xr_bos_book_code = match xr_bos_book_code {
            Some(b) if !b.is_empty() && !matches!(b.as_str(), "SAM" | "KGS" | "CHR") => b,
            _ => {
                // Failed to find book — skip past this match
                re_start_ix = first_end;
                continue;
            }
        };

        // Validate chapter/verse are digits
        if xc.is_empty() || xv.is_empty()
            || !xc.chars().all(|c| c.is_ascii_digit()) || !xv.chars().all(|c| c.is_ascii_digit()) {
            re_start_ix = first_end;
            continue;
        }

        // --- Capture the full match text (including range tail) ---
        let mut match_inner_end = first_end;
        while match_inner_end < xref_live_middle.len() {
            let c = xref_live_middle.as_bytes()[match_inner_end] as char;
            if is_range_char(c) {
                match_inner_end += 1;
            } else {
                break;
            }
        }
        let match_inner = &xref_live_middle[first_start..match_inner_end].to_string();

        // --- Validate chapter count ---
        let int_xc: i32 = xc.parse().unwrap_or(0);
        if int_xc > bos_books_codes::get_max_chapters(&xr_bos_book_code) as i32 {
            re_start_ix = first_end;
            continue;
        }

        // Only a validated target may become the context of a later reference.
        last_xr_bos_book_code = xr_bos_book_code.clone();
        last_xc = xc.clone();
        last_was_chapter = is_chapter;

        // --- Build the link ---
        let title_prefix = if field_type == "x" { "cross " } else { "" };

        let inside = if version_abbreviation == "OET-RV"
            && (bos_books_codes::is_old_testament_nr(&xr_bos_book_code) || bos_books_codes::is_new_testament_nr(&xr_bos_book_code))
        {
            // Link to section page
            match find_section_fn(version_abbreviation, &xr_bos_book_code, &xc, &xv) {
                Some(section_number) => {
                    let adj_path = if path_prefix.is_empty() {
                        "../bySec/".to_string()
                    } else {
                        path_prefix.replace("byC", "bySec")
                    };
                    format!(
                        r#"<a title="View {title_prefix}reference" href="{adj_path}{xr_bos_book_code}_S{section_number}.htm#C{xc}V{xv}">{match_inner}</a>"#
                    )
                }
                _ => {
                    // Fallback to chapter page
                    format!(
                        r#"<a title="View {title_prefix}reference" href="{path_prefix}{xr_bos_book_code}_C{xc}.htm#C{xc}V{xv}">{match_inner}</a>"#
                    )
                }
            }
        } else {
            // Link to chapter page
            format!(
                r#"<a title="View {title_prefix}reference" href="{path_prefix}{xr_bos_book_code}_C{xc}.htm#C{xc}V{xv}">{match_inner}</a>"#
            )
        };

        xref_live_middle = format!("{}{}{}", &xref_live_middle[..first_start], inside, &xref_live_middle[match_inner_end..]);
        re_start_ix = first_start + inside.len();
    }

    Ok(xref_live_middle)
}

/// Resolve a book name from xref text to a bos_book_code code.
/// Returns `None` if the name refers to the *current* book (caller should use its own bos_book_code).
/// Returns `Some(bos_book_code.to_string())` where bos_book_code is the same as `current_bos_book_code` for "same book" cases.
fn resolve_book_name(name: &str, version_abbreviation: &str, current_bos_book_code: &str) -> Option<String> {
    let lower = name.to_lowercase();

    // Special cases
    if lower == "songs" { return Some("SNG".to_string()); }
    if lower == "yohan" { return Some("JHN".to_string()); }

    // KJB-1611 / RV "same book" words → caller must handle
    if version_abbreviation == "KJB-1611" || version_abbreviation == "RV" {
        if matches!(lower.as_str(), "and" | "c" | "ca" | "verse" | "vers" | "ver") {
            return Some(current_bos_book_code.to_string());
        }
    }

    // KJB-1611 specific table lookup
    if version_abbreviation == "KJB-1611" {
        if let Some(&bos_book_code) = KJB_1611_XREF_TABLE.get(name) {
            return Some(bos_book_code.to_string());
        }
        // Fix KJB-1611 spellings
        let adj = name
            .replace("1.", "1 ").replace("2.", "2 ").replace("3.", "3 ").replace("4.", "4 ")
            .replace("I.", "1 ")
            .replace("Ie", "Je")
            .replace("Io", "Jo");
        return get_bbb_from_oet_book_name(&adj).map(|s| s.to_string());
    }

    // General lookup
    get_bbb_from_oet_book_name(name).map(|s| s.to_string())
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    /// No-op section finder for testing (OET-RV section links not tested here).
    fn noop_section_finder(_v: &str, _b: &str, _c: &str, _v2: &str) -> Option<usize> {
        None
    }

    #[test]
    fn test_kjb_1611_table_lookup() {
        assert_eq!(KJB_1611_XREF_TABLE.get("Actes"), Some(&"ACT"));
        assert_eq!(KJB_1611_XREF_TABLE.get("Luc"), Some(&"LUK"));
        assert_eq!(KJB_1611_XREF_TABLE.get("Iob"), Some(&"JOB"));
        assert_eq!(KJB_1611_XREF_TABLE.get("nnm"), Some(&"NUM"));
        assert_eq!(KJB_1611_XREF_TABLE.get("psalme"), Some(&"PSA"));
        assert_eq!(KJB_1611_XREF_TABLE.get("Unknown"), None);
    }

    #[test]
    fn test_bcv_regex() {
        let text = "Gen. 17:5 and 20:9";
        let m = BCV_REF_REGEX.find(text).unwrap();
        assert_eq!(m.as_str(), "Gen. 17:5");
    }

    #[test]
    fn test_bv_regex() {
        let text = "Verse 7";
        let m = BV_REF_REGEX.find(text).unwrap();
        assert_eq!(m.as_str(), "Verse 7");
    }

    #[test]
    fn test_cv_regex() {
        let text = "12:34";
        let m = CV_REF_REGEX.find(text).unwrap();
        assert_eq!(m.as_str(), "12:34");
    }

    #[test]
    fn test_next_v_regex() {
        let text = ",5 and 6";
        let m = NEXT_V_REF_REGEX.find(text).unwrap();
        assert_eq!(m.as_str(), ",5");
    }

    #[test]
    fn test_simple_bcv_ref() {
        // "Exod 17:5" should become a link to EXO C17 V5
        let result = liven_xref_field_core(
            "f", "NET", "GEN", "1", "1", "chapter", "",
            "1:1", "Exod. 17:5",
            noop_section_finder,
        ).unwrap();
        assert!(result.contains("EXO_C17.htm#C17V5"), "Expected chapter link in: {result}");
        assert!(result.contains("Exod. 17:5"), "Expected original text preserved: {result}");
    }

    #[test]
    fn test_kjb_1611_acts_lookup() {
        let result = liven_xref_field_core(
            "x", "KJB-1611", "GEN", "1", "1", "chapter", "",
            "1:1", "Actes 1",
            noop_section_finder,
        ).unwrap();
        // Actes → ACT, chapter 1, verse 1
        assert!(result.contains("ACT_C1.htm"), "Expected ACT chapter link in: {result}");
    }

    #[test]
    fn test_rv_roman_numeral_conversion() {
        // RV replaces roman numerals with arabic
        let result = liven_xref_field_core(
            "x", "RV", "GEN", "1", "1", "chapter", "",
            "1:1", "Gen. iii. 5",
            noop_section_finder,
        ).unwrap();
        // After roman numeral conversion, "iii." → "3."
        assert!(result.contains("GEN_C3.htm"), "Expected GEN chapter 3 link in: {result}");
    }

    #[test]
    fn test_kjb_1611_as_special() {
        // "A&s" → "Acts"
        let result = liven_xref_field_core(
            "x", "KJB-1611", "GEN", "1", "1", "chapter", "",
            "1:1", "A&s 1:1",
            noop_section_finder,
        ).unwrap();
        assert!(result.contains("Acts"), "Expected 'Acts' in result: {result}");
        assert!(result.contains("ACT_C1.htm"), "Expected ACT chapter link in: {result}");
    }

    #[test]
    fn test_no_match_returns_unchanged() {
        let input = "no references here";
        let result = liven_xref_field_core(
            "x", "NET", "GEN", "1", "1", "chapter", "",
            "1:1", input,
            noop_section_finder,
        ).unwrap();
        assert_eq!(result, input);
    }

    #[test]
    fn test_invalid_field_type() {
        let result = liven_xref_field_core(
            "z", "NET", "GEN", "1", "1", "chapter", "",
            "1:1", "Gen 1:1",
            noop_section_finder,
        );
        assert!(result.is_err());
    }

    #[test]
    fn test_single_chapter_book_bv_ref() {
        // Jude is a single-chapter book; "Jude 5" → Jude C1 V5
        let result = liven_xref_field_core(
            "x", "NET", "JDE", "1", "1", "chapter", "",
            "1:1", "Jude 5",
            noop_section_finder,
        ).unwrap();
        assert!(result.contains("JDE_C1.htm#C1V5"), "Expected JDE chapter 1 verse 5 link in: {result}");
    }

    #[test]
    fn test_multiple_refs_in_one_field() {
        let result = liven_xref_field_core(
            "x", "NET", "GEN", "1", "1", "chapter", "",
            "1:1", "Gen 1:1, 2:3",
            noop_section_finder,
        ).unwrap();
        // Should have two links
        assert!(result.contains("GEN_C1.htm"), "Expected GEN chapter 1 link");
        assert!(result.contains("GEN_C2.htm"), "Expected GEN chapter 2 link");
    }

    #[test]
    fn test_separator_prefixes_skipped() {
        // ", Gen 1:1" — leading comma should be skipped
        let result = liven_xref_field_core(
            "x", "NET", "GEN", "1", "1", "chapter", "",
            "1:1", ", Gen 1:1",
            noop_section_finder,
        ).unwrap();
        assert!(result.contains("GEN_C1.htm"), "Expected GEN chapter link: {result}");
    }
}
