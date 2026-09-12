// SPDX-License-Identifier: GPL-3.0-or-later
//
// word_table_snapshot.rs
//
// Copy-on-write snapshot of state.OETRefData['word_tables'].
//
// Why it exists
//     The two liven wrappers (liven_oet_word_links_py and
//     liven_oet_compatible_berean_word_links_py) liven every word of every
//     verse by calling a Python closure get_row(number) → table[number] — one
//     Python↔Rust crossing PER WORD. Across the OET word tables (~581k OT rows
//     + ~166k NT rows) and 27 forked workers, that Python closure is the
//     dominant crossing cost in a full build.
//
// Design (mirrors the existing PageChromeConfig + SECTION_LOOKUP_CACHE
//     pre-fork COW snapshots in this crate)
//     The PARENT process builds this snapshot ONCE, before the worker Pool
//     forks, so every forked worker shares it via copy-on-write. Each row is
//     pre-split on '\t'. At liven time get_row is a pure Rust HashMap lookup
//     that joins the stored fields back on '\t' — byte-identical to Python's
//     table[number] because a row never contains '\t' inside a field, so
//     split+join is lossless (unit-tested below).
//
// Byte-exactness safety
//     If no snapshot was built (e.g. a single-process run, or isolated unit
//     tests calling the wrapper directly), get_row falls back to the ORIGINAL
//     Python closure, so the exact error strings asserted by the tests
//     (e.g. "KeyError: 99") are preserved byte-for-byte minus nothing.
//     This first phase deliberately does NOT touch the nfc_normalise closure
//     at all — NFC handling stays byte-identical by construction.

use std::collections::HashMap;
use std::sync::{Arc, Mutex, MutexGuard, OnceLock};

use pyo3::types::PyAny;
use pyo3::{Bound, pyfunction, PyResult, prelude::*};

/// word_file_name → (word number → pre-split row fields)
pub(crate) type WordTableSnapshot = HashMap<String, HashMap<i64, Vec<String>>>;

static WORD_TABLE_SNAPSHOT: OnceLock<Mutex<Option<Arc<WordTableSnapshot>>>> = OnceLock::new();

fn word_table_snapshot_lock() -> MutexGuard<'static, Option<Arc<WordTableSnapshot>>> {
    WORD_TABLE_SNAPSHOT
        .get_or_init(|| Mutex::new(None))
        .lock()
        .expect("word-table snapshot mutex poisoned")
}

/// True once a snapshot has been built (either pre-fork in the parent, or
///     lazily in a single-process / unit-test run).
pub(crate) fn snapshot_is_present() -> bool {
    word_table_snapshot_lock().is_some()
}

/// Pure-Rust lookup: pre-split fields for (word_file_name, word_number).
///     Returns None if no snapshot was built or the number is absent — the
///     wrappers then fall back to the original Python closure so error
///     strings stay byte-exact.
pub(crate) fn get_snapshot_row(word_file_name: &str, word_number: i64) -> Option<Vec<String>> {
    word_table_snapshot_lock()
        .as_ref()?
        .get(word_file_name)?
        .get(&word_number)
        .cloned()
}

/// Build the snapshot from state.OETRefData['word_tables'] in the PARENT,
///     before the worker Pool forks (no-op if a snapshot already exists, so a
///     forked worker re-calling it cannot clobber the parent's COW copy).
#[pyfunction]
pub fn build_word_table_snapshot_py<'py>(state: &Bound<'py, PyAny>) -> PyResult<()> {
    {
        let lock = word_table_snapshot_lock();
        if lock.is_some() {
            return Ok(());
        }
    }
    let word_tables = state.getattr("OETRefData")?.get_item("word_tables")?;
    let mut snapshot: WordTableSnapshot = HashMap::with_capacity(2);
    for word_file_name_item in word_tables.try_iter()? {
        let word_file_name_item = word_file_name_item?;
        let word_file_name: String = word_file_name_item.extract()?;
        let table = word_tables.get_item(&word_file_name)?;
        let mut word_table: HashMap<i64, Vec<String>> = HashMap::with_capacity(70_000);
        // The tables are dicts keyed by word number; older/edge builds may
        //     expose a plain sequence instead. Handle both.
        if table.hasattr("items")? {
            for pair in table.call_method0("items")?.try_iter()? {
                let pair = pair?;
                let number: i64 = pair.get_item(0)?.extract()?;
                let row: String = pair.get_item(1)?.extract()?;
                word_table.insert(number, row.split('\t').map(str::to_string).collect());
            }
        } else {
            for (index, row_item) in table.try_iter()?.enumerate() {
                let row_item = row_item?;
                let row: String = row_item.extract()?;
                word_table.insert(index as i64 + 1, row.split('\t').map(str::to_string).collect());
            }
        }
        snapshot.insert(word_file_name, word_table);
    }
    *word_table_snapshot_lock() = Some(Arc::new(snapshot));
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn split_join_round_trip_is_lossless() {
        let row = "MRK_1:1w1\tκαὶ\tkai\t1\t24560\tC\tNone\tABCDEfghi\tX";
        let fields: Vec<String> = row.split('\t').map(str::to_string).collect();
        assert_eq!(fields[7], "ABCDEfghi");
        assert_eq!(fields.join("\t"), row);
    }

    #[test]
    fn empty_field_round_trips() {
        let row = "a\tb\t\t\td";
        let fields: Vec<String> = row.split('\t').map(str::to_string).collect();
        assert_eq!(fields.len(), 5);
        assert_eq!(fields.join("\t"), row);
    }
}
