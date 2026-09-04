//! PyO3 module exposing OpenBibleData Rust extensions.

use pyo3::exceptions::{
    PyAssertionError, PyIndexError, PyKeyError, PyTypeError, PyUnboundLocalError, PyValueError,
};
use pyo3::prelude::*;
use pyo3::types::PyAny;

pub mod constants;
pub mod intro_links;
pub mod ior_links;
pub mod oet_books;
pub mod oet_handlers;
pub mod page_chrome;
pub mod roman_numerals;
pub mod section_numbers;
pub mod character_formatting;
pub mod html_validation;
pub mod xref_links;
pub mod verse_to_html;
pub mod verse_entry_list;

pub use intro_links::{liven_introduction_links_core, IntroLinkError};
pub use ior_links::{liven_iors_core, IORLinkError};
pub use roman_numerals::to_roman_numerals;
pub use character_formatting::{convert_usfm_character_formatting, CharacterFormattingResult};
pub use html_validation::check_html;

/// Build a section-number lookup callback that calls back into Python's
/// `createSectionPages.findSectionNumber` via the optional State object.
///
/// All PyO3 wrappers that need live section numbers use this shared helper;
/// the actual linking logic lives in the pure-Rust `*_core` functions.
fn py_find_section_fn<'s>(
    state: Option<&'s Bound<'_, PyAny>>,
) -> impl Fn(&str, &str, &str, &str) -> Option<usize> + Clone + 's {
    move |v_abbr: &str, bos_book_code: &str, c: &str, v: &str| -> Option<usize> {
        if let Some(state_obj) = state {
            let py_env = state_obj.py();
            if let Ok(module) = py_env.import("createSectionPages") {
                if let Ok(func) = module.getattr("findSectionNumber") {
                    if let Ok(res) = func.call1((v_abbr, bos_book_code, c, v, state_obj)) {
                        if let Ok(opt_num) = res.extract::<Option<usize>>() {
                            return opt_num;
                        }
                    }
                }
            }
        }
        None
    }
}

/// Build a book-availability callback that checks the optional State object's
/// `booksToLoad` (mirroring Python's
/// `'ALL' in state.booksToLoad[vAbbr] or bos_book_code in state.booksToLoad[vAbbr]`).
///
/// Returns true when no State is supplied (e.g., from test programs), so that
/// behaviour stays permissive there.
fn py_is_book_available_fn<'s>(
    state: Option<&'s Bound<'_, PyAny>>,
) -> impl Fn(&str, &str) -> bool + Clone + 's {
    move |v_abbr: &str, bos_book_code: &str| -> bool {
        if let Some(state_obj) = state {
            let books_to_load = match state_obj.getattr("booksToLoad") {
                Ok(btl) if !btl.is_none() => btl,
                _ => return true, // can't determine -- stay permissive
            };
            let book_list = match books_to_load.get_item(v_abbr) {
                Ok(list) if !list.is_none() => list,
                _ => return true,
            };
            if let Ok(iter) = book_list.try_iter() {
                for item in iter.flatten() {
                    if let Ok(entry) = item.extract::<String>() {
                        if entry == "ALL" || entry == bos_book_code {
                            return true;
                        }
                    }
                }
            }
            return false;
        }
        true
    }
}

/// Log a message through Python's logging module so that it appears in the
/// same place as the messages logged by the Python build scripts.
fn log_message(py: Python<'_>, level: &str, message: &str) {
    if let Ok(logging) = py.import("logging") {
        let _ = logging.call_method1(level, (message,));
    }
}

// ── Section lookup cache ──────────────────────────────────────────────────

/// Pre-extract section lookup data from `state.sectionsListsForSections` into
/// a pure-Rust `SectionLookupCache`.  This eliminates per-verse Python
/// callbacks for section lookups during footnote/cross-reference processing.
///
/// Returns `None` if state is `None` or the attribute is missing.
fn build_section_lookup_cache(state: Option<&Bound<'_, PyAny>>) -> Option<section_numbers::SectionLookupCache> {
    let state_obj = state?;
    let sections_lists = state_obj.getattr("sectionsListsForSections").ok()?;

    let mut cache = section_numbers::SectionLookupCache::new();

    // Collect version keys first to avoid borrowing issues
    let version_keys: Vec<String> = sections_lists.try_iter().ok()?
        .filter_map(|item| item.ok())
        .filter_map(|item| item.extract().ok())
        .collect();

    for version_abbrev in version_keys {
        let version_dict = match sections_lists.get_item(&version_abbrev) {
            Ok(v) => v,
            Err(_) => continue,
        };

        // Collect book keys for this version
        let book_keys: Vec<String> = match version_dict.try_iter() {
            Ok(iter) => iter.filter_map(|item| item.ok())
                .filter_map(|item| item.extract().ok())
                .collect(),
            Err(_) => continue,
        };

        for bos_book_code in book_keys {
            let book_list = match version_dict.get_item(&bos_book_code) {
                Ok(v) => v,
                Err(_) => continue,
            };

            // Extract section entries (same fields as find_section_number_py)
            let mut sections = Vec::new();
            if let Ok(iter) = book_list.try_iter() {
                for item in iter.flatten() {
                    if let (Ok(start_c), Ok(start_v), Ok(end_c), Ok(end_v), Ok(reason_marker)) = (
                        item.get_item(1).and_then(|v| v.extract()),
                        item.get_item(2).and_then(|v| v.extract()),
                        item.get_item(3).and_then(|v| v.extract()),
                        item.get_item(4).and_then(|v| v.extract()),
                        item.get_item(6).and_then(|v| v.extract()),
                    ) {
                        sections.push(section_numbers::SectionEntry {
                            start_c, start_v, end_c, end_v, reason_marker,
                        });
                    }
                }
            }

            cache.insert(version_abbrev.clone(), bos_book_code, sections);
        }
    }

    Some(cache)
}

// ── section_numbers PyO3 wrapper ───────────────────────────────────────────

