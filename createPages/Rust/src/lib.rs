//! PyO3 module exposing OpenBibleData Rust extensions.

use pyo3::exceptions::{PyAssertionError, PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict};

pub mod constants;
pub mod intro_links;
pub mod ior_links;
pub mod oet_books;
pub mod roman_numerals;
pub mod character_formatting;
pub mod xref_links;
pub mod verse_to_html;
pub mod verse_entry_list;

pub use intro_links::{liven_introduction_links_core, IntroLinkError};
pub use ior_links::{liven_iors_core, IORLinkError};
pub use oet_books::get_bbb_from_oet_book_name;
pub use roman_numerals::to_roman_numerals;
pub use character_formatting::{convert_usfm_character_formatting, CharacterFormattingResult};
pub use xref_links::{liven_xref_field_core, XRefError};

/// Convert an original book name to its 3-character BOS Book Code (BBB).
#[pyfunction]
#[pyo3(name = "get_bbb_from_oet_book_name")]
fn get_bbb_from_oet_book_name_py(book_name: &str) -> PyResult<Option<&'static str>> {
    Ok(get_bbb_from_oet_book_name(book_name))
}

/// CamelCase alias for get_bbb_from_oet_book_name.
#[pyfunction]
#[pyo3(name = "getBBBFromOETBookName")]
fn get_bbb_from_oet_book_name_camel_py(book_name: &str) -> PyResult<Option<&'static str>> {
    Ok(get_bbb_from_oet_book_name(book_name))
}

/// Liven introduction links in HTML text using Rust.
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

    let find_section_fn = |v_abbr: &str, bbb: &str, c: &str, v: &str| -> Option<usize> {
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
    };

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

/// CamelCase alias for liven_introduction_links.
#[pyfunction]
#[pyo3(
    name = "livenIntroductionLinks",
    signature = (version_abbreviation, ref_tuple, segment_type, intro_html, state=None)
)]
fn liven_introduction_links_camel_py<'py>(
    py: Python<'py>,
    version_abbreviation: &str,
    ref_tuple: &Bound<'py, PyAny>,
    segment_type: &str,
    intro_html: &str,
    state: Option<&Bound<'py, PyAny>>,
) -> PyResult<String> {
    liven_introduction_links_py(py, version_abbreviation, ref_tuple, segment_type, intro_html, state)
}

/// Convert an integer or integer string to Roman numerals.
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

/// CamelCase alias for to_roman_numerals.
#[pyfunction]
#[pyo3(name = "toRomanNumerals")]
fn to_roman_numerals_camel_py(num: &Bound<'_, PyAny>) -> PyResult<String> {
    to_roman_numerals_py(num)
}

/// Liven IOR (Introduction Outline Reference) links in HTML text using Rust.
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
    let find_section_fn = |v_abbr: &str, bbb: &str, c: &str, v: &str| -> Option<usize> {
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
    };

    match liven_iors_core(version_abbreviation, our_bbb, segment_type, ior_html, is_single_chapter, find_section_fn) {
        Ok(res) => Ok(res),
        Err(IORLinkError::InvalidSegmentType(seg)) => {
            Err(PyValueError::new_err(format!("Unsupported segmentType: {seg}")))
        }
        Err(IORLinkError::Custom(msg)) => Err(PyValueError::new_err(msg)),
    }
}

/// CamelCase alias for liven_iors.
#[pyfunction]
#[pyo3(
    name = "livenIORs",
    signature = (version_abbreviation, our_bbb, segment_type, ior_html, is_single_chapter, state=None)
)]
fn liven_iors_camel_py<'py>(
    py: Python<'py>,
    version_abbreviation: &str,
    our_bbb: &str,
    segment_type: &str,
    ior_html: &str,
    is_single_chapter: bool,
    state: Option<&Bound<'py, PyAny>>,
) -> PyResult<String> {
    liven_iors_py(py, version_abbreviation, our_bbb, segment_type, ior_html, is_single_chapter, state)
}

