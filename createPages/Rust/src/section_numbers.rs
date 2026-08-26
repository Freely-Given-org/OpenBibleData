//! Rust port of `findSectionNumber` from `createSectionPages.py`.
//!
//! Given a BCV reference and the list of prebuilt section entries for one
//! book of one Bible version, return the index of the section that contains
//! the reference (or `None` if no section covers it).
//!
//! Changelog:
//!  2026-08-26: Added `SectionLookupCache` and `cached_find_section_fn` for
//!              pre-extracting section data into Rust, eliminating per-verse
//!              Python callbacks during footnote/cross-reference processing.

use std::collections::HashMap;

/// Minimal data for one entry of a `state.sectionsListsForSections` list --
/// exactly the fields that the section-number search needs.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SectionEntry {
    /// Starting chapter, e.g., `"1"` or `"-1"` for document introductions.
    pub start_c: String,
    /// Starting verse, e.g., `"1"` or `"17a"`.
    pub start_v: String,
    /// Ending chapter.
    pub end_c: String,
    /// Ending verse.
    pub end_v: String,
    /// Raw reason marker (e.g., `'s1'`, `'ms1/c'`, `'Headers'`) or a display
    /// name such as `'Alternate …'` for alternative headings, which are
    /// skipped by the search but keep consuming an index.
    pub reason_marker: String,
}

impl SectionEntry {
    pub fn new(
        start_c: &str,
        start_v: &str,
        end_c: &str,
        end_v: &str,
        reason_marker: &str,
    ) -> Self {
        Self {
            start_c: start_c.to_string(),
            start_v: start_v.to_string(),
            end_c: end_c.to_string(),
            end_v: end_v.to_string(),
            reason_marker: reason_marker.to_string(),
        }
    }
}

/// Extract the leading integer from a string
/// (like BibleOrgSys' `getSmallLeadingInt`, e.g., `"17a"` → `17`, `"-1"` → `-1`).
///
/// Returns `0` when there is no leading integer (the Python code would raise
/// in that case, but such strings never occur in practice).
fn get_small_leading_int(s: &str) -> i64 {
    let unsigned = s.strip_prefix('-').unwrap_or(s);
    let sign: i64 = if unsigned.len() < s.len() { -1 } else { 1 };
    let digit_count = unsigned
        .bytes()
        .take_while(|b| b.is_ascii_digit())
        .count();
    if digit_count == 0 {
        0
    } else {
        sign * unsigned[..digit_count].parse::<i64>().unwrap_or(0)
    }
}

/// Parse a complete chapter number string like Python's `int()`
/// (returns `0` for unparseable strings instead of raising).
fn parse_chapter_int(s: &str) -> i64 {
    s.trim().parse().unwrap_or(0)
}

/// Find the index of the section containing the given chapter/verse reference.
///
/// Faithful port of the search loop in `createSectionPages.findSectionNumber`
/// -- note that the returned index is the position in the *full* list,
/// including any skipped `'Alternate …'` entries.
pub fn find_section_number_core(
    sections: &[SectionEntry],
    ref_c: &str,
    ref_v: &str,
) -> Option<usize> {
    // Verse '0' really means verse '1' (i.e., the start of the chapter)
    let adjusted_ref_v = if ref_v == "0" { "1" } else { ref_v };
    let int_ref_v = get_small_leading_int(adjusted_ref_v);

    for (n, entry) in sections.iter().enumerate() {
        if entry.reason_marker.starts_with("Alternate ") {
            continue; // ignore these ones
        }

        if entry.start_c == ref_c && entry.end_c == ref_c {
            // This section only spans a single chapter (or part of a chapter)
            if get_small_leading_int(&entry.start_v) <= int_ref_v
                && int_ref_v <= get_small_leading_int(&entry.end_v)
            {
                return Some(n); // It's in this single chapter
            }
        } else {
            // This section spans two or more chapters
            if entry.start_c == ref_c && int_ref_v >= get_small_leading_int(&entry.start_v) {
                return Some(n); // It's in the first chapter
            } else if entry.end_c == ref_c && int_ref_v <= get_small_leading_int(&entry.end_v) {
                return Some(n); // It's in the last chapter
            } else if parse_chapter_int(&entry.start_c) < parse_chapter_int(ref_c)
                && parse_chapter_int(ref_c) < parse_chapter_int(&entry.end_c)
            {
                return Some(n); // It's in one of the middle chapters
            }
        }
    }
    None
}

