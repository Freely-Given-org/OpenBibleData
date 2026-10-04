//! Byte-identical Rust port of the BCV index build over the OET word tables.
//!
//! The index maps each verse reference (e.g. `'MAT_1:1'`) to the inclusive
//! (first, last) row numbers of that verse's word-table rows inside
//! `state.OETRefData['word_tables'][wordTableFilename]`, where row 0 is the
//! header row and the first data row is index 1.
//!
//! This is a simple but mechanical per-row scan that used to run in Python
//! in createSitePages.py; it is now built in Rust for speed and to keep the
//! layout logic next to the other word-table helpers.
//!
//! Index semantics (must stay byte-identical with the old Python loop):
//!   * For each data row `n` (1-based offset into the table *including* the
//!     header row at index 0), take the first TSV field — the "Ref" field,
//!     e.g. `'MAT_1:1w1'`.
//!   * The BCV key is the part before the first `'w'` in the Ref field,
//!     e.g. `'MAT_1:1'`.
//!   * Groups of *consecutive rows with the same BCV key* map to
//!     `(firstRowNumber, lastRowNumber)` of the group (inclusive, using the
//!     same numbering that indexes the whole table, header included).
//!
//! Use: see `createSitePages._createSitePages` (point of creation) and the
//! lookups in createOETInterlinearPages.py / createParallelVersePages.py
//! (points of use).

use std::collections::HashMap;

use pyo3::prelude::*;

/// Byte-identical port of the Python BCV index build.
///
/// `rows` is the raw word-table list (row 0 is the header, so only indices
/// 1.. are scanned).  Rows are expected to be valid OET word-table rows;
/// a malformed row (no '\t') yields the whole row as its "Ref" field,
/// matching the old Python `split('\t', 1)[0]` behaviour.
pub fn build_word_table_index(rows: &[String]) -> HashMap<String, (usize, usize)> {
    let mut index = HashMap::new();
    let mut last_bcvref: Option<&str> = None;
    let mut start_ix = 1;
    let mut last_n = rows.len().saturating_sub(1);
    for (n, columns_string) in rows.iter().enumerate().skip(1) {
        last_n = n;
        let word_ref = columns_string.split('\t').next().unwrap_or(columns_string);
        let bcvref = match word_ref.find('w') {
            Some(i) => &word_ref[..i],
            None => word_ref,
        };
        if last_bcvref != Some(bcvref) {
            if let Some(last) = last_bcvref {
                index.insert(last.to_string(), (start_ix, n - 1));
            }
            start_ix = n;
            last_bcvref = Some(bcvref);
        }
    }
    if let Some(last) = last_bcvref {
        index.insert(last.to_string(), (start_ix, last_n));
    }
    index
}

#[pyfunction(name = "build_word_table_index")]
pub fn build_word_table_index_py(rows: Vec<String>) -> PyResult<HashMap<String, (usize, usize)>> {
    Ok(build_word_table_index(&rows))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn builds_consecutive_groups() {
        let rows: Vec<String> = vec![
            "Ref\tRowType".to_string(),
            "MAT_1:1w1\tA".to_string(),
            "MAT_1:1w2\tB".to_string(),
            "MAT_1:2w1\tC".to_string(),
            "MAT_1:2w2\tD".to_string(),
            "MAT_1:2w3\tE".to_string(),
        ];
        let index = build_word_table_index(&rows);
        assert_eq!(index.len(), 2);
        assert_eq!(index["MAT_1:1"], (1, 2));
        assert_eq!(index["MAT_1:2"], (3, 5));
    }

    #[test]
    fn missing_w_in_ref_uses_whole_ref() {
        let rows: Vec<String> = vec![
            "Ref\tRowType".to_string(),
            "FRT_0\tA".to_string(),
            "FRT_0\tB".to_string(),
            "HAG_1:1w1\tC".to_string(),
        ];
        let index = build_word_table_index(&rows);
        assert_eq!(index["FRT_0"], (1, 2));
        assert_eq!(index["HAG_1:1"], (3, 3));
    }

    #[test]
    fn header_only_table_gives_empty_index() {
        let rows: Vec<String> = vec!["Ref\tRowType".to_string()];
        assert!(build_word_table_index(&rows).is_empty());
    }
}