/// Convert USFM character formatting to HTML using Rust.
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

    let result = convert_usfm_character_formatting(
        version_abbrev,
        bbb,
        segment_type,
        usfm_field,
        basic_only,
        &expanded_char_markers,
        &booklist_nt27,
        is_net_version,
        level,
    );

    let dict = PyDict::new(py);
    dict.set_item("html", result.html)?;
    dict.set_item("background_colour", result.background_colour)?;
    dict.set_item("files_to_copy", result.files_to_copy)?;
    Ok(dict.into())
}

/// CamelCase alias for convert_usfm_character_formatting.
#[pyfunction]
#[pyo3(
    name = "convertUSFMCharacterFormatting",
    signature = (version_abbrev, bbb, segment_type, usfm_field, basic_only, expanded_char_markers, booklist_nt27, is_net_version, level=0)
)]
fn convert_usfm_character_formatting_camel_py(
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
    convert_usfm_character_formatting_py(
        py,
        version_abbrev,
        bbb,
        segment_type,
        usfm_field,
        basic_only,
        expanded_char_markers,
        booklist_nt27,
        is_net_version,
        level,
    )
}

/// Liven a cross-reference or footnote xt field using Rust.
///
/// Parameters match the Python `livenXRefField` signature:
///   field_type, version_abbreviation, bbb, c, v, segment_type,
///   path_prefix, xo_text, xref_original_middle, state=None
#[pyfunction]
#[pyo3(
    name = "liven_xref_field",
    signature = (field_type, version_abbreviation, bbb, c, v, segment_type, path_prefix, xo_text, xref_original_middle, state=None)
)]
fn liven_xref_field_py<'py>(
    _py: Python<'py>,
    field_type: &str,
    version_abbreviation: &str,
    bbb: &str,
    c: &str,
    v: &str,
    segment_type: &str,
    path_prefix: &str,
    xo_text: &str,
    xref_original_middle: &str,
    state: Option<&Bound<'py, PyAny>>,
) -> PyResult<String> {
    let find_section_fn = |v_abbr: &str, target_bbb: &str, target_c: &str, target_v: &str| -> Option<usize> {
        if let Some(state_obj) = state {
            let py_env = state_obj.py();
            if let Ok(module) = py_env.import("createSectionPages") {
                if let Ok(func) = module.getattr("findSectionNumber") {
                    if let Ok(res) = func.call1((v_abbr, target_bbb, target_c, target_v, state_obj)) {
                        if let Ok(opt_num) = res.extract::<Option<usize>>() {
                            return opt_num;
                        }
                    }
                }
            }
        }
        None
    };

    match liven_xref_field_core(
        field_type,
        version_abbreviation,
        bbb,
        c,
        v,
        segment_type,
        path_prefix,
        xo_text,
        xref_original_middle,
        find_section_fn,
    ) {
        Ok(result) => Ok(result),
        Err(XRefError::InvalidFieldType(ft)) => {
            Err(PyValueError::new_err(format!("Invalid fieldType: {ft}")))
        }
        Err(XRefError::InvalidSegmentType(seg)) => {
            Err(PyValueError::new_err(format!("Unsupported segmentType: {seg}")))
        }
        Err(XRefError::Custom(msg)) => Err(PyValueError::new_err(msg)),
    }
}

/// CamelCase alias for liven_xref_field.
#[pyfunction]
#[pyo3(
    name = "livenXRefField",
    signature = (field_type, version_abbreviation, bbb, c, v, segment_type, path_prefix, xo_text, xref_original_middle, state=None)
)]
fn liven_xref_field_camel_py<'py>(
    py: Python<'py>,
    field_type: &str,
    version_abbreviation: &str,
    bbb: &str,
    c: &str,
    v: &str,
    segment_type: &str,
    path_prefix: &str,
    xo_text: &str,
    xref_original_middle: &str,
    state: Option<&Bound<'py, PyAny>>,
) -> PyResult<String> {
    liven_xref_field_py(py, field_type, version_abbreviation, bbb, c, v, segment_type, path_prefix, xo_text, xref_original_middle, state)
}

// ── verse_entry_list PyO3 wrapper ──────────────────────────────────────────