/// Find the section number containing the given BCV reference
/// (Rust port of `createSectionPages.findSectionNumber`).
///
/// Reads the prebuilt `state.sectionsListsForSections[versionAbbreviation][refBBB]`
/// list (tuples of `(n,startC,startV,endC,endV,sectionName,reasonMarker,…)`)
/// and runs the search loop from `section_numbers::find_section_number_core`.
#[pyfunction]
#[pyo3(
    name = "findSectionNumber",
    signature = (versionAbbreviation, refBBB, refC, refV, state=None)
)]
#[allow(non_snake_case)]
fn find_section_number_py<'py>(
    py: Python<'py>,
    versionAbbreviation: &str,
    refBBB: &str,
    refC: &str,
    refV: &str,
    state: Option<&Bound<'py, PyAny>>,
) -> PyResult<Option<usize>> {
    let Some(state_obj) = state else {
        return Ok(None); // Can't do anything without State to read the sections lists from
    };
    if refBBB.is_empty() {
        return Ok(None); // Can't do anything without a valid BBB
    }

    // BOOKLIST_66 membership via the linked-in bos_books_codes crate
    // (reference numbers 1..66 are exactly the 66 canonical books).
    if !bos_books_codes::is_old_testament_nr(refBBB) && !bos_books_codes::is_new_testament_nr(refBBB)
    {
        // Only continue for versions that include the Apocrypha books
        let mut is_version_with_apocrypha = false;
        if let Ok(apocrypha_versions) = state_obj.getattr("VERSIONS_WITH_APOCRYPHA") {
            if let Ok(iter) = apocrypha_versions.try_iter() {
                for item in iter.flatten() {
                    if let Ok(va) = item.extract::<String>() {
                        if va == versionAbbreviation {
                            is_version_with_apocrypha = true;
                            break;
                        }
                    }
                }
            }
        }
        if !is_version_with_apocrypha {
            log_message(
                py,
                "warning",
                &format!(
                    "Unable to continue in findSectionNumber( {versionAbbreviation}, {refBBB} {refC}:{refV} )"
                ),
            );
            return Ok(None); // Can't do anything here
        }
    }

    // This raises KeyError like the original Python code when we have no
    // sectionsLists at all for this version.
    let version_sections_lists = state_obj.getattr("sectionsListsForSections")?.get_item(versionAbbreviation)?;

    let test_mode_flag: bool = state_obj
        .getattr("TEST_MODE_FLAG")
        .and_then(|v| v.extract())
        .unwrap_or(false);

    let has_book = version_sections_lists
        .call_method1("__contains__", (refBBB,))?
        .is_truthy()?;
    if !has_book {
        // No section headings for this book
        if test_mode_flag {
            return Ok(Some(0)); // default to introduction for testing (because it doesn't contain all the books)
        }
        let available_keys: Vec<String> = version_sections_lists
            .try_iter()?
            .filter_map(|item| item.ok())
            .filter_map(|item| item.extract().ok())
            .collect();
        log_message(
            py,
            "error",
            &format!(
                "findSectionNumber: No {versionAbbreviation} sectionsLists for {refBBB} -- only have {available_keys:?} -- returning None"
            ),
        );
        return Ok(None);
    }

    // Extract just the fields that the search needs from each
    // (n,startC,startV,endC,endV,sectionName,reasonMarker,contextList,verseEntryList,filename) tuple.
    let book_sections_list = version_sections_lists.get_item(refBBB)?;
    let mut sections = Vec::with_capacity(64);
    for item in book_sections_list.try_iter()? {
        let item = item?;
        sections.push(section_numbers::SectionEntry {
            start_c: item.get_item(1)?.extract()?,
            start_v: item.get_item(2)?.extract()?,
            end_c: item.get_item(3)?.extract()?,
            end_v: item.get_item(4)?.extract()?,
            reason_marker: item.get_item(6)?.extract()?,
        });
    }

    Ok(section_numbers::find_section_number_core(&sections, refC, refV))
}

/// Liven introduction links in HTML text using Rust.
///
/// Currently only called from Python test programs — production Python reaches
/// this logic via `convertVerseEntryListToHtml`, which calls
/// `intro_links::liven_introduction_links_core` internally.
#[pyfunction]
#[pyo3(
    name = "liven_introduction_links",
    signature = (version_abbreviation, ref_tuple, segment_type, intro_html, state=None)
)]
fn liven_introduction_links_py<'py>(
    _py: Python<'py>,
    version_abbreviation: &str,
    ref_tuple: &Bound<'py, PyAny>,
    segment_type: &str,
    intro_html: &str,
    state: Option<&Bound<'py, PyAny>>,
) -> PyResult<String> {
    let our_bos_book_code: String = if let Ok(tuple) = ref_tuple.extract::<Vec<String>>() {
        if tuple.is_empty() {
            return Err(PyValueError::new_err("ref_tuple must not be empty"));
        }
        if segment_type.ends_with("Verse") && tuple.len() > 1 && tuple[1] != "-1" {
            return Err(PyAssertionError::new_err(format!(
                "Expected refTuple[1] == '-1', got {:?}",
                tuple
            )));
        }
        tuple[0].clone()
    } else if let Ok(s) = ref_tuple.extract::<String>() {
        s
    } else {
        return Err(PyTypeError::new_err(
            "ref_tuple must be a tuple or list of strings",
        ));
    };

    let find_section_fn = py_find_section_fn(state);

    match liven_introduction_links_core(
        version_abbreviation,
        &our_bos_book_code,
        segment_type,
        intro_html,
        find_section_fn,
    ) {
        Ok(res) => Ok(res),
        Err(IntroLinkError::ContainsIorMarker) => {
            Err(PyAssertionError::new_err(r#"intro_html must not contain '\ior' or 'class="ior"'"#))
        }
        Err(IntroLinkError::InvalidSegmentType(seg)) => {
            Err(PyValueError::new_err(format!("Unsupported segmentType: {seg}")))
        }
        Err(IntroLinkError::Custom(msg)) => Err(PyValueError::new_err(msg)),
    }
}

/// Convert an integer or integer string to Roman numerals.
///
/// Currently only called from Python test programs — production Python reaches
/// this logic via `convertVerseEntryListToHtml`, which calls
/// `roman_numerals::to_roman_numerals` internally.
#[pyfunction]
#[pyo3(name = "to_roman_numerals")]
fn to_roman_numerals_py(num: &Bound<'_, PyAny>) -> PyResult<String> {
    let val: u32 = if let Ok(i) = num.extract::<i64>() {
        if i <= 0 {
            return Ok(String::new());
        }
        i as u32
    } else if let Ok(s) = num.extract::<String>() {
        let trimmed = s.trim();
        if trimmed.is_empty() {
            return Ok(String::new());
        }
        match trimmed.parse::<i64>() {
            Ok(i) if i <= 0 => return Ok(String::new()),
            Ok(i) => i as u32,
            Err(_) => {
                return Err(PyValueError::new_err(format!(
                    "Cannot parse '{s}' as integer for Roman numerals"
                )))
            }
        }
    } else {
        return Err(PyTypeError::new_err("num must be an int or a str"));
    };

    Ok(to_roman_numerals(val))
}

/// Liven IOR (Introduction Outline Reference) links in HTML text using Rust.
///
/// Currently only called from Python test programs — production Python reaches
/// this logic via `convertVerseEntryListToHtml`, which calls
/// `ior_links::liven_iors_core` internally.
#[pyfunction]
#[pyo3(
    name = "liven_iors",
    signature = (version_abbreviation, our_bos_book_code, segment_type, ior_html, is_single_chapter, level=0, state=None)
)]
fn liven_iors_py<'py>(
    _py: Python<'py>,
    version_abbreviation: &str,
    our_bos_book_code: &str,
    segment_type: &str,
    ior_html: &str,
    is_single_chapter: bool,
    level: usize,
    state: Option<&Bound<'py, PyAny>>,
) -> PyResult<String> {
    let find_section_fn = py_find_section_fn(state);

    match liven_iors_core(version_abbreviation, our_bos_book_code, segment_type, ior_html, is_single_chapter, level, find_section_fn) {
        Ok(res) => Ok(res),
        Err(IORLinkError::InvalidSegmentType(seg)) => {
            Err(PyValueError::new_err(format!("Unsupported segmentType: {seg}")))
        }
        Err(IORLinkError::Custom(msg)) => Err(PyValueError::new_err(msg)),
    }
}

