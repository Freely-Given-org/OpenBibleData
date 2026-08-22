//! PyO3 module exposing OpenBibleData Rust extensions.

use pyo3::exceptions::{PyAssertionError, PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyAny;

pub mod constants;
pub mod intro_links;
pub mod ior_links;
pub mod oet_books;
pub mod page_chrome;
pub mod roman_numerals;
pub mod character_formatting;
pub mod xref_links;
pub mod verse_to_html;
pub mod verse_entry_list;

pub use intro_links::{liven_introduction_links_core, IntroLinkError};
pub use ior_links::{liven_iors_core, IORLinkError};
pub use roman_numerals::to_roman_numerals;
pub use character_formatting::{convert_usfm_character_formatting, CharacterFormattingResult};

/// Build a section-number lookup callback that calls back into Python's
/// `createSectionPages.findSectionNumber` via the optional State object.
///
/// All PyO3 wrappers that need live section numbers use this shared helper;
/// the actual linking logic lives in the pure-Rust `*_core` functions.
fn py_find_section_fn<'s>(
    state: Option<&'s Bound<'_, PyAny>>,
) -> impl Fn(&str, &str, &str, &str) -> Option<usize> + Clone + 's {
    move |v_abbr: &str, bbb: &str, c: &str, v: &str| -> Option<usize> {
        if let Some(state_obj) = state {
            let py_env = state_obj.py();
            if let Ok(module) = py_env.import("createSectionPages") {
                if let Ok(func) = module.getattr("findSectionNumber") {
                    if let Ok(res) = func.call1((v_abbr, bbb, c, v, state_obj)) {
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
/// `'ALL' in state.booksToLoad[vAbbr] or bbb in state.booksToLoad[vAbbr]`).
///
/// Returns true when no State is supplied (e.g., from test programs), so that
/// behaviour stays permissive there.
fn py_is_book_available_fn<'s>(
    state: Option<&'s Bound<'_, PyAny>>,
) -> impl Fn(&str, &str) -> bool + Clone + 's {
    move |v_abbr: &str, bbb: &str| -> bool {
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
                        if entry == "ALL" || entry == bbb {
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
    let our_bbb: String = if let Ok(tuple) = ref_tuple.extract::<Vec<String>>() {
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
        &our_bbb,
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
    signature = (version_abbreviation, our_bbb, segment_type, ior_html, is_single_chapter, state=None)
)]
fn liven_iors_py<'py>(
    _py: Python<'py>,
    version_abbreviation: &str,
    our_bbb: &str,
    segment_type: &str,
    ior_html: &str,
    is_single_chapter: bool,
    state: Option<&Bound<'py, PyAny>>,
) -> PyResult<String> {
    let find_section_fn = py_find_section_fn(state);

    match liven_iors_core(version_abbreviation, our_bbb, segment_type, ior_html, is_single_chapter, find_section_fn) {
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
    signature = (version_abbrev, bbb, segment_type, usfm_field, basic_only, expanded_char_markers, booklist_nt27, is_net_version, level=0)
)]
fn convert_usfm_character_formatting_py(
    py: Python,
    version_abbrev: &str,
    bbb: &str,
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
        bbb,
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

    // Split up the reference tuple: (BBB,), (BBB,C), or (BBB,C,V)
    let bbb = refTuple.first().map(String::as_str)
        .ok_or_else(|| PyValueError::new_err("Empty refTuple"))?;
    let c = refTuple.get(1).map(String::as_str);
    let v = refTuple.get(2).map(String::as_str);

    // bos_books_codes is linked in directly, so we don't need this passed as a parameter
    let is_single_chapter_book = bos_books_codes::is_single_chapter_book(bbb);

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

    // Build find_section_fn callback
    let find_section_fn = py_find_section_fn(state);
    let is_book_available = py_is_book_available_fn(state);

    let no_op_obi = |_l: usize, _st: &str, _b: &str, _c: &str, _v: &str| -> Option<String> { None };
    let no_op_check = |_w: &str, _h: &str| -> bool { true };

    let context_refs: Vec<&str> = context_list.iter().map(|s| s.as_str()).collect();

    let result = verse_entry_list::convert_verse_entry_list_to_html_standalone(
        level,
        versionAbbreviation,
        bbb,
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
#[pyo3(signature = (html, version_abbreviation, bbb, c, segment_type, path_prefix, state=None))]
fn process_cross_references_py<'py>(
    _py: Python<'py>,
    html: &str,
    version_abbreviation: &str,
    bbb: &str,
    c: Option<&str>,
    segment_type: &str,
    path_prefix: &str,
    state: Option<&Bound<'py, PyAny>>,
) -> PyResult<(String, String)> {
    let c = c.unwrap_or("");
    let find_section_fn = py_find_section_fn(state);

    match verse_to_html::process_cross_references_core(
        html, version_abbreviation, bbb, c, segment_type, path_prefix, find_section_fn,
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
#[pyo3(signature = (html, version_abbreviation, bbb, c, segment_type, path_prefix, max_footnote_chars, state=None))]
fn process_footnotes_py<'py>(
    _py: Python<'py>,
    html: &str,
    version_abbreviation: &str,
    bbb: &str,
    c: Option<&str>,
    segment_type: &str,
    path_prefix: &str,
    max_footnote_chars: usize,
    state: Option<&Bound<'py, PyAny>>,
) -> PyResult<(String, String)> {
    let c = c.unwrap_or("");
    let find_section_fn = py_find_section_fn(state);

    match verse_to_html::process_footnotes_core(
        html, version_abbreviation, bbb, c, segment_type, path_prefix, max_footnote_chars, find_section_fn,
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

    let all_bbbs: Vec<String> = state
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
        for bbb in &all_bbbs {
            if bible.call_method1("__contains__", (bbb,))?.is_truthy()? {
                books.insert(bbb.clone());
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
        all_bbbs,
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

#[pymodule]
fn openbibledata_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(liven_introduction_links_py, m)?)?;
    m.add_function(wrap_pyfunction!(to_roman_numerals_py, m)?)?;
    m.add_function(wrap_pyfunction!(liven_iors_py, m)?)?;
    m.add_function(wrap_pyfunction!(convert_usfm_character_formatting_py, m)?)?;
    m.add_function(wrap_pyfunction!(process_cross_references_py, m)?)?;
    m.add_function(wrap_pyfunction!(process_footnotes_py, m)?)?;
    m.add_function(wrap_pyfunction!(convert_verse_entry_list_to_html_py, m)?)?;
    m.add_function(wrap_pyfunction!(make_top_py, m)?)?;
    m.add_function(wrap_pyfunction!(make_view_nav_list_py, m)?)?;
    m.add_class::<PyPageChromeConfig>()?;
    Ok(())
}