/// Convert a list of verse entries to HTML using Rust.
///
/// This is the Rust port of `convertVerseEntryListToHtml` from `usfm.py`.
/// Heavy processing is done in Rust; file I/O and validation callbacks
/// remain in Python via the `convert_char_formatting_fn`, `copy_fig_files_fn`,
/// `get_open_bible_images_fn`, and `check_html_fn` parameters.
///
/// Returns a JSON string with keys: `html`, `cross_references`, `footnotes`.
#[pyfunction]
#[pyo3(name = "convert_verse_entry_list_to_html")]
#[pyo3(signature = (
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
    convert_char_formatting_fn,
    _copy_fig_files_fn,
    _get_open_bible_images_fn,
    _check_html_fn,
    state=None,
))]
fn convert_verse_entry_list_to_html_py<'py>(
    py: Python<'py>,
    level: usize,
    version_abbreviation: &str,
    bbb: &str,
    c: Option<&str>,
    v: Option<&str>,
    segment_type: &str,
    context_list: Vec<String>,
    verse_entries: Vec<Bound<'py, PyAny>>,
    basic_only: bool,
    is_single_chapter_book: bool,
    convert_char_formatting_fn: &Bound<'py, PyAny>,
    _copy_fig_files_fn: &Bound<'py, PyAny>,
    _get_open_bible_images_fn: &Bound<'py, PyAny>,
    _check_html_fn: &Bound<'py, PyAny>,
    state: Option<&Bound<'py, PyAny>>,
) -> PyResult<Py<PyAny>> {
    // Extract verse entries
    let mut entries = Vec::with_capacity(verse_entries.len());
    for py_entry in &verse_entries {
        let marker: String = py_entry.getattr("marker")?.extract()?;
        let full_text: String = py_entry.getattr("full_text")?.extract()?;
        let clean_text: String = py_entry.getattr("clean_text")?.extract()?;
        entries.push(verse_entry_list::VerseEntry { marker, full_text, clean_text });
    }

    // Build find_section_fn callback
    let find_section_fn = |v_abbr: &str, target_bbb: &str, target_c: &str, target_v: &str| -> Option<usize> {
        if let Some(state_obj) = state {
            let py_env = state_obj.py();
            if let Ok(module) = py_env.import("createSectionPages") {
                if let Ok(func) = module.getattr("findSectionNumber") {
                    if let Ok(res) = func.call1((v_abbr, target_bbb, target_c, target_v, state_obj)) {
                        if let Ok(opt_num) = res.extract::<Option<usize>>() {
                            return opt_num;
                        }
                    }
                }
            }
        }
        None
    };

    // Build convert_char_formatting callback (calls Python)
    let convert_char_formatting = |
        va: &str, bbb_inner: &str, st: &str, field: &str, bo: bool,
        bg: &mut Option<String>,
    | -> Result<String, verse_entry_list::ConvertError> {
        let py_ref_tuple = (bbb_inner, c.unwrap_or(""), v.unwrap_or(""));
        let result = convert_char_formatting_fn.call1((
            va, py_ref_tuple, st, field, bo,
        ));
        match result {
            Ok(obj) => {
                if let Ok(dict) = obj.extract::<Bound<'_, PyDict>>() {
                    if let Ok(html_out) = dict.get_item("html") {
                        if let Some(h) = html_out {
                            if let Ok(s) = h.extract::<String>() {
                                if let Ok(bc) = dict.get_item("background_colour") {
                                    if let Some(b) = bc {
                                        *bg = b.extract::<Option<String>>().ok().flatten();
                                    }
                                }
                                return Ok(s);
                            }
                        }
                    }
                }
                // Fallback: try extracting as string directly
                if let Ok(s) = obj.extract::<String>() {
                    return Ok(s);
                }
                Err(verse_entry_list::ConvertError::AssertionFailed(
                    format!("convert_char_formatting returned unexpected type for '{field}'")
                ))
            }
            Err(e) => Err(verse_entry_list::ConvertError::AssertionFailed(
                format!("convert_char_formatting call failed: {e}")
            )),
        }
    };

    let no_op_fig = |_files: &[(String, String)]| {};
    let no_op_obi = |_l: usize, _st: &str, _b: &str, _c: &str, _v: &str| -> Option<String> { None };
    let no_op_check = |_w: &str, _h: &str| -> bool { true };

    let context_refs: Vec<&str> = context_list.iter().map(|s| s.as_str()).collect();

    let result = verse_entry_list::convert_verse_entry_list_to_html_core(
        level,
        version_abbreviation,
        bbb,
        c,
        v,
        segment_type,
        &context_refs,
        &entries,
        basic_only,
        is_single_chapter_book,
        convert_char_formatting,
        no_op_fig,
        find_section_fn,
        no_op_obi,
        no_op_check,
    );

    match result {
        Ok(html) => {
            let dict = PyDict::new(py);
            dict.set_item("html", html)?;
            dict.set_item("cross_references", "")?;
            dict.set_item("footnotes", "")?;
            Ok(dict.unbind().into_any())
        }
        Err(e) => Err(PyValueError::new_err(format!("convert_verse_entry_list_to_html failed: {e}"))),
    }
}

