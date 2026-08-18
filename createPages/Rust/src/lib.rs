//! PyO3 module exposing OpenBibleData Rust extensions.

use pyo3::exceptions::{PyAssertionError, PyTypeError, PyValueError};
use pyo3::prelude::*;

pub mod intro_links;
pub mod ior_links;
pub mod oet_books;
pub mod roman_numerals;
pub mod character_formatting;

pub use intro_links::{liven_introduction_links_core, IntroLinkError};
pub use ior_links::{liven_iors_core, IORLinkError};
pub use oet_books::get_bbb_from_oet_book_name;
pub use roman_numerals::to_roman_numerals;
pub use character_formatting::{convert_usfm_character_formatting, CharacterFormattingResult};

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
#[pyo3(name = "liven_iors")]
fn liven_iors_py(
    our_bbb: &str,
    segment_type: &str,
    ior_html: &str,
    is_single_chapter: bool,
) -> PyResult<String> {
    match liven_iors_core(our_bbb, segment_type, ior_html, is_single_chapter) {
        Ok(res) => Ok(res),
        Err(IORLinkError::InvalidSegmentType(seg)) => {
            Err(PyValueError::new_err(format!("Unsupported segmentType: {seg}")))
        }
        Err(IORLinkError::Custom(msg)) => Err(PyValueError::new_err(msg)),
    }
}

/// CamelCase alias for liven_iors.
#[pyfunction]
#[pyo3(name = "livenIORs")]
fn liven_iors_camel_py(
    our_bbb: &str,
    segment_type: &str,
    ior_html: &str,
    is_single_chapter: bool,
) -> PyResult<String> {
    liven_iors_py(our_bbb, segment_type, ior_html, is_single_chapter)
}

/// Convert USFM character formatting to HTML using Rust.
#[pyfunction]
#[pyo3(name = "convert_usfm_character_formatting")]
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
    );

    let dict = PyDict::new(py);
    dict.set_item("html", result.html)?;
    dict.set_item("background_colour", result.background_colour)?;
    dict.set_item("files_to_copy", result.files_to_copy)?;
    Ok(dict.into())
}

/// CamelCase alias for convert_usfm_character_formatting.
#[pyfunction]
#[pyo3(name = "convertUSFMCharacterFormatting")]
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
    )
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
    Ok(())
}
