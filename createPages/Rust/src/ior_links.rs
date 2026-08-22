//! Logic for livening IOR (Introduction Outline Reference) links in HTML text.

use std::sync::LazyLock;
use regex::Regex;

static IOR_SPAN_REGEX: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"<span class="ior">(.*?)</span>"#).unwrap()
});

/// Errors that can occur during IOR link livening.
#[derive(Debug, PartialEq, Eq)]
pub enum IORLinkError {
    InvalidSegmentType(String),
    Custom(String),
}

impl std::fmt::Display for IORLinkError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            IORLinkError::InvalidSegmentType(seg) => {
                write!(f, "Invalid or unsupported segmentType: {seg}")
            }
            IORLinkError::Custom(msg) => write!(f, "{msg}"),
        }
    }
}

impl std::error::Error for IORLinkError {}

/// Parse a chapter:verse reference string into components.
/// Handles:
/// - "12:34" -> ("12", "34")
/// - "4" (for multi-chapter books) -> ("4", "1")
/// - "4" (for single-chapter books) -> ("1", "4")
fn parse_cv_reference(guts: &str, is_single_chapter: bool) -> (String, String) {
    let parts: Vec<&str> = guts.split('-').collect();
    let start_ref = parts[0].trim();

    if start_ref.contains(':') {
        let cv_parts: Vec<&str> = start_ref.split(':').collect();
        if cv_parts.len() == 2 {
            return (cv_parts[0].to_string(), cv_parts[1].to_string());
        }
    }

    // Only one part - either chapter or verse depending on book type
    if is_single_chapter {
        ("1".to_string(), start_ref.to_string())
    } else {
        (start_ref.to_string(), "1".to_string())
    }
}

/// Maximum number of IORs to process in one field (matches Python's range(15) safety loop)
const MAX_IORS: usize = 15;

/// Format an HTML reference link for IOR according to segment_type.
fn format_ior_link<F>(
    version_abbreviation: &str,
    our_bbb: &str,
    ref_c: &str,
    ref_v: &str,
    guts: &str,
    segment_type: &str,
    find_section_fn: &F,
) -> Result<String, IORLinkError>
where
    F: Fn(&str, &str, &str, &str) -> Option<usize>,
{
    match segment_type {
        "book" => {
            Ok(format!(
                r##"<a title="Jump down to reference" href="#C{ref_c}V{ref_v}">{guts}</a>"##
            ))
        }
        "chapter" => {
            Ok(format!(
                r##"<a title="Jump to chapter page with reference" href="{our_bbb}_C{ref_c}.htm#C{ref_c}V{ref_v}">{guts}</a>"##
            ))
        }
        s if s.ends_with("Verse") => {
            // For introduction (so 'verse' is 'line')
            Ok(format!(
                r##"<a title="Go to reference verse" href="C{ref_c}V{ref_v}.htm#Top">{guts}</a>"##
            ))
        }
        "section" | "relatedPassage" => {
            // Look up the section number via the callback
            if let Some(section_num) =
                find_section_fn(version_abbreviation, our_bbb, ref_c, ref_v)
            {
                Ok(format!(
                    r##"<a title="Jump to section page with reference" href="{our_bbb}_S{section_num}.htm#Top">{guts}</a>"##
                ))
            } else {
                // Fallback: return the guts unchanged (matching Python behaviour which logs a critical error)
                Ok(guts.to_string())
            }
        }
        other => Err(IORLinkError::InvalidSegmentType(other.to_string())),
    }
}

