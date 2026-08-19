//! Shared constants, compiled regexes, and lookup tables for OpenBibleData.
//!
//! These mirror the Python constants defined at the top of `usfm.py` and are
//! consumed by multiple Rust modules (`character_formatting`, `verse_to_html`, etc.).

use std::collections::HashMap;
use std::sync::LazyLock;

use regex::Regex;

// ---------------------------------------------------------------------------
// Character constants
// ---------------------------------------------------------------------------

pub const BACKSLASH: char = '\\';
pub const NEWLINE: char = '\n';
/// U+2009
pub const THIN_SPACE: char = '\u{2009}';
/// U+202F
pub const NARROW_NON_BREAK_SPACE: char = '\u{202F}';
/// U+00A0
pub const NON_BREAK_SPACE: char = '\u{00A0}';

// ---------------------------------------------------------------------------
// Numeric limits
// ---------------------------------------------------------------------------

/// Maximum footnote character count before truncation (general Bibles).
pub const MAX_FOOTNOTE_CHARS: usize = 11_500;
/// Maximum footnote character count for NET Bible (which has longer footnotes).
pub const MAX_NET_FOOTNOTE_CHARS: usize = 18_000;

// ---------------------------------------------------------------------------
// Compiled regexes – footnote / cross-reference extraction
// ---------------------------------------------------------------------------

/// Matches `\x …\x*` cross-reference fields (non-greedy).
pub static XREF_REGEX: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r#"\\x .+?\\x\*"#).unwrap());

/// Matches `\f …\f*` footnote fields (non-greedy).
pub static FOOTNOTE_REGEX: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r#"\\f .+?\\f\*"#).unwrap());

/// Matches `<span class="…">` opening tags (non-greedy on the class value).
pub static SPAN_CLASS_REGEX: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r#"<span class=".+?">"#).unwrap());

// ---------------------------------------------------------------------------
// Compiled regexes – figure attributes (shared with character_formatting)
// ---------------------------------------------------------------------------

pub static FIG_SRC_REGEX: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r#"src="([^"]+?)""#).unwrap());

pub static FIG_SIZE_REGEX: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r#"size="([^"]+?)""#).unwrap());

pub static FIG_REF_REGEX: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r#"ref="([^"]+?)""#).unwrap());

pub static FIG_ALT_REGEX: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r#"alt="([^"]+?)""#).unwrap());

pub static FIG_LOC_REGEX: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r#"loc="([^"]+?)""#).unwrap());

pub static FIG_COPY_REGEX: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r#"copy="([^"]+?)""#).unwrap());

// ---------------------------------------------------------------------------
// Speaker-name → CSS class mapping (Song of Solomon, Jeremiah)
// ---------------------------------------------------------------------------

pub static SP_CLASS_DICT: LazyLock<HashMap<&'static str, &'static str>> = LazyLock::new(|| {
    let mut m = HashMap::new();
    m.insert("The groom", "groom");
    m.insert("The bride", "bride");
    m.insert("Yerushalem\u{2019}s young women", "women");  // smart apostrophe
    m.insert("Yerushalem\u{2018}s young women", "women");  // curly opening apostrophe
    m.insert("Bride\u{2019}s older brothers", "brothers");
    m.insert("Bride\u{2018}s older brothers", "brothers");
    m.insert("Yirmeyah", "Yirmeyah");
    m.insert("The people", "people");
    m
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_character_constants() {
        assert_eq!(BACKSLASH, '\\');
        assert_eq!(NEWLINE, '\n');
        assert_eq!(THIN_SPACE as u32, 0x2009);
        assert_eq!(NARROW_NON_BREAK_SPACE as u32, 0x202F);
        assert_eq!(NON_BREAK_SPACE as u32, 0x00A0);
    }

    #[test]
    fn test_footnote_limits() {
        assert_eq!(MAX_FOOTNOTE_CHARS, 11_500);
        assert_eq!(MAX_NET_FOOTNOTE_CHARS, 18_000);
    }

    #[test]
    fn test_xref_regex() {
        let sample = r#"See \x - Matt 5:16; John 3:16.\x* for more."#;
        assert!(XREF_REGEX.is_match(sample));
        let caps = XREF_REGEX.captures(sample).unwrap();
        assert_eq!(&caps[0], r#"\x - Matt 5:16; John 3:16.\x*"#);
    }

    #[test]
    fn test_footnote_regex() {
        let sample = r#"Text \f - Footnote here.\f* more text"#;
        assert!(FOOTNOTE_REGEX.is_match(sample));
        let caps = FOOTNOTE_REGEX.captures(sample).unwrap();
        assert_eq!(&caps[0], r#"\f - Footnote here.\f*"#);
    }

    #[test]
    fn test_fig_regexes() {
        let fig = r#"src="41_Mk_01_06_RG.jpg" size="col" ref="1:9" loc="1:9" copy="© Sweet""#;
        assert_eq!(&FIG_SRC_REGEX.captures(fig).unwrap()[1], "41_Mk_01_06_RG.jpg");
        assert_eq!(&FIG_SIZE_REGEX.captures(fig).unwrap()[1], "col");
        assert_eq!(&FIG_REF_REGEX.captures(fig).unwrap()[1], "1:9");
        assert_eq!(&FIG_COPY_REGEX.captures(fig).unwrap()[1], "© Sweet");
    }

    #[test]
    fn test_span_class_regex() {
        let html = r#"<span class="ior">5:13</span>"#;
        assert!(SPAN_CLASS_REGEX.is_match(html));
        assert_eq!(SPAN_CLASS_REGEX.find(html).unwrap().as_str(), r#"<span class="ior">"#);
    }

    #[test]
    fn test_sp_class_dict() {
        assert_eq!(SP_CLASS_DICT["The groom"], "groom");
        assert_eq!(SP_CLASS_DICT["The bride"], "bride");
        assert_eq!(SP_CLASS_DICT["The people"], "people");
        assert_eq!(SP_CLASS_DICT["Yirmeyah"], "Yirmeyah");
    }
}