/// Convert USFM character formatting to HTML using Rust.
///
/// Currently only called from Python test programs — production Python reaches
/// this logic via `convertVerseEntryListToHtml`, which calls
/// `character_formatting::convert_usfm_character_formatting` internally.
#[pyfunction]
#[pyo3(
    name = "convert_usfm_character_formatting",
    signature = (version_abbrev, bos_book_code, segment_type, usfm_field, basic_only, expanded_char_markers, booklist_nt27, is_net_version, level=0)
)]
fn convert_usfm_character_formatting_py(
    py: Python,
    version_abbrev: &str,
    bos_book_code: &str,
    segment_type: &str,
    usfm_field: &str,
    basic_only: bool,
    expanded_char_markers: Vec<String>,
    booklist_nt27: Vec<String>,
    is_net_version: bool,
    level: usize,
) -> PyResult<Py<PyAny>> {
    use pyo3::types::PyDict;

    let mut background_colour: Option<String> = None;
    let result = convert_usfm_character_formatting(
        version_abbrev,
        bos_book_code,
        segment_type,
        usfm_field,
        basic_only,
        &mut background_colour,
        &expanded_char_markers,
        &booklist_nt27,
        is_net_version,
        level,
    );

    let dict = PyDict::new(py);
    dict.set_item("html", result.html)?;
    dict.set_item("background_colour", background_colour)?;
    dict.set_item("files_to_copy", result.files_to_copy)?;
    Ok(dict.into())
}

// ── verse_entry_list PyO3 wrapper ──────────────────────────────────────────

/// Convert a list of verse entries to HTML using Rust.
///
/// This is the Rust port of `convertVerseEntryListToHtml` from `usfm.py`;
/// the former thin Python wrapper (`convert.py`) has been absorbed into this
/// function. Character formatting, footnotes, cross-references, and figure
/// copying are handled here in Rust; Python is only called back for OBI
/// images, HTML validation, and section-number lookup.
///
/// The single-chapter-book flag is looked up directly from the parallel
/// bos_books_codes crate, so it doesn't need to be passed as a parameter.
#[pyfunction]
#[pyo3(name = "convertVerseEntryListToHtml")]
#[pyo3(signature = (
    level,
    versionAbbreviation,
    refTuple,
    segmentType,
    contextList=None,
    verseEntryList=None,
    basicOnly=false,
    state=None,
))]
#[allow(non_snake_case)]
fn convert_verse_entry_list_to_html_py<'py>(
    level: usize,
    versionAbbreviation: &str,
    refTuple: Vec<String>,
    segmentType: &str,
    contextList: Option<Vec<String>>,
    verseEntryList: Option<Vec<Bound<'py, PyAny>>>,
    basicOnly: bool,
    state: Option<&Bound<'py, PyAny>>,
) -> PyResult<String> {
    let context_list = contextList.unwrap_or_default();
    let verse_entries = verseEntryList.unwrap_or_default();

    // Split up the reference tuple: (bos_book_code,), (bos_book_code,C), or (bos_book_code,C,V)
    let bos_book_code = refTuple.first().map(String::as_str)
        .ok_or_else(|| PyValueError::new_err("Empty refTuple"))?;
    let c = refTuple.get(1).map(String::as_str);
    let v = refTuple.get(2).map(String::as_str);

    // bos_books_codes is linked in directly, so we don't need this passed as a parameter
    let is_single_chapter_book = bos_books_codes::is_single_chapter_book(bos_book_code);

    // Formerly done in convert.py
    let destination_folder: Option<String> = match state {
        Some(state_obj) => match state_obj.getattr("DESTINATION_FOLDER") {
            Ok(dest) if !dest.is_none() => {
                let py_str = dest.str()?;
                Some(py_str.to_str()?.to_owned())
            }
            _ => None,
        },
        None => None,
    };

    // Extract verse entries — accept both InternalBibleEntry (methods) and simple objects (attributes)
    let mut entries = Vec::with_capacity(verse_entries.len());
    for py_entry in &verse_entries {
        // Try InternalBibleEntry methods first, fall back to attributes
        let (marker, full_text, clean_text) = if let Ok(m) = py_entry.call_method0("getMarker") {
            let marker: String = m.extract()?;
            let full_text: String = py_entry.call_method0("getFullText")?.extract()?;
            let clean_text: String = py_entry.call_method0("getCleanText")?.extract()?;
            (marker, full_text, clean_text)
        } else {
            let marker: String = py_entry.getattr("marker")?.extract()?;
            let full_text: String = py_entry.getattr("full_text")?.extract()?;
            let clean_text: String = py_entry.getattr("clean_text")?.extract()?;
            (marker, full_text, clean_text)
        };
        entries.push(verse_entry_list::VerseEntry { marker, full_text, clean_text });
    }

    // Build find_section_fn callback — pre-extract section data into Rust
    // to eliminate per-verse Python callbacks during footnote/xref processing.
    let section_cache = build_section_lookup_cache(state)
        .unwrap_or_else(section_numbers::SectionLookupCache::new);
    let section_cache_rc = std::rc::Rc::new(section_cache);
    let find_section_fn = {
        let cache = section_cache_rc.clone();
        move |va: &str, bbb: &str, c: &str, v: &str| -> Option<usize> {
            cache.lookup(va, bbb, c, v)
        }
    };
    let is_book_available = py_is_book_available_fn(state);

    let no_op_obi = |_l: usize, _st: &str, _b: &str, _c: &str, _v: &str| -> Option<String> { None };
    let no_op_check = |_w: &str, _h: &str| -> bool { true };

    let context_refs: Vec<&str> = context_list.iter().map(|s| s.as_str()).collect();

    let result = verse_entry_list::convert_verse_entry_list_to_html_standalone(
        level,
        versionAbbreviation,
        bos_book_code,
        c,
        v,
        segmentType,
        &context_refs,
        &entries,
        basicOnly,
        is_single_chapter_book,
        find_section_fn,
        is_book_available,
        &no_op_obi,
        &no_op_check,
        destination_folder.as_deref(),
    );

    match result {
        Ok(html) => Ok(html),
        Err(e) => Err(PyValueError::new_err(format!("convertVerseEntryListToHtml failed: {e}"))),
    }
}
// ── verse_to_html PyO3 wrappers ───────────────────────────────────────────

/// Process cross-references in HTML, replacing `\x…\x*` markers with live links.
///
/// Returns `(html, cross_references_html)`.
///
/// Currently only called from Python test programs — production Python reaches
/// this logic via `convertVerseEntryListToHtml`, which calls
/// `verse_to_html::process_cross_references_core` internally.
#[pyfunction]
#[pyo3(name = "process_cross_references")]
#[pyo3(signature = (html, version_abbreviation, bos_book_code, c, segment_type, path_prefix, state=None))]
fn process_cross_references_py<'py>(
    _py: Python<'py>,
    html: &str,
    version_abbreviation: &str,
    bos_book_code: &str,
    c: Option<&str>,
    segment_type: &str,
    path_prefix: &str,
    state: Option<&Bound<'py, PyAny>>,
) -> PyResult<(String, String)> {
    let c = c.unwrap_or("");
    let find_section_fn = py_find_section_fn(state);

    match verse_to_html::process_cross_references_core(
        html, version_abbreviation, bos_book_code, c, segment_type, path_prefix, find_section_fn,
    ) {
        Ok(result) => Ok(result),
        Err(e) => Err(PyValueError::new_err(format!("process_cross_references failed: {e}"))),
    }
}