/// CamelCase alias for convert_verse_entry_list_to_html.
#[pyfunction]
#[pyo3(name = "convertVerseEntryListToHtml")]
#[pyo3(signature = (
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
    convert_char_formatting_fn,
    copy_fig_files_fn,
    get_open_bible_images_fn,
    check_html_fn,
    state=None,
))]
fn convert_verse_entry_list_to_html_camel_py<'py>(
    py: Python<'py>,
    level: usize,
    version_abbreviation: &str,
    bbb: &str,
    c: Option<&str>,
    v: Option<&str>,
    segment_type: &str,
    context_list: Vec<String>,
    verse_entries: Vec<Bound<'py, PyAny>>,
    basic_only: bool,
    is_single_chapter_book: bool,
    convert_char_formatting_fn: &Bound<'py, PyAny>,
    copy_fig_files_fn: &Bound<'py, PyAny>,
    get_open_bible_images_fn: &Bound<'py, PyAny>,
    check_html_fn: &Bound<'py, PyAny>,
    state: Option<&Bound<'py, PyAny>>,
) -> PyResult<Py<PyAny>> {
    convert_verse_entry_list_to_html_py(
        py, level, version_abbreviation, bbb, c, v, segment_type,
        context_list, verse_entries, basic_only, is_single_chapter_book,
        convert_char_formatting_fn, copy_fig_files_fn, get_open_bible_images_fn,
        check_html_fn, state,
    )
}

// ── verse_to_html PyO3 wrappers ───────────────────────────────────────────

/// Process cross-references in HTML, replacing `\x…\x*` markers with live links.
///
/// Returns `(html, cross_references_html)`.
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
    let find_section_fn = |v_abbr: &str, target_bbb: &str, target_c: &str, target_v: &str| -> Option<usize> {
        if let Some(state_obj) = state {
            let py_env = state_obj.py();
            if let Ok(module) = py_env.import("createSectionPages") {
                if let Ok(func) = module.getattr("findSectionNumber") {
                    if let Ok(res) = func.call1((v_abbr, target_bbb, target_c, target_v, state_obj)) {
                        if let Ok(opt_num) = res.extract::<Option<usize>>() {
                            return opt_num;
                        }
                    }
                }
            }
        }
        None
    };

    match verse_to_html::process_cross_references_core(
        html, version_abbreviation, bbb, c, segment_type, path_prefix, find_section_fn,
    ) {
        Ok(result) => Ok(result),
        Err(e) => Err(PyValueError::new_err(format!("process_cross_references failed: {e}"))),
    }
}

/// CamelCase alias.
#[pyfunction]
#[pyo3(name = "processCrossReferences")]
#[pyo3(signature = (html, version_abbreviation, bbb, c, segment_type, path_prefix, state=None))]
fn process_cross_references_camel_py<'py>(
    py: Python<'py>,
    html: &str,
    version_abbreviation: &str,
    bbb: &str,
    c: Option<&str>,
    segment_type: &str,
    path_prefix: &str,
    state: Option<&Bound<'py, PyAny>>,
) -> PyResult<(String, String)> {
    process_cross_references_py(py, html, version_abbreviation, bbb, c, segment_type, path_prefix, state)
}