// ── Pre-extracted section lookup cache ─────────────────────────────────────

/// Pre-extracted section data for one book of one version.
#[derive(Debug, Clone)]
pub struct BookSections {
    pub sections: Vec<SectionEntry>,
}

/// Pre-extracted section lookup cache: version_abbreviation → bos_book_code → sections.
///
/// Built once per `convertVerseEntryListToHtml` call from `state.sectionsListsForSections`,
/// then used as a pure-Rust closure — no Python callbacks needed for section lookups.
#[derive(Debug, Clone)]
pub struct SectionLookupCache {
    data: HashMap<String, HashMap<String, BookSections>>,
}

impl SectionLookupCache {
    pub fn new() -> Self {
        Self { data: HashMap::new() }
    }

    pub fn insert(&mut self, version_abbrev: String, bos_book_code: String, sections: Vec<SectionEntry>) {
        self.data.entry(version_abbrev)
            .or_default()
            .insert(bos_book_code, BookSections { sections });
    }

    pub fn lookup(&self, version_abbrev: &str, bos_book_code: &str, ref_c: &str, ref_v: &str) -> Option<usize> {
        let book_sections = self.data.get(version_abbrev)?.get(bos_book_code)?;
        find_section_number_core(&book_sections.sections, ref_c, ref_v)
    }

    /// Returns true if the cache contains data for the given version and book.
    pub fn has_entry(&self, version_abbrev: &str, bos_book_code: &str) -> bool {
        self.data.get(version_abbrev)
            .and_then(|books| books.get(bos_book_code))
            .is_some()
    }
}