/// Process footnotes in HTML, replacing `\f…\f*` markers with caller links.
///
/// Returns `(html, footnotes_html)`.
///
/// Currently only called from Python test programs — production Python reaches
/// this logic via `convertVerseEntryListToHtml`, which calls
/// `verse_to_html::process_footnotes_core` internally.
#[pyfunction]
#[pyo3(name = "process_footnotes")]
#[pyo3(signature = (html, version_abbreviation, bos_book_code, c, segment_type, path_prefix, max_footnote_chars, state=None))]
fn process_footnotes_py<'py>(
    _py: Python<'py>,
    html: &str,
    version_abbreviation: &str,
    bos_book_code: &str,
    c: Option<&str>,
    segment_type: &str,
    path_prefix: &str,
    max_footnote_chars: usize,
    state: Option<&Bound<'py, PyAny>>,
) -> PyResult<(String, String)> {
    let c = c.unwrap_or("");
    let find_section_fn = py_find_section_fn(state);

    match verse_to_html::process_footnotes_core(
        html, version_abbreviation, bos_book_code, c, segment_type, path_prefix, max_footnote_chars, find_section_fn,
    ) {
        Ok(result) => Ok(result),
        Err(e) => Err(PyValueError::new_err(format!("process_footnotes failed: {e}"))),
    }
}

// ── page_chrome PyO3 wrappers ──────────────────────────────────────────────

/// Build a [`page_chrome::PageChromeConfig`] snapshot from a Python State
/// object by extracting every attribute that html.makeTop needs.
fn page_chrome_config_from_state(
    state: &Bound<'_, PyAny>,
) -> PyResult<page_chrome::PageChromeConfig> {
    let py = state.py();

    let test_mode_flag: bool = state.getattr("TEST_MODE_FLAG")?.extract()?;
    let site_name: String = state.getattr("SITE_NAME")?.extract()?;

    let bible_versions: Vec<String> = state
        .getattr("BibleVersions")?
        .try_iter()?
        .map(|item| item?.extract())
        .collect::<PyResult<Vec<String>>>()?;

    let versions_without_their_own_pages: std::collections::HashSet<String> = state
        .getattr("versionsWithoutTheirOwnPages")?
        .try_iter()?
        .map(|item| item?.extract())
        .collect::<PyResult<Vec<String>>>()?
        .into_iter()
        .collect();

    let test_versions_only_obj = state.getattr("TEST_VERSIONS_ONLY")?;
    let test_versions_only = if test_versions_only_obj.is_none() {
        None
    } else {
        Some(
            test_versions_only_obj
                .try_iter()?
                .map(|item| item?.extract())
                .collect::<PyResult<Vec<String>>>()?
                .into_iter()
                .collect::<std::collections::HashSet<String>>(),
        )
    };

    let all_bos_book_codes: Vec<String> = state
        .getattr("allBBBs")?
        .try_iter()?
        .map(|item| item?.extract())
        .collect::<PyResult<Vec<String>>>()?;

    // Decorations and names are plain dicts keyed by version abbreviation
    let decorations_dict = state.getattr("BibleVersionDecorations")?;
    let mut decorations = std::collections::HashMap::new();
    for key in decorations_dict.try_iter()? {
        let key: String = key?.extract()?;
        let pair: Vec<String> = decorations_dict.get_item(&key)?.extract()?;
        if pair.len() != 2 {
            return Err(PyValueError::new_err(format!(
                "BibleVersionDecorations['{key}'] must be a (prefix, suffix) pair"
            )));
        }
        decorations.insert(key, [pair[0].clone(), pair[1].clone()]);
    }

    let names_dict = state.getattr("BibleNames")?;
    let mut bible_names = std::collections::HashMap::new();
    for key in names_dict.try_iter()? {
        let key: String = key?.extract()?;
        bible_names.insert(key.clone(), names_dict.get_item(&key)?.extract()?);
    }

    // Precompute makeSafeString for each version like the Python code does per call
    let bos_globals = py.import("BibleOrgSys.BibleOrgSysGlobals")?;
    let mut safe_names = std::collections::HashMap::new();
    for va in &bible_versions {
        let safe = bos_globals.call_method1("makeSafeString", (va,))?;
        safe_names.insert(va.clone(), safe.extract::<String>()?);
    }

    // preloadedBibles: discovery flags plus book membership sets
    let preloaded = state.getattr("preloadedBibles")?;
    let mut have_section_headings = std::collections::HashSet::new();
    let mut version_books = std::collections::HashMap::new();
    for key in preloaded.try_iter()? {
        let key: String = key?.extract()?;
        let bible = preloaded.get_item(&key)?;
        let has_sections = match bible.getattr("discoveryResults") {
            Ok(dr) => match dr.get_item("ALL") {
                Ok(dr_all) => dr_all
                    .get_item("haveSectionHeadings")
                    .and_then(|v| v.is_truthy())
                    .unwrap_or(false),
                Err(_) => false,
            },
            Err(_) => false,
        };
        if has_sections {
            have_section_headings.insert(key.clone());
        }
        let mut books = std::collections::HashSet::new();
        for bos_book_code in &all_bos_book_codes {
            if bible.call_method1("__contains__", (bos_book_code,))?.is_truthy()? {
                books.insert(bos_book_code.clone());
            }
        }
        version_books.insert(key, books);
    }

    Ok(page_chrome::PageChromeConfig {
        test_mode_flag,
        site_name,
        bible_versions,
        versions_without_their_own_pages,
        test_versions_only,
        safe_names,
        decorations,
        bible_names,
        all_bos_book_codes,
        have_section_headings,
        version_books,
    })
}

/// Snapshot of the State data needed to build page tops, extracted once so
/// that generating each page needs no Python interaction.
#[pyclass]
#[pyo3(name = "PageChromeConfig")]
struct PyPageChromeConfig {
    inner: page_chrome::PageChromeConfig,
}

#[pymethods]
impl PyPageChromeConfig {
    #[new]
    fn new(state: &Bound<'_, PyAny>) -> PyResult<Self> {
        Ok(Self {
            inner: page_chrome_config_from_state(state)?,
        })
    }
}

/// Create the very top part of an HTML page (Rust port of html.makeTop).
///
/// The config should be created once per State via
/// `openbibledata_rust.PageChromeConfig(state)` and reused across pages.
#[pyfunction]
#[pyo3(
    name = "make_top",
    signature = (config, level, pageType, versionAbbreviation=None, versionSpecificFileOrFolderName=None)
)]
#[allow(non_snake_case)]
fn make_top_py(
    config: &PyPageChromeConfig,
    level: usize,
    pageType: &str,
    versionAbbreviation: Option<&str>,
    versionSpecificFileOrFolderName: Option<&str>,
) -> PyResult<String> {
    page_chrome::make_top_core(
        &config.inner,
        level,
        versionAbbreviation,
        pageType,
        versionSpecificFileOrFolderName,
    )
    .map_err(|e| PyValueError::new_err(format!("make_top failed: {e}")))
}