/// Process footnotes in HTML, replacing `\f…\f*` markers with caller links.
///
/// Returns `(html, footnotes_html)`.
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
    let find_section_fn = |v_abbr: &str, target_bbb: &str, target_c: &str, target_v: &str| -> Option<usize> {
        if let Some(state_obj) = state {
            let py_env = state_obj.py();
            if let Ok(module) = py_env.import("createSectionPages") {
                if let Ok(func) = module.getattr("findSectionNumber") {
                    if let Ok(res) = func.call1((v_abbr, target_bbb, target_c, target_v, state_obj)) {
                        if let Ok(opt_num) = res.extract::<Option<usize>>() {
                            return opt_num;
                        }
                    }
                }
            }
        }
        None
    };

    match verse_to_html::process_footnotes_core(
        html, version_abbreviation, bbb, c, segment_type, path_prefix, max_footnote_chars, find_section_fn,
    ) {
        Ok(result) => Ok(result),
        Err(e) => Err(PyValueError::new_err(format!("process_footnotes failed: {e}"))),
    }
}

/// CamelCase alias.
#[pyfunction]
#[pyo3(name = "processFootnotes")]
#[pyo3(signature = (html, version_abbreviation, bbb, c, segment_type, path_prefix, max_footnote_chars, state=None))]
fn process_footnotes_camel_py<'py>(
    py: Python<'py>,
    html: &str,
    version_abbreviation: &str,
    bbb: &str,
    c: Option<&str>,
    segment_type: &str,
    path_prefix: &str,
    max_footnote_chars: usize,
    state: Option<&Bound<'py, PyAny>>,
) -> PyResult<(String, String)> {
    process_footnotes_py(py, html, version_abbreviation, bbb, c, segment_type, path_prefix, max_footnote_chars, state)
}

// ── standalone verse_entry_list (no Python char-formatting callback needed) ─