/// Liven IOR (Introduction Outline Reference) links in HTML text.
///
/// For `section` and `relatedPassage` segment types, the `find_section_fn` callback
/// is called as `find_section_fn(version_abbrev, bbb, c, v)` and should return
/// `Some(section_number)` if found.  For other segment types the callback is ignored.
pub fn liven_iors_core<F>(
    version_abbreviation: &str,
    our_bbb: &str,
    segment_type: &str,
    ior_html: &str,
    is_single_chapter: bool,
    find_section_fn: F,
) -> Result<String, IORLinkError>
where
    F: Fn(&str, &str, &str, &str) -> Option<usize>,
{
    let mut result_html = ior_html.to_string();
    let mut search_start_ix = 0;
    let mut safety_count = 0;

    while search_start_ix < result_html.len() {
        let Some(cap) = IOR_SPAN_REGEX.captures(&result_html[search_start_ix..]) else {
            break;
        };
        safety_count += 1;
        if safety_count > MAX_IORS {
            return Err(IORLinkError::Custom(format!(
                "liven_iors loop needed to break -- more than {MAX_IORS} IORs in one field"
            )));
        }

        let entire_match = cap.get(0).unwrap();
        let match_start = search_start_ix + entire_match.start();
        let match_end = search_start_ix + entire_match.end();

        let guts_raw = cap.get(1).unwrap().as_str();
        // Convert any en-dash to hyphen
        let guts = guts_raw.replace('–', "-");

        // Parse the chapter:verse reference
        let (ref_c, ref_v) = parse_cv_reference(&guts, is_single_chapter);

        // Format the link (the <span class="ior"> wrapper is kept around it, as in Python)
        let new_link = format_ior_link(
            version_abbreviation, our_bbb, &ref_c, &ref_v, &guts, segment_type, &find_section_fn,
        )?;
        let new_span = format!("<span class=\"ior\">{new_link}</span>");

        result_html.replace_range(match_start..match_end, &new_span);
        search_start_ix = match_start + new_span.len();
    }

    Ok(result_html)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// No-op section finder for tests that don't exercise section lookup.
    fn noop_section_finder(_v: &str, _b: &str, _c: &str, _v2: &str) -> Option<usize> {
        None
    }

    #[test]
    fn test_ior_book_segment() {
        let input = r#"See also <span class="ior">12:12</span> for more."#;
        let output = liven_iors_core("OET-RV", "MAT", "book", input, false, noop_section_finder).unwrap();
        assert_eq!(
            output,
            r##"See also <span class="ior"><a title="Jump down to reference" href="#C12V12">12:12</a></span> for more."##
        );
    }

    #[test]
    fn test_ior_chapter_segment() {
        let input = r#"Find it in <span class="ior">5:13</span> section."#;
        let output = liven_iors_core("OET-RV", "MAT", "chapter", input, false, noop_section_finder).unwrap();
        assert_eq!(
            output,
            r##"Find it in <span class="ior"><a title="Jump to chapter page with reference" href="MAT_C5.htm#C5V13">5:13</a></span> section."##
        );
    }

    #[test]
    fn test_ior_verse_segment() {
        let input = r#"Reference: <span class="ior">4:10</span>."#;
        let output = liven_iors_core("OET-RV", "COL", "Verse", input, false, noop_section_finder).unwrap();
        assert_eq!(
            output,
            r##"Reference: <span class="ior"><a title="Go to reference verse" href="C4V10.htm#Top">4:10</a></span>."##
        );
    }

    #[test]
    fn test_ior_single_chapter_verse_only() {
        let input = r#"See <span class="ior">4</span> for details."#;
        let output = liven_iors_core("OET-RV", "OBD", "Verse", input, true, noop_section_finder).unwrap();
        assert_eq!(
            output,
            r##"See <span class="ior"><a title="Go to reference verse" href="C1V4.htm#Top">4</a></span> for details."##
        );
    }

    #[test]
    fn test_ior_multi_chapter_chapter_only() {
        let input = r#"See <span class="ior">4</span> for details."#;
        let output = liven_iors_core("OET-RV", "MAT", "chapter", input, false, noop_section_finder).unwrap();
        assert_eq!(
            output,
            r##"See <span class="ior"><a title="Jump to chapter page with reference" href="MAT_C4.htm#C4V1">4</a></span> for details."##
        );
    }

    #[test]
    fn test_ior_multiple_spans() {
        let input = r#"In <span class="ior">3:16</span> and <span class="ior">5:7</span> we find this."#;
        let output = liven_iors_core("OET-RV", "JHN", "book", input, false, noop_section_finder).unwrap();
        assert_eq!(
            output,
            r##"In <span class="ior"><a title="Jump down to reference" href="#C3V16">3:16</a></span> and <span class="ior"><a title="Jump down to reference" href="#C5V7">5:7</a></span> we find this."##
        );
    }

    #[test]
    fn test_ior_with_range() {
        let input = r#"Found in <span class="ior">12:12-15</span> section."#;
        let output = liven_iors_core("OET-RV", "MRK", "book", input, false, noop_section_finder).unwrap();
        assert_eq!(
            output,
            r##"Found in <span class="ior"><a title="Jump down to reference" href="#C12V12">12:12-15</a></span> section."##
        );
    }

    #[test]
    fn test_ior_with_endash() {
        let input = r#"Range: <span class="ior">5:3–8</span>."#;
        let output = liven_iors_core("OET-RV", "ROM", "chapter", input, false, noop_section_finder).unwrap();
        assert_eq!(
            output,
            r##"Range: <span class="ior"><a title="Jump to chapter page with reference" href="ROM_C5.htm#C5V3">5:3-8</a></span>."##
        );
    }

    #[test]
    fn test_ior_empty_input() {
        let input = "No IOR tags here.";
        let output = liven_iors_core("OET-RV", "MAT", "book", input, false, noop_section_finder).unwrap();
        assert_eq!(output, input);
    }

    #[test]
    fn test_ior_section_segment_with_finder() {
        let input = r#"See <span class="ior">5:13</span> for context."#;
        let finder = |_v: &str, _b: &str, c: &str, v: &str| -> Option<usize> {
            // Pretend section 42 exists for 5:13
            if c == "5" && v == "13" { Some(42) } else { None }
        };
        let output = liven_iors_core("OET-RV", "MAT", "section", input, false, finder).unwrap();
        assert_eq!(
            output,
            r##"See <span class="ior"><a title="Jump to section page with reference" href="MAT_S42.htm#Top">5:13</a></span> for context."##
        );
    }

    #[test]
    fn test_ior_section_segment_finder_returns_none() {
        let input = r#"See <span class="ior">99:1</span> for context."#;
        let finder = |_v: &str, _b: &str, _c: &str, _v2: &str| -> Option<usize> { None };
        let output = liven_iors_core("OET-RV", "JHN", "section", input, false, finder).unwrap();
        // When section not found, guts are returned unchanged
        assert_eq!(
            output,
            r#"See <span class="ior">99:1</span> for context."#
        );
    }

    #[test]
    fn test_ior_related_passage_segment() {
        let input = r#"Ref: <span class="ior">3:16</span>."#;
        let finder = |_v: &str, _b: &str, c: &str, v: &str| -> Option<usize> {
            if c == "3" && v == "16" { Some(7) } else { None }
        };
        let output = liven_iors_core("OET-RV", "MAT", "relatedPassage", input, false, finder).unwrap();
        assert_eq!(
            output,
            r##"Ref: <span class="ior"><a title="Jump to section page with reference" href="MAT_S7.htm#Top">3:16</a></span>."##
        );
    }
}