/// Create the "ByDocument/BySection" navigation bar (Rust port of
/// html.makeViewNavListParagraph). Can return an empty string.
#[pyfunction]
#[pyo3(
    name = "make_view_nav_list",
    signature = (config, level, pageType, versionAbbreviation=None)
)]
#[allow(non_snake_case)]
fn make_view_nav_list_py(
    config: &PyPageChromeConfig,
    level: usize,
    pageType: &str,
    versionAbbreviation: Option<&str>,
) -> String {
    page_chrome::view_nav_list_core(&config.inner, level, versionAbbreviation, pageType)
}

// ── OETHandlers PyO3 wrappers ───────────────────────────────────────────────

const NARROW_NON_BREAK_SPACE: &str = "\u{202F}";

/// Turn a core `Err(String)` into the closest matching Python exception,
/// based on the message prefix conventions used by the oet_handlers cores.
fn err_to_pyerr(message: String) -> PyErr {
    if let Some(rest) = message.strip_prefix("AssertionError:") {
        PyAssertionError::new_err(rest.trim_start().to_string())
    } else if let Some(rest) = message.strip_prefix("IndexError:") {
        PyIndexError::new_err(rest.trim_start().to_string())
    } else if let Some(rest) = message.strip_prefix("KeyError:") {
        PyKeyError::new_err(rest.trim_start().to_string())
    } else if let Some(rest) = message.strip_prefix("ValueError:") {
        PyValueError::new_err(rest.trim_start().to_string())
    } else if let Some(rest) = message.strip_prefix("UnboundLocalError:") {
        PyUnboundLocalError::new_err(rest.trim_start().to_string())
    } else {
        PyValueError::new_err(message)
    }
}

/// Our customised version of tidyBBB (Rust port of OETHandlers.getOETTidyBBB).
#[pyfunction]
#[pyo3(
    name = "getOETTidyBBB",
    signature = (BBB, titleCase=false, allowFourChars=true, insertChar=NARROW_NON_BREAK_SPACE, addNotes=false)
)]
#[allow(non_snake_case)]
fn get_oet_tidy_bbb_py(
    BBB: &str,
    titleCase: bool,
    allowFourChars: bool,
    insertChar: Option<&str>,
    addNotes: bool,
) -> String {
    // The binding maps None to '' before calling the pure function
    let new_bbb =
        bos_books_codes::tidy_bbb(BBB, titleCase, allowFourChars, insertChar.unwrap_or(""));
    oet_handlers::apply_oet_tidy_renames(&new_bbb, insertChar.unwrap_or(""), addNotes)
}

/// Handle our different spelling of well-known book names
/// (Rust port of OETHandlers.getOETBookName).
#[pyfunction]
#[pyo3(name = "getOETBookName", signature = (BBB))]
#[allow(non_snake_case)]
fn get_oet_book_name_py(BBB: &str) -> PyResult<String> {
    oet_handlers::oet_book_name(BBB)
        .ok_or_else(|| PyValueError::new_err(format!("Unknown BBB book code '{BBB}'")))
}

/// Look up a BBB from an English/OET bookname; can return None
/// (Rust port of OETHandlers.getBBBFromOETBookName).
#[pyfunction]
#[pyo3(name = "getBBBFromOETBookName", signature = (originalBooknameText, _location=""))]
#[allow(non_snake_case)]
fn get_bbb_from_oet_book_name_py(
    py: Python<'_>,
    originalBooknameText: &str,
    _location: &str,
) -> PyResult<Option<&'static str>> {
    let lookup = oet_handlers::get_bbb_from_oet_book_name_core(originalBooknameText);
    // Python logs a diagnostic whenever no VALID book code was produced
    // ("not resultBBB or not is_valid_bos_book_code(resultBBB)")
    let needs_diagnostic = matches!(
        lookup,
        oet_handlers::BbbLookup::InvalidFallback(_) | oet_handlers::BbbLookup::NotFound
    );
    if !needs_diagnostic {
        return Ok(lookup.code());
    }
    let uppered: String = originalBooknameText
        .chars()
        .filter(|&c| c != ' ' && c != '\u{202F}' && c != '.')
        .flat_map(char::to_uppercase)
        .collect();
    // Faithful crash: Python's f-string indexes upperedBooknameText[0]
    if uppered.is_empty() {
        return Err(PyIndexError::new_err("string index out of range"));
    }
    // dPrint('Info'/'Normal', …) prints when verbosityLevel >= requested
    // ('Info'=3, 'Normal'=2); the site build runs at the default level 2.
    let requested_level = if uppered.as_bytes()[0].is_ascii_digit() { 3 } else { 2 };
    let globals = py.import("BibleOrgSys.BibleOrgSysGlobals")?;
    let verbosity_level: i64 = globals.getattr("verbosityLevel")?.extract()?;
    if verbosity_level >= requested_level {
        py.import("builtins")?
            .call_method1(
                "print",
                (format!(
                    "getBBBFromOETBookName can't get valid BBB from upperedBooknameText='{uppered}' where='{_location}': {} from originalBooknameText='{originalBooknameText}'",
                    match lookup.code() {
                        Some(code) => format!("resultBBB='{code}'"),
                        None => "resultBBB=None".to_string(),
                    },
                ),),
            )?;
    }
    Ok(lookup.code())
}

/// Take an OT word-table row number and make it into a wordpage filename
/// like `KI2c1v3w4.htm` (Rust port of OETHandlers.getHebrewWordpageFilename).
#[pyfunction]
#[pyo3(name = "getHebrewWordpageFilename", signature = (wordTableRowNum, state))]
#[allow(non_snake_case)]
fn get_hebrew_wordpage_filename_py<'py>(
    wordTableRowNum: i64,
    state: &Bound<'py, PyAny>,
) -> PyResult<String> {
    let row_object = state
        .getattr("OETRefData")?
        .get_item("word_tables")?
        .get_item("OET-LV_OT_word_table.tsv")?
        .get_item(wordTableRowNum)?; // IndexError propagates (incl. negatives)
    let row: String = row_object.extract()?;
    oet_handlers::hebrew_wordpage_filename_from_row(&row).map_err(err_to_pyerr)
}

/// Take an NT word-table row number and make it into a wordpage filename
/// like `JN2c1v3w4.htm` (Rust port of OETHandlers.getGreekWordpageFilename).
#[pyfunction]
#[pyo3(name = "getGreekWordpageFilename", signature = (rowNum, state))]
#[allow(non_snake_case)]
fn get_greek_wordpage_filename_py<'py>(
    rowNum: i64,
    state: &Bound<'py, PyAny>,
) -> PyResult<String> {
    let row_object = state
        .getattr("OETRefData")?
        .get_item("word_tables")?
        .get_item("OET-LV_NT_word_table.tsv")?
        .get_item(rowNum)?; // IndexError propagates (incl. negatives)
    let row: String = row_object.extract()?;
    oet_handlers::greek_wordpage_filename_from_row(&row).map_err(err_to_pyerr)
}

