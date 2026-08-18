//! Logic for livening introduction links in USFM/HTML text.

use std::sync::LazyLock;
use regex::Regex;
use crate::oet_books::get_bbb_from_oet_book_name;

static PARENTHETICAL_REGEX: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"\(([^()]+)\)").unwrap()
});

static CV_PATTERN: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"([1-9][0-9]{0,2}):([1-9][0-9]{0,2})([-–][1-9][0-9]{0,2})?").unwrap()
});

static STANDALONE_CV_REGEX: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(\s)([1-9][0-9]{0,2}):([1-9][0-9]{0,2})([-–][1-9][0-9]{0,2})?([ ,.?!:;])").unwrap()
});

/// Errors that can occur during introduction link livening.
#[derive(Debug, PartialEq, Eq)]
pub enum IntroLinkError {
    ContainsIorMarker,
    InvalidSegmentType(String),
    Custom(String),
}

impl std::fmt::Display for IntroLinkError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            IntroLinkError::ContainsIorMarker => {
                write!(f, r#"intro_html must not contain '\ior' or 'class="ior"'"#)
            }
            IntroLinkError::InvalidSegmentType(seg) => {
                write!(f, "Invalid or unsupported segmentType: {seg}")
            }
            IntroLinkError::Custom(msg) => write!(f, "{msg}"),
        }
    }
}

impl std::error::Error for IntroLinkError {}

struct BookMatch<'a> {
    prefix_and_book: &'a str,
    bbb: &'static str,
}

/// Helper to identify book names and optional prefixes in text preceding a C:V reference.
fn find_book_in_prefix(text: &str) -> Option<BookMatch<'_>> {
    let trimmed = text.trim();
    if trimmed.is_empty() {
        return None;
    }

    let mut s = trimmed;
    while let Some(rest) = s.strip_prefix(',').or_else(|| s.strip_prefix(';')) {
        s = rest.trim_start();
    }
    if let Some(rest) = s.strip_prefix("and ") {
        s = rest.trim_start();
    } else if let Some(rest) = s.strip_prefix("or ") {
        s = rest.trim_start();
    }

    if s.is_empty() {
        return None;
    }

    let whole_candidate = s;
    let mut book_part = s;
    if let Some(rest) = book_part.strip_prefix("See ") {
        book_part = rest;
    } else if let Some(rest) = book_part.strip_prefix("see ") {
        book_part = rest;
    } else if let Some(rest) = book_part.strip_prefix("as in ") {
        book_part = rest;
    }

    // Try whole book_part first (e.g. "1 Peter", "Song of Solomon", "Acts")
    if let Some(bbb) = get_bbb_from_oet_book_name(book_part) {
        return Some(BookMatch {
            prefix_and_book: whole_candidate,
            bbb,
        });
    }

    // If book_part has multiple words, try suffix words (e.g. "e.g., Acts" -> "Acts")
    let words: Vec<&str> = book_part.split_whitespace().collect();
    for i in 1..words.len() {
        let sub_part = words[i..].join(" ");
        if let Some(bbb) = get_bbb_from_oet_book_name(&sub_part) {
            if let Some(pos) = whole_candidate.find(&sub_part) {
                return Some(BookMatch {
                    prefix_and_book: &whole_candidate[pos..],
                    bbb,
                });
            }
        }
    }

    None
}