/// Convert verse entries to HTML — standalone version.
///
/// Calls `convert_usfm_character_formatting` directly in Rust (no Python
/// callback), handles figure-file copying via `destination_folder`, and
/// keeps Python callbacks only for OBI images, HTML validation, and
/// section-number lookup.
///
/// Parameters `get_open_bible_images_fn` and `check_html_fn` can be `None`.
#[pyfunction]
#[pyo3(name = "convertVerseEntryListToHtml2")]
#[pyo3(signature = (
    level,
    version_abbreviation,
    bbb,
    c=None,
    v=None,
    segment_type="chapter",
    context_list=None,
    verse_entries=None,
    basic_only=false,
    is_single_chapter_book=false,
    get_open_bible_images_fn=None,
    check_html_fn=None,
    destination_folder=None,
    state=None,
))]
fn convert_verse_entry_list_to_html_standalone_py<'py>(
    py: Python<'py>,
    level: usize,
    version_abbreviation: &str,
    bbb: &str,
    c: Option<&str>,
    v: Option<&str>,
    segment_type: &str,
    context_list: Option<Vec<String>>,
    verse_entries: Option<Vec<Bound<'py, PyAny>>>,
    basic_only: bool,
    is_single_chapter_book: bool,
    get_open_bible_images_fn: Option<&Bound<'py, PyAny>>,
    check_html_fn: Option<&Bound<'py, PyAny>>,
    destination_folder: Option<&str>,
    state: Option<&Bound<'py, PyAny>>,
) -> PyResult<Py<PyAny>> {
    let context_list = context_list.unwrap_or_default();
    let verse_entries = verse_entries.unwrap_or_default();

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
    let find_section_fn = |v_abbr: &str, target_bbb: &str, target_c: &str, target_v: &str| -> Option<usize> {
        if let Some(state_obj) = state {
            let py_env = state_obj.py();
            if let Ok(module) = py_env.import("createSectionPages") {
                if let Ok(func) = module.getattr("findSectionNumber") {
                    if let Ok(res) = func.call1((v_abbr, target_bbb, target_c, target_v, state_obj)) {
                        if let Ok(opt_num) = res.extract::<Option<usize>>() {
                            return opt_num;
                        }
                    }
                }
            }
        }
        None
    };

    // Build get_open_bible_images callback
    let no_op_obi = |_l: usize, _st: &str, _b: &str, _c: &str, _v: &str| -> Option<String> { None };
    let obi_fn;
    let obi_ref: &dyn Fn(usize, &str, &str, &str, &str) -> Option<String>;
    if let Some(obi_callable) = get_open_bible_images_fn {
        let obi_owned = obi_callable.clone();
        obi_fn = move |l: usize, st: &str, b: &str, c: &str, v: &str| -> Option<String> {
            if let Ok(res) = obi_owned.call1((l, st, b, c, v)) {
                res.extract::<Option<String>>().ok().flatten()
            } else {
                None
            }
        };
        obi_ref = &obi_fn;
    } else {
        obi_ref = &no_op_obi;
    }

    // Build check_html callback
    let no_op_check = |_w: &str, _h: &str| -> bool { true };
    let chk_fn;
    let chk_ref: &dyn Fn(&str, &str) -> bool;
    if let Some(chk_callable) = check_html_fn {
        let chk_owned = chk_callable.clone();
        chk_fn = move |w: &str, h: &str| -> bool {
            chk_owned.call1((w, h)).is_ok()
        };
        chk_ref = &chk_fn;
    } else {
        chk_ref = &no_op_check;
    }

    let context_refs: Vec<&str> = context_list.iter().map(|s| s.as_str()).collect();

    let result = verse_entry_list::convert_verse_entry_list_to_html_standalone(
        level,
        version_abbreviation,
        bbb,
        c,
        v,
        segment_type,
        &context_refs,
        &entries,
        basic_only,
        is_single_chapter_book,
        find_section_fn,
        obi_ref,
        chk_ref,
        destination_folder,
    );

    match result {
        Ok(html) => {
            let dict = PyDict::new(py);
            dict.set_item("html", html)?;
            dict.set_item("cross_references", "")?;
            dict.set_item("footnotes", "")?;
            Ok(dict.unbind().into_any())
        }
        Err(e) => Err(PyValueError::new_err(format!("convertVerseEntryListToHtml failed: {e}"))),
    }
}

#[pymodule]
fn openbibledata_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(liven_introduction_links_py, m)?)?;
    m.add_function(wrap_pyfunction!(liven_introduction_links_camel_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_bbb_from_oet_book_name_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_bbb_from_oet_book_name_camel_py, m)?)?;
    m.add_function(wrap_pyfunction!(to_roman_numerals_py, m)?)?;
    m.add_function(wrap_pyfunction!(to_roman_numerals_camel_py, m)?)?;
    m.add_function(wrap_pyfunction!(liven_iors_py, m)?)?;
    m.add_function(wrap_pyfunction!(liven_iors_camel_py, m)?)?;
    m.add_function(wrap_pyfunction!(convert_usfm_character_formatting_py, m)?)?;
    m.add_function(wrap_pyfunction!(convert_usfm_character_formatting_camel_py, m)?)?;
    m.add_function(wrap_pyfunction!(liven_xref_field_py, m)?)?;
    m.add_function(wrap_pyfunction!(liven_xref_field_camel_py, m)?)?;
    m.add_function(wrap_pyfunction!(process_cross_references_py, m)?)?;
    m.add_function(wrap_pyfunction!(process_cross_references_camel_py, m)?)?;
    m.add_function(wrap_pyfunction!(process_footnotes_py, m)?)?;
    m.add_function(wrap_pyfunction!(process_footnotes_camel_py, m)?)?;
    m.add_function(wrap_pyfunction!(convert_verse_entry_list_to_html_py, m)?)?;
    m.add_function(wrap_pyfunction!(convert_verse_entry_list_to_html_camel_py, m)?)?;
    m.add_function(wrap_pyfunction!(convert_verse_entry_list_to_html_standalone_py, m)?)?;
    Ok(())
}