/// Build a new `InternalBibleEntry(marker, originalMarker, text, '', None, '')`
/// via the Python class (same class as the entries we iterate).
fn make_new_entry<'py>(
    py: Python<'py>,
    marker: &str,
    original_marker: &str,
    text: &str,
) -> PyResult<Bound<'py, PyAny>> {
    py.import("bible_organisational_system")?
        .getattr("InternalBibleEntry")?
        .call1((marker, original_marker, text, "", py.None(), ""))
}

/// Get `entry.getOriginalText()` as an owned string ('' for None).
fn entry_original_text(entry: &Bound<'_, PyAny>) -> PyResult<String> {
    entry.call_method0("getOriginalText")?.extract()
}

/// Shared second half of livenOETWordLinks / livenOETCompatibleBereanWordLinks:
/// replace the `§…§ … ►NNNN◄` placeholders with real hrefs, transliterated
/// titles, and colourisation classes.
///
/// Returns the new InternalBibleEntryList (or raises AssertionError
/// "We want to stop here" when nothing could be processed).
#[allow(non_snake_case)]
fn postprocess_word_link_entries<'py>(
    py: Python<'py>,
    revised_list: &Bound<'py, PyAny>,
    bible_abbreviation: &str,
    BBB: &str,
    level: usize,
    word_file_name: &str,
    state: &Bound<'py, PyAny>,
    colourise_word_classes: bool,
) -> PyResult<Bound<'py, PyAny>> {
    let is_nt = bos_books_codes::is_new_testament_nr(BBB);
    let table = state
        .getattr("OETRefData")?
        .get_item("word_tables")?
        .get_item(word_file_name)?;
    let unicodedata = py.import("unicodedata")?;

    let get_row = |number: i64| -> Result<String, String> {
        table
            .get_item(number)
            .map_err(|e| e.to_string())?
            .extract::<String>()
            .map_err(|e| e.to_string())
    };
    let nfc_normalise = |s: &str| -> String {
        unicodedata
            .call_method1("normalize", ("NFC", s))
            .and_then(|r| r.extract())
            .unwrap_or_else(|_| s.to_string())
    };

    let mut updated_entries: Vec<Bound<'py, PyAny>> = Vec::with_capacity(16);
    for entry in revised_list.try_iter()? {
        let entry = entry?;
        let original_text_owned = entry_original_text(&entry)?;
        if !original_text_owned.contains('§') {
            updated_entries.push(entry);
            continue;
        }
        match oet_handlers::postprocess_word_link_titles(
            &original_text_owned,
            level,
            is_nt,
            &get_row,
            &nfc_normalise,
            colourise_word_classes,
        ) {
            Ok(oet_handlers::TitlePostprocess::Updated { text, transliterations_added, colourisations_added })
                if transliterations_added > 0 || colourisations_added > 0 =>
            {
                log_message(
                    py,
                    "info",
                    &format!(
                        "Added {transliterations_added} {bible_abbreviation} {BBB} transliterations and {colourisations_added} colourisations to titles."
                    ),
                );
                updated_entries.push(make_new_entry(
                    py,
                    &entry.call_method0("getMarker")?.extract::<String>()?,
                    &entry.call_method0("getOriginalMarker")?.extract::<String>()?,
                    &text,
                )?);
            }
            Ok(_) => {
                // No title matched at all (or nothing changed)
                log_message(
                    py,
                    "critical",
                    &format!(
                        "ESFMBible.livenESFMWordLinks unable to find wordlink title in '{original_text_owned}'"
                    ),
                );
                updated_entries.push(entry);
                return Err(PyAssertionError::new_err("We want to stop here"));
            }
            Err(message) => return Err(err_to_pyerr(message)),
        }
    }

    let list_module = py.import("builtins")?;
    let python_list = list_module.call_method1("list", (updated_entries,))?;
    py.import("bible_organisational_system")?
        .getattr("InternalBibleEntryList")?
        .call1((python_list,))
}

/// Livens ESFM wordlinks in the OET versions
///     (Rust port of OETHandlers.livenOETWordLinks).
#[pyfunction]
#[pyo3(
    name = "livenOETWordLinks",
    signature = (level, bibleObject, refTuple, givenEntryList, state, colouriseWordClasses=true)
)]
#[allow(non_snake_case)]
fn liven_oet_word_links_py<'py>(
    py: Python<'py>,
    level: usize,
    bibleObject: &Bound<'py, PyAny>,
    refTuple: &Bound<'py, PyAny>,
    givenEntryList: &Bound<'py, PyAny>,
    state: &Bound<'py, PyAny>,
    colouriseWordClasses: bool,
) -> PyResult<Bound<'py, PyAny>> {
    if !(1..=3).contains(&level) {
        return Err(PyAssertionError::new_err(format!("level={level}")));
    }
    let word_tables_count: usize = bibleObject
        .getattr("ESFMWordTables")?
        .len()?;
    if word_tables_count != 2 {
        return Err(PyAssertionError::new_err(format!(
            "len(bibleObject.ESFMWordTables)={word_tables_count}"
        )));
    }
    if !refTuple.is_instance_of::<pyo3::types::PyTuple>() {
        return Err(PyTypeError::new_err("refTuple must be a tuple"));
    }
    let BBB: String = refTuple.get_item(0)?.extract()?;

    let abbreviation: String = bibleObject.getattr("abbreviation")?.extract()?;
    let test_mode_flag: bool = state
        .getattr("TEST_MODE_FLAG")
        .and_then(|v| v.extract())
        .unwrap_or(false);

    let mut preprocessed_entries: Vec<Bound<'py, PyAny>> = Vec::with_capacity(16);
    let mut preprocessed_list_object: Option<Bound<'py, PyAny>> = None;
    if test_mode_flag
        && abbreviation == "OET-RV"
        && (bos_books_codes::is_old_testament_nr(&BBB)
            || bos_books_codes::is_new_testament_nr(&BBB))
    {
        // Highlight all OET-RV words that DON'T have a word link
        for entry in givenEntryList.try_iter()? {
            let entry = entry?;
            let marker: String = entry.call_method0("getMarker")?.extract()?;
            let original_text = entry_original_text(&entry)?;
            let opening_count = original_text.matches("\\add ").count();
            let closing_count = original_text.matches("\\add*").count();
            if opening_count != closing_count {
                return Err(PyAssertionError::new_err(format!(
                    "Bad add open/close counts in OET {abbreviation} {BBB} {marker} line: {opening_count} != {closing_count}"
                )));
            }
            if !original_text.is_empty() && marker == "v~" {
                if original_text.contains("\\nd \\nd ") {
                    return Err(PyAssertionError::new_err(format!(
                        "Double nd in {abbreviation} {BBB} {marker:?} {original_text:?}"
                    )));
                }
                let ref_elements: Vec<String> = refTuple
                    .try_iter()?
                    .map(|item| item.and_then(|i| i.extract()))
                    .collect::<PyResult<Vec<String>>>()?;
                let ref_strings: Vec<&str> = ref_elements.iter().map(String::as_str).collect();
                match oet_handlers::preprocess_oet_rv_entry(
                    &marker,
                    &original_text,
                    &abbreviation,
                    &ref_strings,
                ) {
                    Ok(Some(new_text)) => {
                        preprocessed_entries.push(make_new_entry(
                            py,
                            &marker,
                            &entry.call_method0("getOriginalMarker")?.extract::<String>()?,
                            &new_text,
                        )?);
                        continue;
                    }
                    Ok(None) => {}
                    Err(message) => return Err(err_to_pyerr(message)),
                }
            }
            preprocessed_entries.push(entry);
        }
        let builtins = py.import("builtins")?;
        preprocessed_list_object = Some(
            py.import("bible_organisational_system")?
                .getattr("InternalBibleEntryList")?
                .call1((builtins.call_method1("list", (preprocessed_entries,))?,))?,
        );
    }

    // Liven the word links using the BibleOrgSys method
    //     We use unusual word pairs in both templates so that we can easily
    //     find them again in the returned InternalBibleEntryList
    let kwargs = pyo3::types::PyDict::new(py);
    kwargs.set_item("linkTemplate", format!("►{{n}}◄"))?;
    kwargs.set_item("titleTemplate", "§«OrigWord»§")?;
    let verse_list = preprocessed_list_object
        .as_ref()
        .unwrap_or(givenEntryList);
    let revised_result =
        bibleObject.call_method("livenESFMWordLinks", (&BBB, verse_list), Some(&kwargs))?;
    let revised_list = revised_result.get_item(0)?;

    // Post-liven sanity checks
    for revised_entry in revised_list.try_iter()? {
        let revised_entry = revised_entry?;
        let original_text = entry_original_text(&revised_entry)?;
        if !original_text.is_empty() {
            if original_text.contains("\\nd \\nd ") {
                return Err(PyAssertionError::new_err("'\\nd \\nd ' found in text"));
            }
            let opening_count = original_text.matches("\\add ").count();
            let closing_count = original_text.matches("\\add*").count();
            if opening_count != closing_count {
                return Err(PyAssertionError::new_err(format!(
                    "Bad add open/close counts in OET {abbreviation} {BBB} line: {opening_count} != {closing_count} {original_text:?}"
                )));
            }
        }
    }

    let is_nt = bos_books_codes::is_new_testament_nr(&BBB);
    let word_file_name = if is_nt {
        "OET-LV_NT_word_table.tsv"
    } else {
        "OET-LV_OT_word_table.tsv"
    };
    postprocess_word_link_entries(
        py, &revised_list, &abbreviation, &BBB, level, word_file_name, state, colouriseWordClasses,
    )
}

