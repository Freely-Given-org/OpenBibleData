//! PyO3 module exposing OpenBibleData Rust extensions.

use pyo3::exceptions::{PyAssertionError, PyTypeError, PyValueError};
use pyo3::prelude::*;

pub mod intro_links;
pub mod oet_books;
pub mod roman_numerals;

pub use intro_links::{liven_introduction_links_core, IntroLinkError};
pub use oet_books::get_bbb_from_oet_book_name;
pub use roman_numerals::to_roman_numerals;

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

#[pymodule]
fn openbibledata_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(liven_introduction_links_py, m)?)?;
    m.add_function(wrap_pyfunction!(liven_introduction_links_camel_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_bbb_from_oet_book_name_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_bbb_from_oet_book_name_camel_py, m)?)?;
    m.add_function(wrap_pyfunction!(to_roman_numerals_py, m)?)?;
    m.add_function(wrap_pyfunction!(to_roman_numerals_camel_py, m)?)?;
    Ok(())
}