/// Format an HTML reference link according to segment_type and target BBB vs our BBB.
fn format_ref_link<F>(
    version_abbreviation: &str,
    our_bbb: &str,
    ref_bbb: &str,
    ref_c: &str,
    ref_v: &str,
    guts: &str,
    segment_type: &str,
    find_section_number: &F,
) -> Result<String, IntroLinkError>
where
    F: Fn(&str, &str, &str, &str) -> Option<usize>,
{
    if ref_bbb == our_bbb {
        match segment_type {
            "book" => {
                Ok(format!(r##"<a title="Jump down to reference" href="#C{ref_c}V{ref_v}">{guts}</a>"##))
            }
            "chapter" => {
                Ok(format!(r##"<a title="Jump to chapter page with reference" href="{our_bbb}_C{ref_c}.htm#C{ref_c}V{ref_v}">{guts}</a>"##))
            }
            s if s.ends_with("Verse") => {
                Ok(format!(r##"<a title="Go to reference verse" href="C{ref_c}V{ref_v}.htm#Top">{guts}</a>"##))
            }
            "section" | "relatedPassage" => {
                let n = find_section_number(version_abbreviation, our_bbb, ref_c, ref_v);
                if let Some(section_idx) = n {
                    Ok(format!(r##"<a title="Jump to section page with reference" href="{our_bbb}_S{section_idx}.htm#Top">{guts}</a>"##))
                } else {
                    Ok(guts.to_string())
                }
            }
            other => Err(IntroLinkError::InvalidSegmentType(other.to_string())),
        }
    } else {
        match segment_type {
            "book" => {
                Ok(format!(r##"<a title="Go to reference document" href="{ref_bbb}.htm#C{ref_c}V{ref_v}">{guts}</a>"##))
            }
            "chapter" => {
                Ok(format!(r##"<a title="Go to reference chapter" href="{ref_bbb}_C{ref_c}.htm#C{ref_c}V{ref_v}">{guts}</a>"##))
            }
            s if s.ends_with("Verse") => {
                Ok(format!(r##"<a title="Go to reference verse" href="../{ref_bbb}/C{ref_c}V{ref_v}.htm#Top">{guts}</a>"##))
            }
            "section" | "relatedPassage" => {
                let n = find_section_number(version_abbreviation, ref_bbb, ref_c, ref_v);
                if let Some(section_idx) = n {
                    Ok(format!(r##"<a title="Go to to section page with reference" href="{ref_bbb}_S{section_idx}.htm#Top">{guts}</a>"##))
                } else {
                    Ok(guts.to_string())
                }
            }
            other => Err(IntroLinkError::InvalidSegmentType(other.to_string())),
        }
    }
}

/// Process all references within a parenthetical group `(...)`.
fn process_parenthetical<F>(
    inner: &str,
    version_abbreviation: &str,
    our_bbb: &str,
    segment_type: &str,
    find_section_number: &F,
) -> Result<String, IntroLinkError>
where
    F: Fn(&str, &str, &str, &str) -> Option<usize>,
{
    let mut result = String::new();
    let mut prev_end = 0;
    let mut current_bbb: Option<&str> = None;

    let matches: Vec<_> = CV_PATTERN.find_iter(inner).collect();
    if matches.is_empty() {
        return Ok(inner.to_string());
    }

    for m in matches {
        let cv_start = m.start();
        let cv_end = m.end();

        let caps = CV_PATTERN.captures(m.as_str()).unwrap();
        let ref_c = caps.get(1).unwrap().as_str();
        let ref_v = caps.get(2).unwrap().as_str();

        let before_text = &inner[prev_end..cv_start];

        if let Some(book_match) = find_book_in_prefix(before_text) {
            current_bbb = Some(book_match.bbb);
            let ref_bbb = book_match.bbb;

            let book_start_in_before = before_text.rfind(book_match.prefix_and_book).unwrap();
            let unlinked_before = &before_text[..book_start_in_before];
            result.push_str(unlinked_before);

            let guts = format!("{}{}", &before_text[book_start_in_before..], m.as_str());
            let link = format_ref_link(
                version_abbreviation,
                our_bbb,
                ref_bbb,
                ref_c,
                ref_v,
                &guts,
                segment_type,
                find_section_number,
            )?;
            result.push_str(&link);
        } else {
            let ref_bbb = current_bbb.unwrap_or(our_bbb);
            result.push_str(before_text);
            let guts = m.as_str();
            let link = format_ref_link(
                version_abbreviation,
                our_bbb,
                ref_bbb,
                ref_c,
                ref_v,
                guts,
                segment_type,
                find_section_number,
            )?;
            result.push_str(&link);
        }

        prev_end = cv_end;
    }

    result.push_str(&inner[prev_end..]);
    Ok(result)
}

/// Liven general links in the introduction.
pub fn liven_introduction_links_core<F>(
    version_abbreviation: &str,
    our_bbb: &str,
    segment_type: &str,
    intro_html: &str,
    find_section_number: F,
) -> Result<String, IntroLinkError>
where
    F: Fn(&str, &str, &str, &str) -> Option<usize>,
{
    if intro_html.contains(r"\ior") || intro_html.contains(r#"class="ior""#) {
        return Err(IntroLinkError::ContainsIorMarker);
    }

    let mut result_html = intro_html.to_string();

    // 1. Process all parenthetical expressions `(...)`
    let mut search_start_ix = 0;
    while search_start_ix < result_html.len() {
        let Some(caps) = PARENTHETICAL_REGEX.captures(&result_html[search_start_ix..]) else {
            break;
        };

        let entire_match = caps.get(0).unwrap();
        let match_start = search_start_ix + entire_match.start();
        let match_end = search_start_ix + entire_match.end();

        let inner = caps.get(1).unwrap().as_str();
        let processed_inner = process_parenthetical(
            inner,
            version_abbreviation,
            our_bbb,
            segment_type,
            &find_section_number,
        )?;

        let replacement = format!("({processed_inner})");
        result_html.replace_range(match_start..match_end, &replacement);
        search_start_ix = match_start + replacement.len();
    }

    // 2. Process any standalone C:V references outside parentheticals (e.g. preceded by whitespace)
    search_start_ix = 0;
    while search_start_ix < result_html.len() {
        let Some(caps) = STANDALONE_CV_REGEX.captures(&result_html[search_start_ix..]) else {
            break;
        };

        let entire_match = caps.get(0).unwrap();
        let match_start = search_start_ix + entire_match.start();
        let match_end = search_start_ix + entire_match.end();

        // Check if inside an HTML tag or attribute
        let prefix_slice = &result_html[..match_start];
        if let Some(last_open) = prefix_slice.rfind('<') {
            if let Some(last_close) = prefix_slice.rfind('>') {
                if last_open > last_close {
                    // We are inside an HTML tag, skip
                    search_start_ix = match_end;
                    continue;
                }
            } else {
                // Inside an unclosed tag, skip
                search_start_ix = match_end;
                continue;
            }
        }

        let pre_char = caps.get(1).unwrap().as_str();
        let ref_c = caps.get(2).unwrap().as_str();
        let ref_v = caps.get(3).unwrap().as_str();
        let post_char = caps.get(5).unwrap().as_str();

        let match_str = entire_match.as_str();
        let guts = &match_str[pre_char.len()..match_str.len() - post_char.len()];

        // Look for book prefix before the CV match
        let before_match = &result_html[..match_start];
        let mut ref_bbb = our_bbb;
        let mut final_guts = guts.to_string();
        let mut actual_match_start = match_start;

        if let Some(book_match) = find_book_in_prefix(before_match) {
            ref_bbb = book_match.bbb;
            // Find where the book prefix starts in the text before the match
            if let Some(_book_pos) = before_match.rfind(book_match.prefix_and_book) {
                // Strip prefix words like "See", "see", "as in" from prefix_and_book
                let mut book_only = book_match.prefix_and_book;
                if let Some(rest) = book_only.strip_prefix("See ") {
                    book_only = rest;
                } else if let Some(rest) = book_only.strip_prefix("see ") {
                    book_only = rest;
                } else if let Some(rest) = book_only.strip_prefix("as in ") {
                    book_only = rest;
                }
                
                // Include the book name from book_only onwards plus pre_char and guts
                if let Some(book_only_pos) = before_match.rfind(book_only) {
                    final_guts = format!("{}{}{}", &before_match[book_only_pos..], pre_char, guts);
                    actual_match_start = book_only_pos;
                }
            }
        }

        let new_guts = format_ref_link(
            version_abbreviation,
            our_bbb,
            ref_bbb,
            ref_c,
            ref_v,
            &final_guts,
            segment_type,
            &find_section_number,
        )?;

        // If we didn't find a book match (actual_match_start == match_start), 
        // pre_char wasn't included in final_guts, so we need to add it
        let replacement = if actual_match_start == match_start {
            format!("{pre_char}{new_guts}{post_char}")
        } else {
            format!("{new_guts}{post_char}")
        };
        result_html.replace_range(actual_match_start..match_end, &replacement);
        search_start_ix = actual_match_start + replacement.len();
    }

    Ok(result_html)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_bcv_book_segment() {
        let input = "was named Mary (Acts 12:12)";
        let output = liven_introduction_links_core("OET-RV", "MAT", "book", input, |_, _, _, _| None).unwrap();
        assert_eq!(output, r##"was named Mary (<a title="Go to reference document" href="ACT.htm#C12V12">Acts 12:12</a>)"##);
    }

    #[test]
    fn test_bcv_chapter_segment() {
        let input = "accompanied Peter (1 Peter 5:13)";
        let output = liven_introduction_links_core("OET-RV", "MAT", "chapter", input, |_, _, _, _| None).unwrap();
        assert_eq!(output, r##"accompanied Peter (<a title="Go to reference chapter" href="PE1_C5.htm#C5V13">1 Peter 5:13</a>)"##);
    }

    #[test]
    fn test_bcv_verse_segment() {
        let input = "see (Col. 4:10).";
        let output = liven_introduction_links_core("OET-RV", "MAT", "Verse", input, |_, _, _, _| None).unwrap();
        assert_eq!(output, r##"see (<a title="Go to reference verse" href="C4V10.htm#Top">Col. 4:10</a>)."##);
    }

    #[test]
    fn test_bcv_prefixes() {
        let input = "(See Acts 12:12) and (as in Matt 5:3)";
        let output = liven_introduction_links_core("OET-RV", "GEN", "book", input, |_, _, _, _| None).unwrap();
        assert_eq!(
            output,
            r##"(<a title="Go to reference document" href="ACT.htm#C12V12">See Acts 12:12</a>) and (<a title="Go to reference document" href="MAT.htm#C5V3">as in Matt 5:3</a>)"##
        );
    }

    #[test]
    fn test_cv_book_and_chapter_self_ref() {
        let input = "in this book (12:12) or (16:9-20)";
        let output_book = liven_introduction_links_core("OET-RV", "MRK", "book", input, |_, _, _, _| None).unwrap();
        assert_eq!(
            output_book,
            r##"in this book (<a title="Jump down to reference" href="#C12V12">12:12</a>) or (<a title="Jump down to reference" href="#C16V9">16:9-20</a>)"##
        );

        let output_chap = liven_introduction_links_core("OET-RV", "MRK", "chapter", input, |_, _, _, _| None).unwrap();
        assert_eq!(
            output_chap,
            r##"in this book (<a title="Jump to chapter page with reference" href="MRK_C12.htm#C12V12">12:12</a>) or (<a title="Jump to chapter page with reference" href="MRK_C16.htm#C16V9">16:9-20</a>)"##
        );
    }

    #[test]
    fn test_multiple_bcv_and_cv_in_parentheses() {
        let input = "about Yeshua the messiah (Acts 12:25, 13:13).";
        let output_book = liven_introduction_links_core("OET-RV", "MRK", "book", input, |_, _, _, _| None).unwrap();
        assert_eq!(
            output_book,
            r##"about Yeshua the messiah (<a title="Go to reference document" href="ACT.htm#C12V25">Acts 12:25</a>, <a title="Go to reference document" href="ACT.htm#C13V13">13:13</a>)."##
        );

        let output_chap = liven_introduction_links_core("OET-RV", "MRK", "chapter", input, |_, _, _, _| None).unwrap();
        assert_eq!(
            output_chap,
            r##"about Yeshua the messiah (<a title="Go to reference chapter" href="ACT_C12.htm#C12V25">Acts 12:25</a>, <a title="Go to reference chapter" href="ACT_C13.htm#C13V13">13:13</a>)."##
        );
    }

    #[test]
    fn test_multiple_cv_self_refs() {
        let input = "something (12:25, 13:13)";
        let output_book = liven_introduction_links_core("OET-RV", "MRK", "book", input, |_, _, _, _| None).unwrap();
        assert_eq!(
            output_book,
            r##"something (<a title="Jump down to reference" href="#C12V25">12:25</a>, <a title="Jump down to reference" href="#C13V13">13:13</a>)"##
        );

        let output_chap = liven_introduction_links_core("OET-RV", "MRK", "chapter", input, |_, _, _, _| None).unwrap();
        assert_eq!(
            output_chap,
            r##"something (<a title="Jump to chapter page with reference" href="MRK_C12.htm#C12V25">12:25</a>, <a title="Jump to chapter page with reference" href="MRK_C13.htm#C13V13">13:13</a>)"##
        );
    }

    #[test]
    fn test_section_segment_type() {
        let dummy_section_finder = |ver: &str, bbb: &str, c: &str, v: &str| -> Option<usize> {
            if ver == "OET-RV" && bbb == "ACT" && c == "12" && v == "25" {
                Some(5)
            } else if ver == "OET-RV" && bbb == "ACT" && c == "13" && v == "13" {
                Some(6)
            } else if ver == "OET-RV" && bbb == "MAT" && c == "13" && v == "13" {
                Some(10)
            } else {
                None
            }
        };

        let input = "(Acts 12:25, 13:13)";
        let output = liven_introduction_links_core("OET-RV", "MRK", "section", input, dummy_section_finder).unwrap();
        assert_eq!(
            output,
            r##"(<a title="Go to to section page with reference" href="ACT_S5.htm#Top">Acts 12:25</a>, <a title="Go to to section page with reference" href="ACT_S6.htm#Top">13:13</a>)"##
        );
    }

    #[test]
    fn test_ior_assertions() {
        let input1 = r"Some \ior text";
        let res1 = liven_introduction_links_core("OET-RV", "MAT", "book", input1, |_, _, _, _| None);
        assert_eq!(res1, Err(IntroLinkError::ContainsIorMarker));

        let input2 = r#"Some <span class="ior">text</span>"#;
        let res2 = liven_introduction_links_core("OET-RV", "MAT", "book", input2, |_, _, _, _| None);
        assert_eq!(res2, Err(IntroLinkError::ContainsIorMarker));
    }
}