/// Livens wordlinks in Berean-compatible versions (Rust port of
/// OETHandlers.livenOETCompatibleBereanWordLinks).
#[pyfunction]
#[pyo3(
    name = "livenOETCompatibleBereanWordLinks",
    signature = (level, bibleObject, BBB, givenEntryList, state, colouriseWordClasses=true)
)]
#[allow(non_snake_case)]
fn liven_oet_compatible_berean_word_links_py<'py>(
    py: Python<'py>,
    level: usize,
    bibleObject: &Bound<'py, PyAny>,
    BBB: &str,
    givenEntryList: &Bound<'py, PyAny>,
    state: &Bound<'py, PyAny>,
    colouriseWordClasses: bool,
) -> PyResult<Bound<'py, PyAny>> {
    if !(1..=3).contains(&level) {
        return Err(PyAssertionError::new_err(format!("level={level}")));
    }
    let esfm_word_tables = bibleObject.getattr("ESFMWordTables")?;
    let word_tables_count: usize = esfm_word_tables.len()?;
    if word_tables_count != 2 {
        return Err(PyAssertionError::new_err(format!(
            "len(bibleObject.ESFMWordTables)={word_tables_count}"
        )));
    }
    let abbreviation: String = bibleObject.getattr("abbreviation")?.extract()?;

    // Pre-liven double-nd check over the GIVEN entries
    for entry in givenEntryList.try_iter()? {
        let entry = entry?;
        let original_text = entry_original_text(&entry)?;
        if !original_text.is_empty() && original_text.contains("\\nd \\nd ") {
            return Err(PyAssertionError::new_err(format!(
                "Double nd in {abbreviation} {BBB} {original_text:?}"
            )));
        }
    }

    // Determine which word table to use (faithful quirk: any other book
    // leaves the variable unbound -- UnboundLocalError)
    let is_ot = bos_books_codes::is_old_testament_nr(BBB);
    let is_nt = bos_books_codes::is_new_testament_nr(BBB);
    let word_file_name = if is_ot {
        "OET-LV_OT_word_table.tsv"
    } else if is_nt {
        "OET-LV_NT_word_table.tsv"
    } else {
        return Err(PyUnboundLocalError::new_err(
            "local variable 'wordFileName' referenced before assignment",
        ));
    };
    let word_table = esfm_word_tables.get_item(word_file_name)?;
    if word_table.is_none() {
        bibleObject.call_method1("loadESFMWordFile", (word_file_name,))?;
    }
    let column_names: Vec<String> = bibleObject
        .getattr("ESFMColumnNameList")?
        .get_item(word_file_name)?
        .extract()?;
    let table_for_rows = bibleObject
        .getattr("ESFMWordTables")?
        .get_item(word_file_name)?;

    let get_row = |number: i64| -> Result<String, String> {
        table_for_rows
            .get_item(number)
            .map_err(|e| e.to_string())?
            .extract::<String>()
            .map_err(|e| e.to_string())
    };

    // Liven the word links using our port of the BibleOrgSys inner function
    //     We use unusual word pairs in both templates so that we can easily
    //     find them again in the returned InternalBibleEntryList
    let mut revised_entries: Vec<Bound<'py, PyAny>> = Vec::with_capacity(16);
    for entry in givenEntryList.try_iter()? {
        let entry = entry?;
        let marker: String = entry.call_method0("getMarker")?.extract()?;
        let original_marker: String = entry.call_method0("getOriginalMarker")?.extract()?;
        let original_text = entry_original_text(&entry)?;
        if !original_text.contains('¦') {
            revised_entries.push(entry);
            continue;
        }
        match oet_handlers::liven_berean_text(
            &original_text,
            BBB,
            "►{n}◄",
            Some("§«OrigWord»§"),
            &column_names,
            &get_row,
        ) {
            Ok(Some(new_text)) => {
                revised_entries.push(make_new_entry(py, &marker, &original_marker, &new_text)?);
            }
            Ok(None) => {
                log_message(
                    py,
                    "critical",
                    &format!(
                        "ESFMBible.livenESFMWordLinks unable to find wordlink in '{original_text}'"
                    ),
                );
                revised_entries.push(entry);
            }
            Err(message) => return Err(err_to_pyerr(message)),
        }
    }
    let builtins = py.import("builtins")?;
    let revised_list = py
        .import("bible_organisational_system")?
        .getattr("InternalBibleEntryList")?
        .call1((builtins.call_method1("list", (revised_entries,))?,))?;

    // NOTE (faithful): the original checks the GIVEN list here, not the
    // revised one -- preserved as-is.
    for given_entry in givenEntryList.try_iter()? {
        let original_text = entry_original_text(&given_entry?)?;
        if !original_text.is_empty() && original_text.contains("\\nd \\nd ") {
            return Err(PyAssertionError::new_err("'\\nd \\nd ' found in text"));
        }
    }

    postprocess_word_link_entries(
        py, &revised_list, &abbreviation, BBB, level, word_file_name, state, colouriseWordClasses,
    )
}