/// Create a pure-Rust section lookup closure from a pre-extracted cache.
///
/// This eliminates the Python callback overhead (import + getattr + call per verse)
/// that `py_find_section_fn` incurs. Falls back to `None` for entries not in the cache.
pub fn cached_find_section_fn(cache: &SectionLookupCache) -> impl Fn(&str, &str, &str, &str) -> Option<usize> + '_ {
    move |version_abbrev: &str, bos_book_code: &str, ref_c: &str, ref_v: &str| -> Option<usize> {
        cache.lookup(version_abbrev, bos_book_code, ref_c, ref_v)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sections(list: &[(&str, &str, &str, &str, &str)]) -> Vec<SectionEntry> {
        list.iter()
            .map(|(sc, sv, ec, ev, r)| SectionEntry::new(sc, sv, ec, ev, r))
            .collect()
    }

    // ── get_small_leading_int ──────────────────────────────────────────────

    #[test]
    fn small_leading_int_basics() {
        assert_eq!(get_small_leading_int("17a"), 17);
        assert_eq!(get_small_leading_int("5"), 5);
        assert_eq!(get_small_leading_int("0"), 0);
        assert_eq!(get_small_leading_int("-1"), -1);
        assert_eq!(get_small_leading_int(""), 0);
        assert_eq!(get_small_leading_int("abc"), 0);
    }

    // ── Single-chapter sections ────────────────────────────────────────────

    #[test]
    fn single_chapter_in_range_matches() {
        let secs = sections(&[("1", "1", "1", "31", "s1"), ("2", "1", "2", "25", "s1")]);
        assert_eq!(find_section_number_core(&secs, "1", "15"), Some(0));
        assert_eq!(find_section_number_core(&secs, "1", "31"), Some(0)); // last verse
        assert_eq!(find_section_number_core(&secs, "2", "1"), Some(1)); // first verse
        assert_eq!(find_section_number_core(&secs, "2", "25"), Some(1));
    }

    #[test]
    fn single_chapter_outside_range_does_not_match() {
        let secs = sections(&[("1", "1", "1", "31", "s1"), ("2", "1", "2", "25", "s1")]);
        assert_eq!(find_section_number_core(&secs, "1", "32"), None);
        assert_eq!(find_section_number_core(&secs, "3", "1"), None);
    }

    #[test]
    fn verse_zero_is_adjusted_to_verse_one() {
        let secs = sections(&[("2", "1", "2", "25", "s1")]);
        assert_eq!(find_section_number_core(&secs, "2", "0"), Some(0));
    }

    #[test]
    fn verse_suffixes_are_ignored() {
        let secs = sections(&[("1", "5a", "1", "10", "s1")]);
        assert_eq!(find_section_number_core(&secs, "1", "5"), Some(0));
        assert_eq!(find_section_number_core(&secs, "1", "5b"), Some(0));
        assert_eq!(find_section_number_core(&secs, "1", "4"), None);
    }

    // ── Multi-chapter sections ─────────────────────────────────────────────

    #[test]
    fn multi_chapter_first_chapter_at_or_after_start_verse() {
        let secs = sections(&[("1", "5", "3", "10", "s1")]);
        assert_eq!(find_section_number_core(&secs, "1", "5"), Some(0));
        assert_eq!(find_section_number_core(&secs, "1", "30"), Some(0));
    }

    #[test]
    fn multi_chapter_first_chapter_before_start_verse_does_not_match() {
        let secs = sections(&[("1", "5", "3", "10", "s1")]);
        assert_eq!(find_section_number_core(&secs, "1", "4"), None);
    }

    #[test]
    fn multi_chapter_middle_chapters_always_match() {
        let secs = sections(&[("1", "5", "3", "10", "s1")]);
        assert_eq!(find_section_number_core(&secs, "2", "1"), Some(0));
        assert_eq!(find_section_number_core(&secs, "2", "48"), Some(0));
    }

    #[test]
    fn multi_chapter_last_chapter_at_or_before_end_verse() {
        let secs = sections(&[("1", "5", "3", "10", "s1")]);
        assert_eq!(find_section_number_core(&secs, "3", "10"), Some(0));
        assert_eq!(find_section_number_core(&secs, "3", "1"), Some(0));
    }

    #[test]
    fn multi_chapter_last_chapter_after_end_verse_does_not_match() {
        let secs = sections(&[("1", "5", "3", "10", "s1")]);
        assert_eq!(find_section_number_core(&secs, "3", "11"), None);
    }

    #[test]
    fn multi_chapter_boundaries_are_exclusive_for_middle_chapters() {
        // refC must be strictly between startC and endC
        let secs = sections(&[("2", "24", "5", "17", "s1")]);
        // Chapters 2 and 5 are handled by first/last-chapter rules above;
        // check that a non-covering chapter just outside the range fails.
        assert_eq!(find_section_number_core(&secs, "6", "1"), None);
        assert_eq!(find_section_number_core(&secs, "1", "1"), None);
    }

    // ── Alternate headings are skipped but keep their index ────────────────

    #[test]
    fn alternate_entries_are_skipped_but_indices_preserved() {
        let secs = sections(&[
            ("1", "1", "1", "10", "s1"),
            ("1", "1", "1", "99", "Alternate section heading"),
            ("2", "1", "2", "20", "s1"),
        ]);
        assert_eq!(find_section_number_core(&secs, "1", "5"), Some(0));
        // The match in chapter 2 lives at index 2, not 1
        assert_eq!(find_section_number_core(&secs, "2", "5"), Some(2));
    }

    // ── Introduction sections (negative chapter numbers) ────────────────────

    #[test]
    fn introduction_sections_use_negative_chapters() {
        let secs = sections(&[
            ("-1", "0", "-1", "12", "Headers"),
            ("-1", "14", "-1", "30", "is1"),
        ]);
        assert_eq!(find_section_number_core(&secs, "-1", "5"), Some(0));
        assert_eq!(find_section_number_core(&secs, "-1", "20"), Some(1));
        assert_eq!(find_section_number_core(&secs, "-1", "13"), None);
        assert_eq!(find_section_number_core(&secs, "-1", "0"), Some(0)); // '0' → '1'
    }

    // ── Realistic OET-RV Daniel-style data (ms1-only entries already removed) ──

    #[test]
    fn daniel_style_lookup() {
        let secs = sections(&[
            ("-1", "0", "-1", "12", "Headers"),
            ("-1", "14", "-1", "30", "is1"),
            ("1", "1", "1", "21", "s1/c"),
            ("2", "1", "2", "23", "s1/c"),
            ("2", "24", "2", "45", "s1"),
            ("3", "1", "3", "7", "s1/c"),
        ]);
        assert_eq!(find_section_number_core(&secs, "1", "1"), Some(2));
        assert_eq!(find_section_number_core(&secs, "1", "21"), Some(2));
        assert_eq!(find_section_number_core(&secs, "2", "30"), Some(4));
        assert_eq!(find_section_number_core(&secs, "2", "23"), Some(3));
        assert_eq!(find_section_number_core(&secs, "3", "5"), Some(5));
        assert_eq!(find_section_number_core(&secs, "-1", "20"), Some(1));
    }

    // ── Misc ────────────────────────────────────────────────────────────────

    #[test]
    fn empty_section_list_returns_none() {
        let secs: Vec<SectionEntry> = Vec::new();
        assert_eq!(find_section_number_core(&secs, "1", "1"), None);
    }

    #[test]
    fn first_matching_section_wins() {
        let secs = sections(&[("1", "1", "1", "10", "s1"), ("1", "1", "1", "20", "s1")]);
        assert_eq!(find_section_number_core(&secs, "1", "5"), Some(0));
    }

    #[test]
    fn unknown_reference_chapter_returns_none() {
        let secs = sections(&[("1", "1", "1", "31", "s1"), ("2", "1", "2", "25", "s1")]);
        assert_eq!(find_section_number_core(&secs, "9", "9"), None);
    }

    // ── SectionLookupCache ────────────────────────────────────────────────

    #[test]
    fn cache_lookup_basic() {
        let mut cache = SectionLookupCache::new();
        cache.insert(
            "OET-RV".into(), "GEN".into(),
            sections(&[("1", "1", "1", "31", "s1"), ("2", "1", "2", "25", "s1")]),
        );
        assert_eq!(cache.lookup("OET-RV", "GEN", "1", "15"), Some(0));
        assert_eq!(cache.lookup("OET-RV", "GEN", "2", "10"), Some(1));
    }

    #[test]
    fn cache_lookup_missing_version_returns_none() {
        let cache = SectionLookupCache::new();
        assert_eq!(cache.lookup("MISSING", "GEN", "1", "1"), None);
    }

    #[test]
    fn cache_lookup_missing_book_returns_none() {
        let mut cache = SectionLookupCache::new();
        cache.insert("OET-RV".into(), "GEN".into(), sections(&[("1", "1", "1", "31", "s1")]));
        assert_eq!(cache.lookup("OET-RV", "EXO", "1", "1"), None);
    }

    #[test]
    fn cache_has_entry() {
        let mut cache = SectionLookupCache::new();
        cache.insert("OET-RV".into(), "GEN".into(), sections(&[("1", "1", "1", "31", "s1")]));
        assert!(cache.has_entry("OET-RV", "GEN"));
        assert!(!cache.has_entry("OET-RV", "EXO"));
        assert!(!cache.has_entry("KJB", "GEN"));
    }

    #[test]
    fn cached_find_section_fn_works() {
        let mut cache = SectionLookupCache::new();
        cache.insert(
            "OET-RV".into(), "GEN".into(),
            sections(&[("1", "1", "1", "31", "s1"), ("2", "1", "2", "25", "s1")]),
        );
        let closure = cached_find_section_fn(&cache);
        assert_eq!(closure("OET-RV", "GEN", "1", "15"), Some(0));
        assert_eq!(closure("OET-RV", "GEN", "2", "10"), Some(1));
        assert_eq!(closure("OET-RV", "EXO", "1", "1"), None);
        assert_eq!(closure("KJB", "GEN", "1", "1"), None);
    }
}