/// Given an original language quote, find the matching OET-LV English words
/// and return them as html (Rust port of OETHandlers.findOLQuoteInLV).
#[pyfunction]
#[pyo3(
    name = "findOLQuoteInLV",
    signature = (level, BBB, C, V, occurrenceNumber, originalLanguageQuote, state)
)]
#[allow(non_snake_case)]
fn find_ol_quote_in_lv_py<'py>(
    py: Python<'py>,
    level: usize,
    BBB: &str,
    C: &str,
    V: &str,
    occurrenceNumber: i64,
    originalLanguageQuote: &str,
    state: &Bound<'py, PyAny>,
) -> PyResult<String> {
    let _ = level;
    let reference = format!("{BBB}_{C}:{V}");
    let is_nt = bos_books_codes::is_new_testament_nr(BBB);
    let word_file_name = if is_nt {
        "OET-LV_NT_word_table.tsv"
    } else {
        "OET-LV_OT_word_table.tsv"
    };

    let context_data = match state
        .getattr("preloadedBibles")?
        .get_item("OET-LV")?
        .call_method1("getContextVerseData", ((BBB, C, V),))
        .and_then(|data| data.get_item(0)) // TypeError if None is returned
    {
        Ok(data) => data,
        Err(error)
            if error
                .get_type(py)
                .name()
                .is_ok_and(|name| name == "KeyError" || name == "TypeError") =>
        {
            let books_to_load = state.getattr("booksToLoad")?.get_item("OET-LV")?;
            let has_book = books_to_load.call_method1("__contains__", (BBB,))?.is_truthy()?;
            log_message(
                py,
                if has_book { "error" } else { "warning" },
                &format!("findOLQuoteInLV: OET-LV has no text for {reference}"),
            );
            return Ok(String::new());
        }
        Err(error) => return Err(error),
    };
    // Collect the texts we might find a starting word number in
    let mut lv_texts: Vec<String> = Vec::with_capacity(8);
    for entry in context_data.try_iter()? {
        lv_texts.push(entry_original_text(&entry?)?);
    }

    let word_table = state
        .getattr("OETRefData")?
        .get_item("word_tables")?
        .get_item(word_file_name)?;
    let table_len: usize = word_table.len()?;
    // Python only looks up word_table_indexes when a starting word number was
    // found; KeyError propagates to the caller in that case.
    let indexes_root = state
        .getattr("OETRefData")?
        .get_item("word_table_indexes")?
        .get_item(word_file_name)?;
    let get_indexes = |ref_: &str| -> Result<(i64, i64), String> {
        let pair = indexes_root
            .get_item(ref_)
            .map_err(|error: PyErr| format!("KeyError: {ref_} ({error})"))?;
        let first: i64 = pair
            .get_item(0)
            .map_err(|e: PyErr| e.to_string())?
            .extract()
            .map_err(|e: PyErr| e.to_string())?;
        let last: i64 = pair
            .get_item(1)
            .map_err(|e: PyErr| e.to_string())?
            .extract()
            .map_err(|e: PyErr| e.to_string())?;
        Ok((first, last))
    };

    let get_row = |number: i64| -> Result<String, String> {
        word_table
            .get_item(number)
            .map_err(|e| e.to_string())?
            .extract::<String>()
            .map_err(|e| e.to_string())
    };
    let log = |log_level: &str, message: &str| log_message(py, log_level, message);

    let outcome = oet_handlers::find_ol_quote_in_lv_core(
        &reference,
        &lv_texts,
        table_len,
        &get_row,
        &get_indexes,
        occurrenceNumber,
        originalLanguageQuote,
        is_nt,
        &log,
    )
    .map_err(err_to_pyerr)?;

    match outcome {
        oet_handlers::OlQuoteOutcome::Html(assembled_html) => {
            // assert checkHtml( 'LVQuote', assembledHtml, segmentOnly=True )
            // NOTE: this resolves to the LOCAL createPages/html.py module
            // (already cached under the 'html' sys.modules key by earlier
            // imports in every caller).
            let check_html_kwargs = pyo3::types::PyDict::new(py);
            check_html_kwargs.set_item("segmentOnly", true)?;
            let check_html_result = py
                .import("html")?
                .call_method(
                    "checkHtml",
                    ("LVQuote", assembled_html.as_str()),
                    Some(&check_html_kwargs),
                )?
                .is_truthy()?;
            if !check_html_result {
                return Err(PyAssertionError::new_err(format!(
                    "checkHtml failed for LVQuote {reference}: '{assembled_html}'"
                )));
            }
            Ok(assembled_html)
        }
        oet_handlers::OlQuoteOutcome::NoStartingWord => {
            log_message(
                py,
                "error",
                &format!(
                    "findOLQuoteInLV: OET-LV can't find a starting word number for {reference}"
                ),
            );
            Ok(String::new())
        }
    }
}

#[pymodule]
fn openbibledata_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(liven_introduction_links_py, m)?)?;
    m.add_function(wrap_pyfunction!(to_roman_numerals_py, m)?)?;
    m.add_function(wrap_pyfunction!(liven_iors_py, m)?)?;
    m.add_function(wrap_pyfunction!(convert_usfm_character_formatting_py, m)?)?;
    m.add_function(wrap_pyfunction!(process_cross_references_py, m)?)?;
    m.add_function(wrap_pyfunction!(process_footnotes_py, m)?)?;
    m.add_function(wrap_pyfunction!(convert_verse_entry_list_to_html_py, m)?)?;
    m.add_function(wrap_pyfunction!(find_section_number_py, m)?)?;
    m.add_function(wrap_pyfunction!(make_top_py, m)?)?;
    m.add_function(wrap_pyfunction!(make_view_nav_list_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_oet_tidy_bbb_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_oet_book_name_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_bbb_from_oet_book_name_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_hebrew_wordpage_filename_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_greek_wordpage_filename_py, m)?)?;
    m.add_function(wrap_pyfunction!(liven_oet_word_links_py, m)?)?;
    m.add_function(wrap_pyfunction!(liven_oet_compatible_berean_word_links_py, m)?)?;
    m.add_function(wrap_pyfunction!(find_ol_quote_in_lv_py, m)?)?;
    m.add_function(wrap_pyfunction!(html_validation::check_html_py, m)?)?;
    m.add_class::<PyPageChromeConfig>()?;
    Ok(())
}

// Internal Rust macro for displaying user messages based on verbosity level
#[macro_export]
macro_rules! verbosity_println {
    ($level:expr, $($arg:tt)*) => {
        if bos_internals::get_verbosity_level() >= $level {
            println!($($arg)*);
        }
    };
}
