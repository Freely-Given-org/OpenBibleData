//! Rust port of `createPages/OETHandlers.py` (deleted 2026-08-25).
//!
//! The PyO3 wrappers that expose these functions to Python live in `lib.rs`
//! (they pull rows out of `state.OETRefData` and build/inspect BOS
//! `InternalBibleEntry` objects). Everything in this module is pure Rust so
//! that it can be unit tested without a Python interpreter.
//!
//! Faithfulness notes (deliberate quirks preserved from the Python code):
//! * `preprocess_oet_rv_entry` compares the full `(BBB,C,V)` tuple against the
//!   exception list using exact equality, so the 1- and 2-element literals in
//!   the original list (e.g., `('PSA','18')`) can never match a 3-tuple —
//!   they are kept here for documentation but are unreachable, exactly as in
//!   the Python original.
//! * The Hebrew strongs colourisation loop skips any strongs number outside
//!   `[-1..200]` (mirroring BOS `getSmallLeadingInt`'s range check), which
//!   means the `hebNeg`/`hebEl`/`hebYhwh` classes can never actually trigger
//!   for real Strong's numbers like '3068'. Preserved as-is.
//! * `get_bbb_from_oet_book_name_core` still returns the fallback book code
//!   even when it isn't a valid BOS book code (only the old dPrint differed).
//! * The OET-RV TEST_MODE preprocessing now leaves any word containing the
//!   missing/untranslated-verse placeholders `◘`/`◙` untouched (they can sit
//!   next to a footnote marker, e.g. `◘\f`, and must never be alpha-checked).

use std::sync::LazyLock;

use regex::Regex;

/// Word joiner used inside OET Hebrew glosses (makes console displays ugly).
pub const WJ: char = '\u{2060}';
/// Hebrew punctuation maqqaf -- word separator in uW quotes.
pub const MAQAF: char = '\u{05BE}';
/// Hebrew punctuation paseq.
pub const PASEQ: char = '\u{05C0}';
/// Narrow non-break space used by `tidy_bbb` inserts.
pub const NARROW_NON_BREAK_SPACE: char = '\u{202F}';

/// We inserted those § markers via the `titleTemplate='§«OrigWord»§'`.
static LINKED_WORD_TITLE_REGEX: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r#"="§(.+?)§""#).unwrap());
/// The ►NNNNN◄ placeholder href inserted by livenESFMWordLinks
/// (includes the closing double quote).
static LINKED_HREF_WORD_NUMBER_REGEX: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r#"="►([1-9][0-9]{0,5})◄""#).unwrap());
/// Note that single words might include a \sup \sup* span as in
/// 'Aʸsaias/(Yəshaˊə\sup yāh\sup*)¦21767' (handled by the SSsupP substitutions).
pub static LINKED_WORD_REGEX: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new("([-¬A-za-z0-9,'’ḨŌⱤḩⱪşţʦⱱĀĒāēéīōūəʸʼˊ/()]+)¦([1-9][0-9]{0,5})").unwrap()
});

// ── getOETTidyBBB ───────────────────────────────────────────────────────────

/// Apply the OET-specific renames after `bos_books_codes::tidy_bbb`
/// (port of the if-chain in `getOETTidyBBB`).
///
/// `insert_char` must already have `None` mapped to `""` (as the
/// `bos_books_codes_py.tidy_bbb` binding does).
pub fn apply_oet_tidy_renames(new_bbb: &str, insert_char: &str, add_notes: bool) -> String {
    let yonah_title = "Yonah (which is closer to the Hebrew יוֹנָה/Yōnāh)";
    let yohan_title = "Yohan (which is closer to the Greek Ἰωάννης/Yōannaʸs)";
    let yudas_title = "Yudas (which is closer to the Greek Ἰούδας/Youdas)";

    // OT
    if new_bbb == "JNA" {
        return if add_notes {
            format!("<span title=\"{yonah_title}\">YNA</span> (JNA)")
        } else {
            "YNA".to_string()
        };
    }
    if new_bbb == "Jna" {
        return if add_notes {
            format!("<span title=\"{yonah_title}\">Yna</span> (Jna)")
        } else {
            "Yna".to_string()
        };
    }
    // NT
    if new_bbb == "JHN" || new_bbb == "JOHN" {
        return if add_notes {
            format!("<span title=\"{yohan_title}\">YHN</span> (JHN)")
        } else {
            "YHN".to_string()
        };
    }
    if new_bbb == "Jhn" || new_bbb == "John" {
        return if add_notes {
            format!("<span title=\"{yohan_title}\">Yhn</span> (Jhn)")
        } else {
            "Yhn".to_string()
        };
    }
    if new_bbb == "JAM" {
        return if add_notes { "YAC (JAM)".to_string() } else { "YAC".to_string() };
    }
    if new_bbb == "Jam" {
        return if add_notes { "Yac (Jam)".to_string() } else { "Yac".to_string() };
    }
    if new_bbb == "ACTS" {
        return "ACTs".to_string();
    }
    for n in ["1", "2", "3"] {
        // UPPERCASE variants (1JN, 2JN…)
        let upper = format!("{n}{insert_char}JN");
        if new_bbb == upper {
            return if add_notes {
                format!("{n}{insert_char}<span title=\"{yohan_title}\">YN</span> ({upper})")
            } else {
                format!("{n}{insert_char}YN")
            };
        }
        // Title case variants (1Jn, 2Jn…)
        let title = format!("{n}{insert_char}Jn");
        if new_bbb == title {
            return if add_notes {
                format!("{n}{insert_char}<span title=\"{yohan_title}\">Yn</span> ({title})")
            } else {
                format!("{n}{insert_char}Yn")
            };
        }
        // All-uppercase variants (1JHN, 2JHN…)
        let all_upper = format!("{n}{insert_char}JHN");
        if new_bbb == all_upper {
            return if add_notes {
                format!("{n}{insert_char}<span title=\"{yohan_title}\">YHN</span> ({all_upper})")
            } else {
                format!("{n}{insert_char}YHN")
            };
        }
        // Mixed variants (1Jhn, 2Jhn…)
        let mixed = format!("{n}{insert_char}Jhn");
        if new_bbb == mixed {
            return if add_notes {
                format!(
                    "{n}{insert_char}<span title=\"{yohan_title}\">Yhn</span> ({n}{insert_char}Yohan or {mixed})"
                )
            } else {
                format!("{n}{insert_char}Yhn")
            };
        }
    }
    if new_bbb == "JUDE" {
        return if add_notes {
            format!("<span title=\"{yudas_title}\">YUD</span> (JUD)")
        } else {
            "YUD".to_string()
        };
    }
    if new_bbb == "Jude" {
        return if add_notes {
            format!("<span title=\"{yudas_title}\">Yud</span> (Jud)")
        } else {
            "Yud".to_string()
        };
    }
    new_bbb.to_string()
}

// ── getOETBookName ──────────────────────────────────────────────────────────

/// Handle our different spellings of well-known book names
/// (port of `getOETBookName`). Returns `None` when the BBB is unknown
/// (the Python code crashed on `None.replace(...)` in that case).
pub fn oet_book_name(bos_book_code: &str) -> Option<String> {
    const REPLACEMENTS: [(&str, &str); 24] = [
        ("Joshua", "Yehoshua/(Joshua)"),
        ("‘Judges’", "Heroes/(‘Judges’)"),
        ("1 Samuel", " 1 Shemuel/(Samuel)"),
        ("2 Samuel", " 2 Shemuel/(Samuel)"),
        ("Job", "Iyyov/(Job)"),
        ("Psalms", "Songs/(Psalms)"),
        ("Isaiah", "Yeshayah/(Isaiah)"),
        ("Jeremiah", "Yermeyah/(Jeremiah)"),
        ("Ezekiel", "Yehezkel/(Ezekiel)"),
        ("Joel", "Yoel/(Joel)"),
        ("Amos", "Amots/(Amos)"),
        ("Obadiah", "Ovadyah/(Obadiah)"),
        ("Jonah", "Yonah/(Jonah)"),
        ("Micah", "Mikah/(Micah)"),
        ("Habakkuk", "Havakkuk/(Habakkuk)"),
        ("Zephaniah", "Tsefanyah/(Zephaniah)"),
        ("Zechariah", "Zekaryah/(Zechariah)"),
        ("Malachi", "Malaki/(Malachi)"),
        ("John", "Yohan/(John)"),
        ("James", "Yacob/Jacob/(James)"),
        ("1 John", " 1 Yohan/(John)"),
        ("2 John", " 2 Yohan/(John)"),
        ("3 John", " 3 Yohan/(John)"),
        ("Jude", "Yudas/(Jude)"),
    ];
    let mut name = bos_books_codes::get_english_name_nr(bos_book_code)?.to_string();
    for (from, to) in REPLACEMENTS {
        name = name.replace(from, to);
    }
    Some(name)
}

// ── getBBBFromOETBookName ───────────────────────────────────────────────────

/// Result of looking up a BBB from an English/OET bookname.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BbbLookup {
    /// Found a valid book code.
    Found(&'static str),
    /// The fallback lookup produced something, but it isn't a valid BOS book
    /// code — the Python original returned it anyway (after a dPrint).
    InvalidFallback(&'static str),
    /// Nothing found at all; the Python original returned None.
    NotFound,
}

impl BbbLookup {
    /// The book code if one was produced (even an invalid fallback).
    pub fn code(&self) -> Option<&'static str> {
        match self {
            BbbLookup::Found(code) | BbbLookup::InvalidFallback(code) => Some(code),
            BbbLookup::NotFound => None,
        }
    }
}

/// Remove spaces, narrow non-break spaces, and periods, then uppercase.
fn normalise_bookname(original_book_name: &str) -> String {
    original_book_name
        .chars()
        .filter(|&c| c != ' ' && c != NARROW_NON_BREAK_SPACE && c != '.')
        .flat_map(char::to_uppercase)
        .collect()
}

/// Port of `getBBBFromOETBookName`. Reuses the identical table from
/// `oet_books.rs`, then falls back to BibleOrgSys English-name lookups.
///
/// NOTE: unlike `oet_books::get_bbb_from_oet_book_name` (used internally by
/// `intro_links.rs`, which drops invalid fallbacks), this faithful port
/// returns invalid fallback codes too — see [`BbbLookup::InvalidFallback`].
pub fn get_bbb_from_oet_book_name_core(original_book_name: &str) -> BbbLookup {
    let uppered = normalise_bookname(original_book_name);

    if let Some(bos_book_code) = crate::oet_books::get_oet_bbb(&uppered) {
        return BbbLookup::Found(bos_book_code);
    }

    match bos_books_codes::english_name_to_bos_book_code(&uppered) {
        Some(code) if bos_books_codes::is_valid_bos_book_code(code) => BbbLookup::Found(code),
        Some(code) => BbbLookup::InvalidFallback(code),
        None => BbbLookup::NotFound,
    }
}

// ── wordpage filenames ──────────────────────────────────────────────────────

/// Approximation of Python `str.isdigit()` (empty string → False).
fn py_is_digit(s: &str) -> bool {
    !s.is_empty() && s.chars().all(|c| c.is_numeric())
}

/// Take an OT word-table row like `JNA_1:5w3<TAB>…` and make the wordpage
/// filename `JNAc1v5w3.htm`; segment/note rows become e.g. `JNAc1v5s2.htm`
/// (port of `getHebrewWordpageFilename` minus the state/table access).
pub fn hebrew_wordpage_filename_from_row(row: &str) -> Result<String, String> {
    let parts: Vec<&str> = row.splitn(4, '\t').collect();
    if parts.len() < 4 {
        return Err(format!(
            "AssertionError: not enough values to unpack in OT word-table row '{row}' (expected at least 4 tab-separated fields)"
        ));
    }
    let mut reference = parts[0].replacen('_', "c", 1).replacen(':', "v", 1).to_string();

    if !reference.contains('w') {
        let letter = if parts[1] == "seg" {
            "s"
        } else if parts[1].contains("note") {
            "n"
        } else {
            return Err(format!(
                "AssertionError: unexpected rowType '{}' in OT word-table row '{row}'",
                parts[1]
            ));
        };
        if !py_is_digit(parts[2]) {
            return Err(format!(
                "AssertionError: morpheme row number/list '{}' is not numeric in OT word-table row '{row}'",
                parts[2]
            ));
        }
        reference = format!("{reference}{letter}{}", parts[2]);
    }

    Ok(format!("{reference}.htm"))
}

/// Take an NT word-table row like `MRK_1:1w2<TAB>…` and make the wordpage
/// filename `MRKc1v1w2.htm` (port of `getGreekWordpageFilename` minus the
/// state/table access).
pub fn greek_wordpage_filename_from_row(row: &str) -> Result<String, String> {
    let first_field = row.split('\t').next().unwrap_or("");
    Ok(format!(
        "{}.htm",
        first_field.replacen('_', "c", 1).replacen(':', "v", 1)
    ))
}

// ── TEST_MODE preprocessing of OET-RV entries ───────────────────────────────

/// Words that are never wrapped in a `noLinkYet` span (verbatim from the
/// original list in `livenOETWordLinks`).
const NO_LINK_YET_SKIP_SET: &[&str] = &[
    "“", "”", "’", "+", "\\x", "\\xo", "\\xt", "\\f", "\\fr", "(Heb.", "—", "i.e.,", "≈i.e.,",
    "=", "◙", "…", "◘", "\\add", "\\+add", "“\\add", "‘\\add", "—\\add", "(\\add", "≈\\add",
    "^\\add", "→\\add", "i.e.,\\add*", "\\qs", "\\bd", "\\em", "\\+em", "\\fig", "\\it", "\\nd",
    "\\+nd", "‘\\nd", "\\wj", "“\\wj", "\\+wj", "’\\wj*", "—\\wj*", "“\\+wj", "\\z1", "\\z2",
    "\\z3", "\\z4", "\\zr",
];

/// References whose more complex spanning gets messed up when adding
/// "noLinkYet" in TEST_MODE. Compared with EXACT tuple equality against the
/// incoming `(BBB,C,V)` — so only the 3-element entries can ever match
/// (preserved verbatim from the original, including the unreachable shorter
/// entries).
const NO_LINK_YET_EXCEPTION_LIST: &[&[&str]] = &[
    &["EZR"],
    &["EZR", "5"],
    &["EZR", "5", "1"],
    &["EZR", "5", "12"],
    &["PSA"],
    &["PSA", "18"],
    &["PSA", "47"],
    &["PSA", "67"],
    &["PSA", "106"],
    &["PSA", "109"],
    &["PSA", "18", "1"],
    &["PSA", "47", "1"],
    &["PSA", "47", "4"],
    &["PSA", "67", "1"],
    &["PSA", "106", "1"],
    &["PSA", "106", "24"],
    &["PSA", "109", "1"],
    &["JER", "11"],
    &["LUK"],
    &["LUK", "11"],
    &["LUK", "16"],
    &["LUK", "17"],
    &["LUK", "18"],
    &["LUK", "22"],
    &["LUK", "24"],
    &["LUK", "11", "24"],
    &["LUK", "11", "37"],
    &["LUK", "11", "44"],
    &["LUK", "16", "1"],
    &["LUK", "16", "3"],
    &["LUK", "16", "31"],
    &["LUK", "16", "19"],
    &["LUK", "17", "7"],
    &["LUK", "18", "1"],
    &["LUK", "18", "3"],
    &["LUK", "22", "47"],
    &["LUK", "22", "51"],
    &["LUK", "24", "36"],
    &["LUK", "24", "47"],
];

const NO_LINK_YET_PREFIXES: &[&str] = &[
    "“", "‘", "(", "[", "—", "≈", "*", "@", "#", "%", "&", "<", ">", "^", "≡", "→", "?", "⇔",
];
const NO_LINK_YET_SUFFIXES: &[&str] = &[
    ",", ".", "?", "!", "”", "’", ":", ";", ")", "]", "\\add", "\\+add", "\\add*", "\\+add*",
    "\\x", "\\x*", "\\f", "\\f*", "\\bd*", "\\em*", "\\+em*", "\\it*", "\\nd*", "\\+nd*", "\\wj*",
    "\\+wj*", "\\qs", "\\qs*", "\\z1", "\\z2", "\\z3", "\\z4", "\\zr", "☺",
];

/// Exact-tuple-equality membership test (Python `refTuple not in (…)`)
/// preserving the arity quirk of the original literal list.
fn in_no_link_yet_exception_list(reference_tuple: &[&str]) -> bool {
    NO_LINK_YET_EXCEPTION_LIST.iter().any(|entry| *entry == reference_tuple)
}

/// Check `\add …\add*` balance like the original asserts do.
fn check_add_counts(text: &str, abbreviation: &str, bbb: &str, marker: &str) -> Result<(), String> {
    let opening_count = text.matches("\\add ").count();
    let closing_count = text.matches("\\add*").count();
    if opening_count != closing_count {
        return Err(format!(
            "Bad add open/close counts in OET {abbreviation} {bbb} {marker} line: {opening_count} != {closing_count}"
        ));
    }
    Ok(())
}

/// TEST_MODE preprocessing for one OET-RV entry: highlight words that don't
/// yet have a word link by wrapping them in `<span class="noLinkYet">…</span>`
/// (port of the first half of `livenOETWordLinks`).
///
/// Returns `Ok(Some(new_text))` when the entry changed, `Ok(None)` when it
/// should be kept as-is, or `Err(message)` for the various assertion failures
/// (the caller turns those into Python AssertionError exceptions).
pub fn preprocess_oet_rv_entry(
    marker: &str,
    original_text: &str,
    abbreviation: &str,
    ref_tuple: &[&str], // e.g. ['PSA'] or ['PSA','18','1'] -- arity matters!
) -> Result<Option<String>, String> {
    let bbb = ref_tuple[0];
    check_add_counts(original_text, abbreviation, bbb, marker)?;
    if original_text.is_empty() || marker != "v~" {
        return Ok(None);
    }
    if original_text.contains("\\nd \\nd ") {
        return Err(format!("Double nd in {abbreviation} {bbb} {marker:?} {original_text:?}"));
    }

    let mut words: Vec<String> = original_text
        .replace('—', " —")
        .split_whitespace()
        .map(String::from)
        .collect();
    let mut change_made = false;
    let mut in_note = false;

    for word_slot in words.iter_mut() {
        let o_word = word_slot.clone();
        let mut new_word;

        // There's a cross-ref butted up to the left of a word
        // TODO: For now we'll take the easy way and just skip it
        if o_word.contains("\\x*") && !o_word.starts_with("\\x*") && !o_word.ends_with("\\x*") {
            in_note = false;
            continue;
        }

        if o_word.contains('¦')
            || o_word.contains('◘')
            || o_word.contains('◙')
            || in_note
            || NO_LINK_YET_SKIP_SET.contains(&o_word.as_str())
        {
            // Leave it alone ('¦' is the word-link marker; '◘'/'◙' are the
            // missing/untranslated-verse placeholders, which can sit next to a
            // footnote marker like '\f' -- they must never be alpha-checked)
            new_word = o_word.clone();
        } else if !in_no_link_yet_exception_list(ref_tuple) {
            let mut prefix = String::new();
            let mut suffix = String::new();
            let mut adj_word = o_word.clone();
            for _iteration in 0..5 {
                for potential_prefix in NO_LINK_YET_PREFIXES {
                    if adj_word.starts_with(potential_prefix) {
                        prefix.push_str(potential_prefix);
                        adj_word = adj_word[potential_prefix.len()..].to_string();
                    }
                }
                for potential_suffix in NO_LINK_YET_SUFFIXES {
                    if adj_word.ends_with(potential_suffix) {
                        suffix = format!("{potential_suffix}{suffix}");
                        adj_word.truncate(adj_word.len() - potential_suffix.len());
                    }
                    // Note: this second check can cut mid-word, exactly as
                    // the original Python code does
                    if let Some(index) = adj_word.find(potential_suffix) {
                        suffix = format!("{}{suffix}", &adj_word[index..]);
                        adj_word.truncate(index);
                    }
                }
            }
            new_word = o_word.clone();
            if !adj_word.is_empty() && !adj_word.starts_with('\\') && !py_is_digit(&adj_word) {
                let needs_alpha_check = !adj_word.contains('\'')
                    && !adj_word.contains(',')
                    && !adj_word.contains('-')
                    && !adj_word.contains('/')
                    && !adj_word.contains('(')
                    && !adj_word.chars().next().is_some_and(|c| c.is_numeric())
                    && !matches!(adj_word.as_str(), "i.e" | "e.g");
                if needs_alpha_check && !adj_word.chars().all(char::is_alphabetic) {
                    return Err(format!(
                        "{bbb} prefix={prefix:?} adjWord={adj_word:?} suffix={suffix:?}"
                    ));
                }
                new_word =
                    format!("{prefix}<span class=\"noLinkYet\">{adj_word}</span>{suffix}");
                change_made = true;
            }
        } else {
            // Reference is in the exception list -- leave it alone
            new_word = o_word.clone();
        }

        *word_slot = new_word;
        let updated = word_slot.as_str();
        if updated.ends_with("\\x") || updated.ends_with("\\f") || updated.ends_with("\\fig") {
            in_note = true;
        } else if updated.ends_with("\\x*")
            || updated.ends_with("\\f*")
            || updated.ends_with("\\fig*")
        {
            in_note = false;
        }
    }

    if change_made {
        let joined = words.join(" ").replace(" —", "—");
        check_add_counts(&joined, abbreviation, bbb, "")?;
        Ok(Some(joined))
    } else {
        Ok(None)
    }
}

// ── §-title post-processing ─────────────────────────────────────────────────

/// Outcome of post-processing the `§…§` titles inserted by livenESFMWordLinks.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TitlePostprocess {
    /// At least one title/href was replaced.
    Updated {
        text: String,
        transliterations_added: usize,
        colourisations_added: usize,
    },
    /// The text contained '§' but nothing matched the title regex.
    /// (The Python caller logged a critical message and then hit
    /// `assert False, "We want to stop here"`.)
    NoTitleMatches,
}

/// Strict version of BOS `getSmallLeadingInt` including its range check:
/// values outside `[-1..200]` are errors (so real Strong's numbers like
/// '3068' fail -- see the module-level faithfulness notes).
fn strict_small_leading_int(s: &str) -> Result<i16, ()> {
    let bytes = s.as_bytes();
    let mut end = 0;
    if bytes.is_empty() {
        return Err(());
    }
    if bytes[0] == b'-' {
        end = 1;
    }
    while end < bytes.len() && bytes[end].is_ascii_digit() {
        end += 1;
    }
    if end == 0 || (end == 1 && bytes[0] == b'-') {
        return Err(());
    }
    let value: i32 = s[..end].parse().map_err(|_| ())?;
    if !(-1..=200).contains(&value) {
        return Err(());
    }
    Ok(value as i16)
}

/// GREEK_CASE_CLASS_DICT from createParallelVersePages.py.
fn greek_case_class(character: char) -> Option<&'static str> {
    match character {
        'N' | 'n' => Some("Nom"),
        'G' | 'g' => Some("Gen"),
        'A' | 'a' => Some("Acc"),
        'D' | 'd' => Some("Dat"),
        'V' | 'v' => Some("Voc"),
        _ => None,
    }
}

/// Find the next occurrence of an ASCII byte at/after `from`
/// (both given in byte offsets; result is a byte offset).
fn find_byte(text: &str, byte: u8, from: usize) -> Option<usize> {
    let start = from.min(text.len());
    text.as_bytes()[start..]
        .iter()
        .position(|&b| b == byte)
        .map(|index| index + start)
}

/// Post-process the `§«OrigWord»§ / ►NNNN◄` placeholders left by
/// livenESFMWordLinks into real hrefs + transliterated titles + colourisation
/// classes (port of the second half of both `livenOETWordLinks` and
/// `livenOETCompatibleBereanWordLinks`).
///
/// `get_row` fetches a word-table row by number (NT or OT depending on
/// `is_nt`); `nfc_normalise` should apply Unicode NFC (passed as a closure so
/// that this core stays dependency-free).
///
/// Position arithmetic note: the Python original reuses match positions from
/// before an edit on the edited string. All our edits happen strictly after
/// `title_match.end()`, so those stay valid; and advancing the next search to
/// the pre-edit `href_match.end()` only ever skips ahead inside the freshly
/// inserted (pure ASCII) href, never over real content.
/// `colourise_word_classes` controls whether the grammatical marker classes
/// (e.g. `hebVrb`/`grkVrb`/`hebEl`/`hebYhwh`/`grkNom`) are added to the word
/// anchors. Only the page families whose stylesheets actually style those
/// classes (parallel-verse, interlinear, reference) should pass `true`; the
/// chapter/book/section/parallel-passage/topic families leave them emitted but
/// unstyled, and the shared dark-mode rules then paint them unreadably.
pub fn postprocess_word_link_titles(
    original_text: &str,
    level: usize,
    is_nt: bool,
    get_row: &dyn Fn(i64) -> Result<String, String>,
    nfc_normalise: &dyn Fn(&str) -> String,
    colourise_word_classes: bool,
) -> Result<TitlePostprocess, String> {
    let mut text = original_text.to_string();
    let mut transliterations_added = 0usize;
    let mut colourisations_added = 0usize;
    let dots = "../".repeat(level);

    loop {
        // Get out all the information we need
        let Some(title_match) = LINKED_WORD_TITLE_REGEX.find_at(&text, 0) else {
            break;
        };
        let Some(href_match) = LINKED_HREF_WORD_NUMBER_REGEX.find_at(&text, title_match.end())
        else {
            // What went wrong here
            return Err(
                "We want to stop here -- no word-number href found after §title§".to_string(),
            );
        };
        // Should be immediately after href
        if href_match.start() - title_match.end() != 5 {
            return Err(format!(
                "AssertionError: expected href immediately after §title§ (gap {} != 5)",
                href_match.start() - title_match.end()
            ));
        }
        let word_number: i64 = LINKED_HREF_WORD_NUMBER_REGEX
            .captures_at(&text, href_match.start())
            .and_then(|captures| captures.get(1)?.as_str().parse().ok())
            .ok_or_else(|| "Unable to parse word number".to_string())?;

        // Positions of the title match are preserved across all the edits
        // below because every edit happens after them.
        let (title_start, title_end) = (title_match.start(), title_match.end());

        if is_nt {
            let row = get_row(word_number)?;
            let fields: Vec<&str> = row.split('\t').collect();
            if fields.len() < 12 {
                return Err(format!(
                    "AssertionError: NT word-table row {word_number} has {} tab-separated fields, expected 12",
                    fields.len()
                ));
            }
            let greek_word = fields[1];
            let sr_lemma = fields[2];
            let extended_strongs = fields[8];
            let role_letter = fields[9];
            let morphology = fields[10];

            // Put in the correct word link
            let filename = greek_wordpage_filename_from_row(&row)?;
            let new_href = format!("=\"{dots}ref/GrkWrd/{filename}#Top\"");
            let href_end = href_match.end();
            text = format!(
                "{}{}{}",
                &text[..href_match.start()],
                new_href,
                &text[href_end..]
            );

            // Do colourisation
            // NOTE: We have almost identical code in brightenSRGNT()
            //       in createParallelVersePages.py
            let mut case_class_name: Option<String> = None;
            if colourise_word_classes {
                case_class_name = if role_letter == "V" {
                    Some("grkVrb".to_string())
                } else if extended_strongs == "37560" {
                    // Greek 'οὐ' (ou) 'not'
                    Some("grkNeg".to_string())
                } else if morphology != "None" {
                    let fourth_char = morphology.chars().nth(4).ok_or_else(|| {
                        format!("IndexError: morphology '{morphology}' has no fifth character")
                    })?;
                    if fourth_char != '·' {
                        // (Middle dot) Two words in table have morphology of
                        // 'None' Jhn 5:27 w2
                        let class = greek_case_class(fourth_char).ok_or_else(|| {
                            format!(
                                "KeyError: unknown Greek case character '{fourth_char}' in morphology '{morphology}'"
                            )
                        })?;
                        Some(format!("grk{class}"))
                    } else {
                        None
                    }
                } else {
                    None
                };
            }

            if let Some(class_name) = case_class_name {
                // Add a class to the anchor for the English word
                // (Allow for '#Top"' -- hence +5)
                let anchor_end_index = find_byte(&text, b'>', href_end + 5)
                    .ok_or_else(|| "ValueError: '>' not found in wordlink anchor".to_string())?;
                colourisations_added += 1;
                text = format!(
                    "{} class=\"{}\"{}",
                    &text[..anchor_end_index],
                    class_name,
                    &text[anchor_end_index..]
                );
            }

            let transliterated_word = bible_transliterations::transliterate_greek(greek_word);
            let stripped_morphology = morphology.strip_prefix("····").unwrap_or(morphology);
            let from_part = if sr_lemma == transliterated_word {
                String::new()
            } else {
                format!(" from {sr_lemma}")
            };
            let new_title_guts = format!(
                "=\"{greek_word} ({transliterated_word}, {stripped_morphology}){from_part}\""
            );
            text = format!(
                "{}{}{}",
                &text[..title_start],
                new_title_guts,
                &text[title_end..]
            );

            transliterations_added += 1;
        } else {
            // OT
            let row = get_row(word_number)?;
            let fields: Vec<&str> = row.split('\t').collect();
            if fields.len() < 19 {
                return Err(format!(
                    "AssertionError: OT word-table row {word_number} has {} tab-separated fields, expected 19",
                    fields.len()
                ));
            }
            //  0    1        2             3        4           5     6                7            ...
            // 'Ref	RowType	LemmaRowList	MorphemeRowList	Strongs	Morphology	Word	NoCantillations	…'
            let strongs = fields[4];
            let morphology = fields[5];
            let no_cantillations = fields[7];

            // Put in the correct word link
            let filename = hebrew_wordpage_filename_from_row(&row)?;
            let new_href = format!("=\"{dots}ref/HebWrd/{filename}#Top\"");
            let href_end = href_match.end();
            text = format!(
                "{}{}{}",
                &text[..href_match.start()],
                new_href,
                &text[href_end..]
            );

            // Need to split at commas for correct transliteration
            let transliterated_word = no_cantillations
                .split(',')
                .map(|part| bible_transliterations::transliterate_hebrew(part, false))
                .collect::<Vec<String>>()
                .join(",");
            // Protect it so not adjusted in the title field
            let transliterated_word_for_title = transliterated_word.replace('ə', "~~SCHWA~~");

            // Do colourisation
            // NOTE: We have almost identical code in brightenUHB()
            //       in createParallelVersePages.py
            let mut case_class_name: Option<&'static str> = None;
            if colourise_word_classes {
                for sub_morphology in morphology.split(',') {
                    if sub_morphology.starts_with('V') {
                        case_class_name = Some("hebVrb");
                        break;
                    }
                }
                for sub_strong in strongs.split(',') {
                    // Ignores suffixes like a,b,c -- but numbers > 200 raise in
                    // BOS getSmallLeadingInt and are skipped (quirk kept)
                    let Ok(sub_strong_int) = strict_small_leading_int(sub_strong) else {
                        continue;
                    };
                    if sub_strong_int == 369 || sub_strong_int == 3808 {
                        // Hebrew 'אַיִן' 'ayin' 'no', or 'לֹא' (lo) 'not'
                        case_class_name = Some("hebNeg");
                        break;
                    }
                    if sub_strong_int == 430 || sub_strong_int == 410 || sub_strong_int == 433 {
                        // Hebrew 'אֱלֹהִים' 'ʼelohīm', 'אֵל' 'El'
                        case_class_name = Some("hebEl");
                        break;
                    }
                    if sub_strong_int == 3068 || sub_strong_int == 3050 {
                        // Hebrew 'יְהוָה' 'Yahweh', 'יָהּ' 'Yah'
                        case_class_name = Some("hebYhwh");
                        break;
                    }
                }
            }

            if let Some(class_name) = case_class_name {
                // Add a class to the anchor for the English word
                // (Allow for '#Top"' -- hence +5)
                let anchor_end_index = find_byte(&text, b'>', href_end + 5)
                    .ok_or_else(|| "ValueError: '>' not found in wordlink anchor".to_string())?;
                colourisations_added += 1;
                text = format!(
                    "{} class=\"{}\"{}",
                    &text[..anchor_end_index],
                    class_name,
                    &text[anchor_end_index..]
                );
            }

            let normalised_no_cantillations = nfc_normalise(no_cantillations);
            let new_title_guts = format!(
                "=\"{normalised_no_cantillations} ({transliterated_word_for_title}, {morphology})\""
            );
            text = format!(
                "{}{}{}",
                &text[..title_start],
                new_title_guts,
                &text[title_end..]
            );

            transliterations_added += 1;
        }
    }

    if transliterations_added > 0 || colourisations_added > 0 {
        Ok(TitlePostprocess::Updated {
            text,
            transliterations_added,
            colourisations_added,
        })
    } else {
        Ok(TitlePostprocess::NoTitleMatches)
    }
}

// ── Berean-compatible ESFM wordlink livening ────────────────────────────────

/// Liven the `word¦number` links in one entry's text exactly like
/// ESFMBible.livenESFMWordLinks does (this is the port of the nested
/// `livenESFMCompatibleBereanWordLinks` inner function body).
///
/// Returns `Ok(Some(new_text))` when links were added, `Ok(None)` when no
/// link could be made (the Python caller logs a critical message and keeps
/// the original entry), or `Err(message)` on assertion failures.
///
/// `column_names` are the word-table column names used to substitute
/// `«ColumnName»` placeholders in `title_template`; `get_row` fetches rows.
pub fn liven_berean_text(
    original_text: &str,
    bbb: &str,
    link_template: &str,
    title_template: Option<&str>,
    column_names: &[String],
    get_row: &dyn Fn(i64) -> Result<String, String>,
) -> Result<Option<String>, String> {
    if !link_template.contains("{n}") {
        return Err("AssertionError: '{n}' missing from linkTemplate".to_string());
    }
    // We have to temporarily make these into normal word-formation chars for
    // the regex to include them
    let mut text = original_text
        .replace("\\sup ", "SSsupP")
        .replace("\\sup*", "ESsupP");
    let mut count = 0usize;
    let mut search_start = 0usize;
    while let Some(found) = LINKED_WORD_REGEX.find_at(&text, search_start) {
        let captures = LINKED_WORD_REGEX
            .captures_at(&text, found.start())
            .ok_or_else(|| "Unable to read word-link capture groups".to_string())?;
        // Copy everything we need out of the borrow before editing the text
        let whole_start = captures.get(0).unwrap().start();
        let whole_end = captures.get(0).unwrap().end();
        let word = captures.get(1).unwrap().as_str().to_string();
        let digits = captures.get(2).unwrap().as_str().to_string();
        if !py_is_digit(&digits) {
            return Err(format!("AssertionError: bad word number '{digits}'"));
        }

        let mut title_html = match title_template {
            Some(template) => format!(
                "title=\"{}\" ",
                template
                    .replace("{W}", &word)
                    .replace("{BBB}", bbb)
                    .replace("{n}", &digits)
            ),
            None => String::new(),
        };
        if !title_html.is_empty() && title_template.is_some_and(|tt| tt.contains('«')) {
            let row_number: i64 = digits.parse().map_err(|e| format!("{e}"))?;
            let row = get_row(row_number)?;
            let row_columns: Vec<&str> = row.split('\t').collect();
            for (cc, column_name) in column_names.iter().enumerate() {
                let Some(replacement) = row_columns.get(cc) else {
                    return Err(format!(
                        "IndexError: word table row {row_number} has {} columns, needed {}",
                        row_columns.len(),
                        cc + 1
                    ));
                };
                title_html = title_html.replace(&format!("«{column_name}»"), replacement);
            }
        }
        let processed_link = link_template
            .replace("{W}", &word)
            .replace("{BBB}", bbb)
            .replace("{n}", &digits);
        text = format!(
            "{}<a {title_html}href=\"{processed_link}\">{word}</a>{}",
            &text[..whole_start],
            &text[whole_end..]
        );
        // We've added at least that many characters
        search_start = whole_end + link_template.len() + title_html.len() + 4;
        count += 1;
    }
    // Restores our 'hidden' HTML markup
    text = text.replace("SSsupP", "\\sup ").replace("ESsupP", "\\sup*");

    if count > 0 {
        Ok(Some(text))
    } else {
        Ok(None)
    }
}

// ── findOLQuoteInLV core ────────────────────────────────────────────────────

/// What `findOLQuoteInLV` should do after the core matcher ran.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum OlQuoteOutcome {
    /// Assembled HTML for the LV quote.
    Html(String),
    /// Couldn't find a starting word number; caller logs an error and
    /// returns ''.
    NoStartingWord,
}

/// Pick the first non-empty gloss field: contextual word gloss,
/// contextual morpheme glosses, morpheme glosses, then no-cantillations.
fn pick_gloss<'a>(fields: &[&'a str]) -> &'a str {
    for index in [10usize, 9, 8, 7] {
        let Some(field) = fields.get(index) else { continue };
        if !field.is_empty() {
            return field;
        }
    }
    ""
}

/// Port of the matching heart of `findOLQuoteInLV`.
///
/// * `lv_texts` are the `getOriginalText()` values of the OET-LV verse
///   entries (used only to discover a starting word number).
/// * `get_row`/`table_len` give access to the relevant word table.
/// * `log` receives `(level, message)` pairs ("critical"/"error"/"warning").
///
/// Returns `Err(message)` where the Python code asserted (AssertionError).
#[allow(clippy::too_many_arguments)]
pub fn find_ol_quote_in_lv_core(
    reference: &str,
    lv_texts: &[String],
    table_len: usize,
    get_row: &dyn Fn(i64) -> Result<String, String>,
    get_indexes: &dyn Fn(&str) -> Result<(i64, i64), String>,
    occurrence_number: i64,
    original_language_quote: &str,
    is_nt: bool,
    log: &dyn Fn(&str, &str),
) -> Result<OlQuoteOutcome, String> {
    // Find an ESFM word number that belongs with this B/C/V
    let mut word_number_str = String::new();
    for text in lv_texts {
        if text.is_empty() || !text.contains('¦') {
            continue; // no interest to us here
        }
        if word_number_str.is_empty() {
            // We only need to find one word number (preferably the first one) here
            let chars: Vec<char> = text.chars().collect();
            let ix_marker = chars.iter().position(|&c| c == '¦').unwrap_or(0);
            for increment in 1..=6 {
                // (maximum of six word-number digits)
                let Some(&character) = chars.get(ix_marker + increment) else {
                    return Err(format!(
                        "IndexError: string index out of range reading word number after ¦ in '{text}'"
                    ));
                };
                if character.is_ascii_digit() {
                    word_number_str.push(character); // Append the next digit
                } else {
                    break;
                }
            }
        }
        if !word_number_str.is_empty() {
            // we only need one
            break;
        }
    }
    if word_number_str.is_empty() {
        return Ok(OlQuoteOutcome::NoStartingWord);
    }
    let (first_word_number, last_word_number) = get_indexes(reference)?;

    // Ok, now we can try to match the given Greek/Hebrew words
    //     Note: We don't try to match punctuation, only the clean words
    let mut adjusted_quote = original_language_quote.trim().to_string();
    for punctuation in [",", ".", "?", "!", ";", ":", "—", "(", ")"] {
        adjusted_quote = adjusted_quote.replace(punctuation, "");
    }
    // Rev 15:4 after final ? is removed above
    if adjusted_quote.ends_with(" & ") {
        adjusted_quote.truncate(adjusted_quote.len() - " & ".len());
    }
    if !is_nt {
        // We use commas to separate Hebrew morphemes instead of word joiners
        adjusted_quote = adjusted_quote.replace(WJ, ",");
        // And we separate words by maqqaf
        adjusted_quote = adjusted_quote.replace(MAQAF, " ");
        adjusted_quote = adjusted_quote.replace(PASEQ, "").replace("  ", " ");
    }
    // Cleans up and copes with uW having multiple spaces
    adjusted_quote = adjusted_quote.replace("   ", " ").replace("  ", " ").trim().to_string();

    let ol_words: Vec<&str> = adjusted_quote.split(' ').collect();
    if ol_words.contains(&"") {
        return Err(format!(
            "findOLQuoteInLV: uW UTN has unexpected empty string {reference} {ol_words:?} from '{adjusted_quote}' from '{original_language_quote}'"
        ));
    }

    let mut current_occurrence_number = occurrence_number;
    let mut ol_index = 0usize;
    let mut word_number_offset: i64 = 0;
    let mut lv_english_words: Vec<String> = Vec::new();
    let mut in_gap = false;
    // Just for curiosity / debugging
    let mut match_start: Option<i64> = None;

    for word_number in first_word_number..=last_word_number {
        let ol_word = ol_words[ol_index];
        if ol_word == "&" {
            lv_english_words.push("&".to_string());
            ol_index += 1;
            if ol_index == 0 {
                log(
                    "critical",
                    &format!(
                        "findOLQuoteInLV: uW UTN has ampersand at beginning {reference} '{original_language_quote}'"
                    ),
                );
            } else if ol_index == ol_words.len() {
                log(
                    "critical",
                    &format!(
                        "findOLQuoteInLV: uW UTN has ampersand at end {reference} '{original_language_quote}'"
                    ),
                );
                break; // finished
            }
            in_gap = true;
            continue; // Pass over whatever this SR row was (i.e., sort of match the ampersand)
        }

        let fetch_row = |offset: i64| -> Result<(String, Vec<String>), String> {
            let row_str = get_row(word_number + offset)?;
            let row: Vec<String> = row_str.split('\t').map(String::from).collect();
            Ok((row_str, row))
        };
        let (mut row_str, mut row) = fetch_row(word_number_offset)?;
        if !is_nt {
            while row.get(1).map(String::as_str) == Some("seg")
                || row.get(1).is_some_and(|rt| rt.contains("note"))
            {
                // maqqaf segment/note row -- skip it
                word_number_offset += 1;
                if word_number + word_number_offset > last_word_number {
                    break;
                }
                (row_str, row) = fetch_row(word_number_offset)?;
            }
        }
        if word_number + word_number_offset > last_word_number {
            break;
        }
        if !row_str.starts_with(&format!("{reference}w")) {
            return Err(format!("AssertionError: {reference} {row_str:?}"));
        }
        let field = |index: usize| -> Result<String, String> {
            row.get(index)
                .cloned()
                .ok_or_else(|| format!("IndexError: OT/NT word-table row {row_str:?} has no field {index}"))
        };

        if is_nt {
            // This Greek word is not in the GNT text (SR/probability column)
            if field(7)? != "X" {
                continue;
            }
            // NOTE: We have to replace MODIFIER LETTER APOSTROPHE with RIGHT
            // SINGLE QUOTATION MARK to match correctly
            if field(1)?.replace('ʼ', "’") == ol_word {
                // we have a Greek word match
                if current_occurrence_number > 0 {
                    if ol_index != 0 {
                        return Err("AssertionError: expected olIndex == 0".to_string());
                    }
                    current_occurrence_number -= 1;
                }
                if current_occurrence_number == 0 {
                    // We can start matching up now
                    lv_english_words.push(field(4)?.replace(' ', "_"));
                    in_gap = false;
                    if ol_index == 0 {
                        match_start = Some(-word_number); // negative so don't get double match below
                    }
                    ol_index += 1;
                    if ol_index >= ol_words.len() {
                        break; // finished
                    }
                }
            } else if ol_index > 0 && !in_gap {
                // No problem at all if either we haven't started yet, or else
                // we're in a gap (&)
                ol_index = 0; // We started a match and then failed -- back to the beginning
                match_start = None;
            }
        } else {
            // OT
            if field(6)? == ol_word {
                // we have a Hebrew word match
                if current_occurrence_number > 0 {
                    if ol_index != 0 {
                        return Err("AssertionError: expected olIndex == 0".to_string());
                    }
                    current_occurrence_number -= 1;
                }
                if current_occurrence_number == 0 {
                    // We can start matching up now
                    // gloss = row[10] if row[10] else row[9] if row[9]
                    //           else row[8] if row[8] else row[7]
                    if row.len() <= 10 {
                        return Err(format!(
                            "IndexError: OT word-table row has only {} fields: {row_str:?}",
                            row.len()
                        ));
                    }
                    let full_row_refs: Vec<&str> = row.iter().map(String::as_str).collect();
                    let gloss = pick_gloss(&full_row_refs);
                    if gloss.is_empty() {
                        log(
                            "critical",
                            &format!("No available gloss1 for Hebrew {row_str}"),
                        );
                    }
                    lv_english_words.push(gloss.replace(' ', "_"));
                    in_gap = false;
                    if ol_index == 0 {
                        match_start = Some(-word_number); // negative so don't get double match below
                    }
                    ol_index += 1;
                    if ol_index >= ol_words.len() {
                        break; // finished
                    }
                }
            } else if ol_index > 0 && !in_gap {
                ol_index = 0; // We started a match and then failed -- back to the beginning
                match_start = None;
            }
        }
    }

    if ol_index < ol_words.len() {
        // We didn't match them all
        let mut our_words: Vec<String> = Vec::new();
        for probe_word_number in first_word_number..first_word_number + 999 {
            if probe_word_number >= table_len as i64 {
                // we must be in one of the last verses of Rev
                break;
            }
            let row_str = get_row(probe_word_number)?;
            if !row_str.starts_with(reference) {
                // gone into the next verse (note: without the 'w',
                // so segs/notes are included -- as in the original)
                break;
            }
            let row: Vec<String> = row_str.split('\t').map(String::from).collect();
            let field = |index: usize| -> Result<String, String> {
                row.get(index)
                    .cloned()
                    .ok_or_else(|| format!("IndexError: word-table row {row_str:?} has no field {index}"))
            };
            if is_nt {
                if field(7)? != "X" {
                    // This Greek word is not in the GNT text
                    continue;
                }
                if match_start == Some(-probe_word_number) {
                    match_start = Some(our_words.len() as i64); // Convert to index of these words
                }
                our_words.push(field(1)?);
            } else {
                if match_start == Some(-probe_word_number) {
                    match_start = Some(our_words.len() as i64); // Convert to index of these words
                }
                if row.len() <= 10 {
                    return Err(format!(
                        "IndexError: OT word-table row has only {} fields: {row_str:?}",
                        row.len()
                    ));
                }
                let full_row_refs: Vec<&str> = row.iter().map(String::as_str).collect();
                let gloss = pick_gloss(&full_row_refs);
                if gloss.is_empty() {
                    log("error", &format!("No available gloss2 for Hebrew {row_str}"));
                }
                our_words.push(gloss.to_string());
            }
        }
        let link = if is_nt {
            "<a href=\"#SR-GNT\">SR-GNT</a>"
        } else {
            "<a href=\"#UHB\">UHB</a>"
        };
        lv_english_words.push(format!(
            "(Some words not found in {link}: {})",
            our_words.join(" ")
        ));
        log(
            "warning",
            &format!(
                "findOLQuoteInLV unable to match {reference} '{original_language_quote}' occurrenceNumber={occurrence_number} currentOccurrenceNumber={current_occurrence_number} inGap={in_gap}\n  olWords={ol_words:?}  olIndex={ol_index}\n  ourWords={our_words:?} matchStart={match_start:?}"
            ),
        );
    }

    let assembled_html = lv_english_words.join(" ");
    if !is_nt {
        let assembled_html = assembled_html
            // Not totally sure where/why some of these have an underline
            // after the ESFM marker where a space is expected
            .replace("\\untr_", "<span class=\"untr\">")
            .replace("\\untr ", "<span class=\"untr\">")
            .replace("\\untr*", "</span>")
            .replace("\\nd_", "<span class=\"nd\">")
            .replace("\\nd ", "<span class=\"nd\">")
            .replace("\\nd*", "</span>");
        return Ok(OlQuoteOutcome::Html(assembled_html));
    }
    Ok(OlQuoteOutcome::Html(assembled_html))
}

// ── tests ───────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    const IDENTITY_NFC: fn(&str) -> String = |s| s.to_string();

    // ── getOETTidyBBB renames ───────────────────────────────────────────────

    #[test]
    fn test_tidy_renames_passthrough() {
        assert_eq!(apply_oet_tidy_renames("GEN", "", false), "GEN");
        assert_eq!(apply_oet_tidy_renames("MAT", " ", true), "MAT");
    }

    #[test]
    fn test_tidy_renames_yonah_yohan() {
        assert_eq!(apply_oet_tidy_renames("JNA", "", false), "YNA");
        assert_eq!(
            apply_oet_tidy_renames("JNA", "", true),
            "<span title=\"Yonah (which is closer to the Hebrew יוֹנָה/Yōnāh)\">YNA</span> (JNA)"
        );
        assert_eq!(apply_oet_tidy_renames("Jna", "", false), "Yna");
        assert_eq!(apply_oet_tidy_renames("JHN", "", false), "YHN");
        assert_eq!(apply_oet_tidy_renames("JOHN", "", false), "YHN");
        assert_eq!(apply_oet_tidy_renames("John", "", true),
            "<span title=\"Yohan (which is closer to the Greek Ἰωάννης/Yōannaʸs)\">Yhn</span> (Jhn)");
        assert_eq!(apply_oet_tidy_renames("Jhn", "", false), "Yhn");
    }

    #[test]
    fn test_tidy_renames_james_acts_jude() {
        assert_eq!(apply_oet_tidy_renames("JAM", "", false), "YAC");
        assert_eq!(apply_oet_tidy_renames("Jam", "", true), "Yac (Jam)");
        assert_eq!(apply_oet_tidy_renames("ACTS", "", true), "ACTs"); // no notes variant!
        assert_eq!(apply_oet_tidy_renames("ACTS", "", false), "ACTs");
        assert_eq!(apply_oet_tidy_renames("JUDE", "", false), "YUD");
        assert_eq!(apply_oet_tidy_renames("Jude", "", true),
            "<span title=\"Yudas (which is closer to the Greek Ἰούδας/Youdas)\">Yud</span> (Jud)");
    }

    #[test]
    fn test_tidy_renames_johns_with_insert_char() {
        let nnbsp = NARROW_NON_BREAK_SPACE.to_string();
        for (insert_char, sep) in [
            ("\u{202F}", "\u{202F}"),
            (" ", " "),
            ("", ""),
        ] {
            let _ = insert_char;
            assert_eq!(apply_oet_tidy_renames(&format!("1{sep}JN"), sep, false), format!("1{sep}YN"));
            assert_eq!(
                apply_oet_tidy_renames(&format!("3{sep}Jn"), sep, false),
                format!("3{sep}Yn")
            );
            assert_eq!(
                apply_oet_tidy_renames(&format!("2{sep}JHN"), sep, true),
                format!("2{sep}<span title=\"Yohan (which is closer to the Greek Ἰωάννης/Yōannaʸs)\">YHN</span> (2{sep}JHN)")
            );
            assert_eq!(
                apply_oet_tidy_renames(&format!("1{sep}Jhn"), sep, false),
                format!("1{sep}Yhn")
            );
            assert_eq!(
                apply_oet_tidy_renames(&format!("1{sep}Jhn"), sep, true),
                format!("1{sep}<span title=\"Yohan (which is closer to the Greek Ἰωάννης/Yōannaʸs)\">Yhn</span> (1{sep}Yohan or 1{sep}Jhn)")
            );
        }
        assert_eq!(
            apply_oet_tidy_renames(&format!("2{nnbsp}JN"), &nnbsp, true),
            format!("2{nnbsp}<span title=\"Yohan (which is closer to the Greek Ἰωάννης/Yōannaʸs)\">YN</span> (2{nnbsp}JN)")
        );
    }

    // ── getOETBookName ──────────────────────────────────────────────────────

    #[test]
    fn test_oet_book_name() {
        assert_eq!(oet_book_name("JOB").unwrap(), "Iyyov/(Job)");
        assert_eq!(oet_book_name("PSA").unwrap(), "Songs/(Psalms)");
        assert_eq!(oet_book_name("JNA").unwrap(), "Yonah/(Jonah)"); // JNA is Jonah's BOS code
        assert_eq!(oet_book_name("JAM").unwrap(), "Yacob/Jacob/(James)");
        assert_eq!(oet_book_name("JOS").unwrap(), "Yehoshua/(Joshua)");
        // BOS English name is plain 'Judges' (no curly quotes) so no rename hits
        assert_eq!(oet_book_name("JDG").unwrap(), "Judges");
        // JON is not a valid BOS code -> get_english_name_nr returns None
        assert!(oet_book_name("JON").is_none());
        assert!(oet_book_name("ZZZ").is_none());
    }

    // ── getBBBFromOETBookName ───────────────────────────────────────────────

    #[test]
    fn test_bbb_from_oet_book_name() {
        assert_eq!(get_bbb_from_oet_book_name_core("Yonah"), BbbLookup::Found("JNA"));
        assert_eq!(get_bbb_from_oet_book_name_core("YNA"), BbbLookup::Found("JNA"));
        assert_eq!(get_bbb_from_oet_book_name_core("2 Kings."), BbbLookup::Found("KI2"));
        assert_eq!(get_bbb_from_oet_book_name_core("3 Kings"), BbbLookup::Found("KI1"));
        assert_eq!(
            get_bbb_from_oet_book_name_core("1\u{202F}Peter."),
            BbbLookup::Found("PE1")
        );
        assert_eq!(get_bbb_from_oet_book_name_core("SongofSolomon"), BbbLookup::Found("SNG"));
        // Fallback into BibleOrgSys English names
        assert_eq!(get_bbb_from_oet_book_name_core("Matthew"), BbbLookup::Found("MAT"));
        assert_eq!(get_bbb_from_oet_book_name_core(""), BbbLookup::NotFound);
    }

    // ── wordpage filenames ──────────────────────────────────────────────────

    #[test]
    fn test_hebrew_wordpage_filename() {
        assert_eq!(
            hebrew_wordpage_filename_from_row("KI2_1:3w4\tword\t7\trest").unwrap(),
            "KI2c1v3w4.htm"
        );
        assert_eq!(
            hebrew_wordpage_filename_from_row("JNA_1:5\tseg\t2\trest").unwrap(),
            "JNAc1v5s2.htm"
        );
        assert_eq!(
            hebrew_wordpage_filename_from_row("JNA_2:1\tfootnote\t12\tr").unwrap(),
            "JNAc2v1n12.htm"
        );
        assert!(hebrew_wordpage_filename_from_row("JNA_1:5\tweird\t2\tr").is_err());
        assert!(hebrew_wordpage_filename_from_row("JNA_1:5\tseg\tx2\tr").is_err());
        assert!(hebrew_wordpage_filename_from_row("no_tabs_here").is_err());
    }

    #[test]
    fn test_greek_wordpage_filename() {
        assert_eq!(
            greek_wordpage_filename_from_row("MRK_1:1w2\tgreek\trest").unwrap(),
            "MRKc1v1w2.htm"
        );
        assert_eq!(greek_wordpage_filename_from_row("REV_22:21w1").unwrap(), "REVc22v21w1.htm");
    }

    // ── TEST_MODE preprocessing ─────────────────────────────────────────────

    #[test]
    fn test_preprocess_non_verse_entries_unchanged() {
        assert_eq!(preprocess_oet_rv_entry("c", "1", "OET-RV", &["GEN", "1", "1"]).unwrap(), None);
        assert_eq!(preprocess_oet_rv_entry("v~", "", "OET-RV", &["GEN", "1", "1"]).unwrap(), None);
    }

    #[test]
    fn test_preprocess_wraps_plain_words() {
        let result =
            preprocess_oet_rv_entry("v~", "hello world", "OET-RV", &["GEN", "1", "1"]).unwrap();
        assert_eq!(
            result.unwrap(),
            "<span class=\"noLinkYet\">hello</span> <span class=\"noLinkYet\">world</span>"
        );
    }

    #[test]
    fn test_preprocess_leaves_linked_and_special_words() {
        let result =
            preprocess_oet_rv_entry("v~", "hello ¦123 world", "OET-RV", &["GEN", "1", "1"]).unwrap();
        assert_eq!(
            result.unwrap(),
            "<span class=\"noLinkYet\">hello</span> ¦123 <span class=\"noLinkYet\">world</span>"
        );
        // Skip-set entries are left alone and Lord gets wrapped
        let result =
            preprocess_oet_rv_entry("v~", "\\nd Lord\\nd* i.e.", "OET-RV", &["GEN", "1", "1"])
                .unwrap();
        assert_eq!(
            result.unwrap(),
            "\\nd <span class=\"noLinkYet\">Lord</span>\\nd* <span class=\"noLinkYet\">i</span>.e."
        );
    }

    #[test]
    fn test_preprocess_strips_prefix_and_suffix() {
        let result =
            preprocess_oet_rv_entry("v~", "(Hello),", "OET-RV", &["GEN", "1", "1"]).unwrap();
        assert_eq!(
            result.unwrap(),
            "(<span class=\"noLinkYet\">Hello</span>),"
        );
    }

    #[test]
    fn test_preprocess_em_dash_round_trip() {
        let result =
            preprocess_oet_rv_entry("v~", "be—gone", "OET-RV", &["GEN", "1", "1"]).unwrap();
        assert_eq!(
            result.unwrap(),
            "<span class=\"noLinkYet\">be</span>—<span class=\"noLinkYet\">gone</span>"
        );
    }

    #[test]
    fn test_preprocess_exception_list_blocks_wrapping() {
        // Exact 3-tuple membership
        assert_eq!(
            preprocess_oet_rv_entry("v~", "hello world", "OET-RV", &["PSA", "18", "1"]).unwrap(),
            None
        );
        // And a verse NOT in the list still wraps
        assert!(
            preprocess_oet_rv_entry("v~", "hello", "OET-RV", &["PSA", "18", "2"])
                .unwrap()
                .is_some()
        );
    }

    #[test]
    fn test_preprocess_in_note_words_skipped() {
        let result = preprocess_oet_rv_entry(
            "v~",
            "\\x 1.2 refs\\x* Hello",
            "OET-RV",
            &["GEN", "1", "1"],
        )
        .unwrap();
        assert_eq!(
            result.unwrap(),
            "\\x 1.2 refs\\x* <span class=\"noLinkYet\">Hello</span>"
        );
    }

    #[test]
    fn test_preprocess_missing_verse_placeholder_skipped() {
        // The ◘/◙ (missing/untranslated-verse) placeholders must never be
        // alpha-checked or wrapped, even when adjacent to a footnote marker.
        let result = preprocess_oet_rv_entry(
            "v~",
            "Words here.◘\\f See note\\f*",
            "OET-RV",
            &["MAT", "1", "1"],
        )
        .unwrap();
        assert_eq!(
            result.unwrap(),
            "<span class=\"noLinkYet\">Words</span> here.◘\\f See note\\f*"
        );
    }

    #[test]
    fn test_preprocess_numbers_and_ie() {
        // '123' is left alone (digits never wrapped), but bare 'i.e' is NOT
        // protected -- the '.' suffix stripping cuts it down to 'i'. This
        // mangling is faithful to the original Python behaviour.
        let result = preprocess_oet_rv_entry("v~", "123 i.e", "OET-RV", &["GEN", "1", "1"]).unwrap();
        assert_eq!(
            result.unwrap(),
            "123 <span class=\"noLinkYet\">i</span>.e"
        );
    }

    #[test]
    fn test_preprocess_add_star_butted_to_prefix_asserts() {
        // The entry-level \add/\add* balance assert fires first (faithful):
        // '\add ' count 0 vs '\add*' count 1.
        let result =
            preprocess_oet_rv_entry("v~", "+\\add*", "OET-RV", &["GEN", "1", "1"]).unwrap_err();
        assert_eq!(
            result,
            "Bad add open/close counts in OET OET-RV GEN v~ line: 0 != 1"
        );
    }

    #[test]
    fn test_preprocess_cross_ref_butted_to_word() {
        // A cross-ref marker butted up against a following word IS skipped
        let result =
            preprocess_oet_rv_entry("v~", "refs\\x*Hello next", "OET-RV", &["GEN", "1", "1"])
                .unwrap();
        assert_eq!(
            result.unwrap(),
            "refs\\x*Hello <span class=\"noLinkYet\">next</span>"
        );
        // But a standalone word ending in \x* just gets wrapped normally
        let result =
            preprocess_oet_rv_entry("v~", "word\\x* next", "OET-RV", &["GEN", "1", "1"]).unwrap();
        assert_eq!(
            result.unwrap(),
            "<span class=\"noLinkYet\">word</span>\\x* <span class=\"noLinkYet\">next</span>"
        );
    }

    #[test]
    fn test_preprocess_add_count_imbalance_is_error() {
        assert!(
            preprocess_oet_rv_entry("v~", "\\add hello", "OET-RV", &["GEN", "1", "1"]).is_err()
        );
    }

    // ── §-title post-processing ─────────────────────────────────────────────

    fn nt_row(ref_: &str, greek: &str, lemma: &str, prob: &str, strongs: &str, role: &str, morph: &str) -> String {
        // Real NT layout: 0Ref 1GreekWord 2SRLemma 3GreekLemma 4VLTGlossWords
        //   5OETGlossWords 6GlossCaps 7Probability 8StrongsExt 9Role 10Morphology 11Tags
        format!("{ref_}\t{greek}\t{lemma}\tLEMMA\tVGLOSS\tOGLOSS\tcaps\t{prob}\t{strongs}\t{role}\t{morph}\ttags")
    }

    fn ot_row(ref_: &str, word: &str, no_cants: &str) -> String {
        // Real OT layout (19 cols, confirmed from OET-LV_OT_word_table.tsv):
        //   0Ref 1RowType 2MorphemeRowList 3LemmaRowList 4Strongs 5Morphology
        //   6Word 7NoCantillations 8MorphemeGlosses 9CtxMorphemeGlosses
        //   10WordGloss 11CtxWordGloss 12Caps 13Punct 14Order 15Insert
        //   16Role 17Nesting 18Tags
        format!("{ref_}\tword\tMR\tLR\tST\tMO\t{word}\t{no_cants}\tMG\tCMG\tWG\tCWG\tcaps\tpunct\tord\tins\trole\tnest\ttags")
    }

    fn ot_seg_row(ref_: &str) -> String {
        format!("{ref_}\tseg\tMR\tLR\tST\tMO\tSEG\tNC\tMG\tCMG\tWG\tCWG\tcaps\tpunct\tord\tins\trole\tnest\ttags")
    }

    fn make_get_row(
        rows: Vec<(i64, String)>,
    ) -> impl Fn(i64) -> Result<String, String> {
        move |number: i64| {
            rows.iter()
                .find(|(n, _)| *n == number)
                .map(|(_, r)| r.clone())
                .ok_or_else(|| format!("IndexError: no word-table row {number}"))
        }
    }

    #[test]
    fn test_postprocess_nt_basic() {
        let row = nt_row("MRK_1:1w1", "καὶ", "kai", "1", "24560", "C", "ABCDGfghi");
        let get_row = make_get_row(vec![(11, row)]);
        let text = "<a title=\"§καὶ§\" href=\"►11◄\">And</a>";
        match postprocess_word_link_titles(text, 1, true, &get_row, &IDENTITY_NFC, true).unwrap() {
            TitlePostprocess::Updated { text, transliterations_added, colourisations_added } => {
                assert_eq!(transliterations_added, 1);
                assert_eq!(colourisations_added, 1);
                // morphology[4] == 'G' -> grkGen; kai == kai -> no 'from'
                assert_eq!(
                    text,
                    "<a title=\"καὶ (kai, ABCDGfghi)\" href=\"../ref/GrkWrd/MRKc1v1w1.htm#Top\" class=\"grkGen\">And</a>"
                );
            }
            other => panic!("Expected Updated, got {other:?}"),
        }
    }

    #[test]
    fn test_postprocess_nt_from_sr_lemma() {
        let row = nt_row("MRK_1:1w1", "καὶ", "kaí", "1", "24560", "N", "None");
        let get_row = make_get_row(vec![(11, row)]);
        let text = "x<a title=\"§καὶ§\" href=\"►11◄\">And</a>y";
        match postprocess_word_link_titles(text, 2, true, &get_row, &IDENTITY_NFC, true).unwrap() {
            TitlePostprocess::Updated { text, .. } => assert_eq!(
                text,
                "x<a title=\"καὶ (kai, None) from kaí\" href=\"../../ref/GrkWrd/MRKc1v1w1.htm#Top\">And</a>y"
            ),
            other => panic!("Expected Updated, got {other:?}"),
        }
    }

    #[test]
    fn test_postprocess_nt_colour_classes() {
        for (role, strongs, morph, expected_class) in [
            ("V", "12345", "ABCDGfghi", Some("grkVrb")),
            ("N", "37560", "ABCDGfghi", Some("grkNeg")),
            ("N", "12345", "····Nomxx", Some("grkNom")), // middle-dot prefix stripped
            ("N", "12345", "None", None),
            ("N", "12345", "ABCD·fghi", None),           // middle dot at [4]
        ] {
            let row = nt_row("MRK_1:1w1", "καὶ", "kai", "1", strongs, role, morph);
            let get_row = make_get_row(vec![(11, row)]);
            let text = "<a title=\"§καὶ§\" href=\"►11◄\">And</a>";
            let outcome =
                postprocess_word_link_titles(text, 1, true, &get_row, &IDENTITY_NFC, true).unwrap();
            let TitlePostprocess::Updated { text, colourisations_added, .. } = outcome else {
                panic!("Expected Updated for {expected_class:?}");
            };
            match expected_class {
                Some(class) => {
                    assert_eq!(colourisations_added, 1, "{morph}");
                    assert!(text.contains(&format!(" class=\"{class}\"")), "{text}");
                }
                None => {
                    assert_eq!(colourisations_added, 0, "{morph}");
                    assert!(!text.contains("class=\"grk"), "{text}");
                }
            }
        }
    }

    #[test]
    fn test_postprocess_two_anchors() {
        let row1 = nt_row("MRK_1:1w1", "καὶ", "kai", "1", "24560", "C", "None");
        let row2 = nt_row("MRK_1:1w2", "δὲ", "de", "1", "11610", "C", "None");
        let get_row = make_get_row(vec![(11, row1), (12, row2)]);
        let text = "<a title=\"§καὶ§\" href=\"►11◄\">And</a> <a title=\"§δὲ§\" href=\"►12◄\">but</a>";
        let outcome = postprocess_word_link_titles(text, 1, true, &get_row, &IDENTITY_NFC, true).unwrap();
        let TitlePostprocess::Updated { text, transliterations_added, .. } = outcome else {
            panic!("Expected Updated");
        };
        assert_eq!(transliterations_added, 2);
        assert!(text.contains("(de, None)"));
        assert!(text.contains("(kai, None)"));
    }

    #[test]
    fn test_postprocess_no_colourise_skips_classes() {
        // With colourise_word_classes=false, no grammatical marker classes are
        // added to the anchors, but transliteration still happens.
        let row = nt_row("MRK_1:1w1", "καὶ", "kai", "1", "24560", "V", "ABCDGfghi");
        let get_row = make_get_row(vec![(11, row)]);
        let text = "<a title=\"§καὶ§\" href=\"►11◄\">And</a>";
        let outcome =
            postprocess_word_link_titles(text, 1, true, &get_row, &IDENTITY_NFC, false).unwrap();
        let TitlePostprocess::Updated { text, transliterations_added, colourisations_added } =
            outcome
        else {
            panic!("Expected Updated");
        };
        assert_eq!(transliterations_added, 1);
        assert_eq!(colourisations_added, 0);
        assert!(!text.contains("class=\"grk"), "{text}");
        assert!(text.contains("(kai, ABCDGfghi)"), "{text}");
    }

    #[test]
    fn test_postprocess_ot_basic() {
        let row = ot_row("GEN_1:1w2", "WORD", "הָאָרֶץ").replacen("\tMO\t", "\tV-qwc-3ms\t", 1);
        let get_row = make_get_row(vec![(21, row)]);
        let text = "<a title=\"§הָאָרֶץ§\" href=\"►21◄\">earth</a>";
        match postprocess_word_link_titles(text, 1, false, &get_row, &IDENTITY_NFC, true).unwrap() {
            TitlePostprocess::Updated { text, transliterations_added, colourisations_added } => {
                assert_eq!(transliterations_added, 1);
                assert_eq!(colourisations_added, 1); // verb morphology
                assert!(text.starts_with("<a title=\""), "{text}");
                assert!(text.contains("../ref/HebWrd/GENc1v1w2.htm#Top"), "{text}");
                assert!(text.contains("class=\"hebVrb\""), "{text}");
            }
            other => panic!("Expected Updated, got {other:?}"),
        }
    }

    #[test]
    fn test_postprocess_ot_strongs_over_200_never_colours() {
        // Faithful quirk: BOS getSmallLeadingInt raises above 200, so
        // '3068' can never trigger the hebYhwh class
        for strongs in ["3068", "3808", "430", "H3068"] {
            let row = ot_row("GEN_1:1w2", "WORD", "x")
                .replacen("\tST\t", &format!("\t{strongs}\t"), 1);
            let get_row = make_get_row(vec![(21, row)]);
            let text = "<a title=\"§הָאָרֶץ§\" href=\"►21◄\">earth</a>";
            let outcome =
                postprocess_word_link_titles(text, 1, false, &get_row, &IDENTITY_NFC, true).unwrap();
            let TitlePostprocess::Updated { text, colourisations_added, .. } = outcome else {
                panic!("Expected Updated");
            };
            assert_eq!(colourisations_added, 0, "{strongs}");
            assert!(!text.contains("hebNeg"), "{text}");
        }
    }

    #[test]
    fn test_postprocess_ot_schwa_protection() {
        // No Hebrew characters means transliteration returns input unchanged,
        // so we can predictably test the schwa protection
        let row = ot_row("GEN_1:1w2", "WORD", "əə").replacen("\tMO\t", "\tN-x\t", 1);
        let get_row = make_get_row(vec![(21, row)]);
        let text = "<a title=\"§x§\" href=\"►21◄\">earth</a>";
        let outcome = postprocess_word_link_titles(text, 1, false, &get_row, &IDENTITY_NFC, true).unwrap();
        let TitlePostprocess::Updated { text, .. } = outcome else { panic!() };
        assert!(text.contains("(~~SCHWA~~~~SCHWA~~, N-x)"), "{text}");
    }

    #[test]
    fn test_postprocess_no_title_matches() {
        let get_row = make_get_row(vec![]);
        let outcome = postprocess_word_link_titles("plain § text", 1, true, &get_row, &IDENTITY_NFC, true).unwrap();
        assert_eq!(outcome, TitlePostprocess::NoTitleMatches);
    }

    #[test]
    fn test_postprocess_missing_href_is_error() {
        let get_row = make_get_row(vec![]);
        assert!(
            postprocess_word_link_titles("<a title=\"§καὶ§\"", 1, true, &get_row, &IDENTITY_NFC, true)
                .is_err()
        );
    }

    #[test]
    fn test_postprocess_bad_gap_is_error() {
        let get_row = make_get_row(vec![]);
        // Gap of 4 ('href') -- must fail the ==5 assert
        assert!(
            postprocess_word_link_titles(
                "<a title=\"§καὶ§\"href=\"►11◄\"",
                1, true, &get_row, &IDENTITY_NFC, true
            )
            .is_err()
        );
    }

    // ── Berean-compatible livening ──────────────────────────────────────────

    #[test]
    fn test_liven_berean_basic() {
        // NOTE: because the title template contains '«', livenESFMWordLinks
        // fetches the word-table row even though 'OrigWord' is not a real
        // column -- so the row must exist (faithful behaviour).
        let row = "MRK_1:1w2\tκόσμος\tworld".to_string();
        let get_row = make_get_row(vec![(12, row)]);
        let result = liven_berean_text(
            "word¦12 rest",
            "MRK",
            "►{n}◄",
            Some("§«OrigWord»§"),
            &[],
            &get_row,
        )
        .unwrap();
        assert_eq!(
            result.unwrap(),
            "<a title=\"§«OrigWord»§\" href=\"►12◄\">word</a> rest"
        );
    }

    #[test]
    fn test_liven_berean_column_substitution() {
        let row = "GEN_1:1w1\tבְּרֵאשִׁית\tbeginning".to_string();
        let get_row = make_get_row(vec![(5, row)]);
        let columns = vec!["ref".to_string(), "word".to_string(), "gloss".to_string()];
        let result = liven_berean_text(
            "In-the-beginning¦5",
            "GEN",
            "►{n}◄",
            Some("«word» (§«OrigWord»§)"),
            &columns,
            &get_row,
        )
        .unwrap();
        assert_eq!(
            result.unwrap(),
            "<a title=\"בְּרֵאשִׁית (§«OrigWord»§)\" href=\"►5◄\">In-the-beginning</a>"
        );
    }

    #[test]
    fn test_liven_berean_sup_hiding_round_trip() {
        let get_row = make_get_row(vec![]);
        let result = liven_berean_text(
            "\\sup x\\sup*y¦13",
            "MRK",
            "►{n}◄",
            None,
            &[],
            &get_row,
        )
        .unwrap();
        assert_eq!(
            result.unwrap(),
            "<a href=\"►13◄\">\\sup x\\sup*y</a>"
        );
    }

    #[test]
    fn test_liven_berean_no_links_found() {
        let get_row = make_get_row(vec![]);
        assert_eq!(
            liven_berean_text("plain text", "MRK", "►{n}◄", None, &[], &get_row).unwrap(),
            None
        );
        assert_eq!(
            liven_berean_text("bad¦0 number", "MRK", "►{n}◄", None, &[], &get_row).unwrap(),
            None // '0' doesn't match [1-9]…
        );
    }

    #[test]
    fn test_liven_berean_requires_n_placeholder() {
        let get_row = make_get_row(vec![]);
        assert!(liven_berean_text("x¦1", "MRK", "no-placeholder", None, &[], &get_row).is_err());
    }

    // ── findOLQuoteInLV core ────────────────────────────────────────────────


        fn make_get_indexes(first: i64, last: i64) -> impl Fn(&str) -> Result<(i64, i64), String> {
            move |_reference| Ok((first, last))
        }

    #[test]
    fn test_find_ol_quote_nt_simple_match() {
        let texts = vec!["v~=and¦11 says¦12".to_string()];
        let row11 = nt_row("MRK_1:1w1", "καὶ", "kai", "X", "24560", "C", "None")
            .replacen("\tVGLOSS\t", "\tand\t", 1);
        let row12 = nt_row("MRK_1:1w2", "ἀρχή", "arch", "X", "7460", "N", "None");
        let rows = [(11usize, row11), (12, row12)];
        let get_row = |n: i64| {
            rows.iter()
                .find(|(rn, _)| *rn == n as usize)
                .map(|(_, r)| r.clone())
                .ok_or_else(|| format!("no row {n}"))
        };
        let no_log = |_level: &str, _message: &str| {};
        // Trailing comma is cleaned off before matching
        let outcome = find_ol_quote_in_lv_core(
            "MRK_1:1", &texts, 20, &get_row,&make_get_indexes(11, 12), 0, "καὶ,", true, &no_log,
        )
        .unwrap();
        assert_eq!(outcome, OlQuoteOutcome::Html("and".to_string()));
    }

    #[test]
    fn test_find_ol_quote_nt_occurrence_skipping() {
        let texts = vec!["v~=and¦11 and¦12".to_string()];
        let row11 = nt_row("MRK_1:1w1", "καὶ", "kai", "X", "24560", "C", "None");
        let row12 = nt_row("MRK_1:1w2", "καὶ", "kai", "X", "25320", "C", "None");
        // Different glosses so we can tell which matched
        let row11 = row11.replacen("\tVGLOSS\t", "\tfirst\t", 1);
        let row12 = row12.replacen("\tVGLOSS\t", "\tsecond\t", 1);
        let rows = [(11usize, row11), (12, row12)];
        let get_row = |n: i64| {
            rows.iter()
                .find(|(rn, _)| *rn == n as usize)
                .map(|(_, r)| r.clone())
                .ok_or_else(|| format!("no row {n}"))
        };
        let no_log = |_level: &str, _message: &str| {};
        // Faithful quirk: the original decrements and then accepts in the
        // same iteration, so occurrenceNumber<=1 takes the FIRST match and
        // occurrenceNumber=2 is what skips to the second one.
        let outcome = find_ol_quote_in_lv_core(
            "MRK_1:1", &texts, 20, &get_row,&make_get_indexes(11, 12), 2, "καὶ", true, &no_log,
        )
        .unwrap();
        assert_eq!(outcome, OlQuoteOutcome::Html("second".to_string()));
        let outcome_first = find_ol_quote_in_lv_core(
            "MRK_1:1", &texts, 20, &get_row,&make_get_indexes(11, 12), 1, "καὶ", true, &no_log,
        )
        .unwrap();
        assert_eq!(outcome_first, OlQuoteOutcome::Html("first".to_string()));
    }

    #[test]
    fn test_find_ol_quote_ampersand_gap() {
        let texts = vec!["v~=and¦11 coming¦12 going¦13".to_string()];
        let row11 = nt_row("MRK_1:1w1", "καὶ", "kai", "X", "24560", "C", "None")
            .replacen("\tVGLOSS\t", "\tand\t", 1);
        let row12 = nt_row("MRK_1:1w2", "σάρξ", "sarx", "X", "45610", "N", "None")
            .replacen("\tVGLOSS\t", "\tflesh\t", 1);
        let row13 = nt_row("MRK_1:1w3", "ἔρχονται", "erchontai", "X", "20640", "V", "None")
            .replacen("\tVGLOSS\t", "\tcoming\t", 1);
        let rows = [(11usize, row11), (12, row12), (13, row13)];
        let get_row = |n: i64| {
            rows.iter()
                .find(|(rn, _)| *rn == n as usize)
                .map(|(_, r)| r.clone())
                .ok_or_else(|| format!("no row {n}"))
        };
        let no_log = |_level: &str, _message: &str| {};
        let outcome = find_ol_quote_in_lv_core(
            "MRK_1:1", &texts, 20, &get_row,&make_get_indexes(11, 13), 0, "καὶ & ἔρχονται.", true, &no_log,
        )
        .unwrap();
        assert_eq!(outcome, OlQuoteOutcome::Html("and & coming".to_string()));
    }

    #[test]
    fn test_find_ol_quote_unmatched_fallback() {
        let texts = vec!["v~=something¦11 else¦12".to_string()];
        let row11 = nt_row("MRK_1:1w1", "καὶ", "kai", "X", "24560", "C", "None");
        let row12 = nt_row("MRK_1:1w2", "λέγει", "legei", "X", "30040", "V", "None");
        let row13 = nt_row("MRK_1:1w3", "ἀρχή", "arch", "X", "7460", "N", "None");
        // Next verse -- this is what stops the fallback scan
        let row14 = nt_row("MRK_1:2w1", "εὐθύς", "euthus", "X", "21170", "D", "None");
        let rows = [(11usize, row11), (12, row12), (13, row13), (14, row14)];
        let get_row = |n: i64| {
            rows.iter()
                .find(|(rn, _)| *rn == n as usize)
                .map(|(_, r)| r.clone())
                .ok_or_else(|| format!("no row {n}"))
        };
        let messages: std::cell::RefCell<Vec<(String, String)>> = std::cell::RefCell::new(vec![]);
        let log = |level: &str, message: &str| {
            messages.borrow_mut().push((level.to_string(), message.to_string()));
        };
        let outcome = find_ol_quote_in_lv_core(
            "MRK_1:1", &texts, 20, &get_row,&make_get_indexes(11, 12), 0, "ζαρίᾱ", true, &log,
        )
        .unwrap();
        let OlQuoteOutcome::Html(html) = outcome else { panic!() };
        assert!(
            html.contains(
                "(Some words not found in <a href=\"#SR-GNT\">SR-GNT</a>: καὶ λέγει ἀρχή)"
            ),
            "{html}"
        );
        assert!(messages.borrow().iter().any(|(level, _)| level == "warning"));
    }

    #[test]
    fn test_find_ol_quote_ot_seg_skipping() {
        let texts = vec!["v~=word¦5 stuff¦7".to_string()];
        // Match target is field 6 (Word); gloss chain prefers field 10 (WordGloss)
        let row5 = ot_row("GEN_1:1w1", "bereshit", "b")
            .replacen("\tWG\t", "\tin-the-beginning\t", 1);
        // A segment row between the two words
        let row6 = ot_seg_row("GEN_1:1");
        let row7 = ot_row("GEN_1:1w2", "barah", "b")
            .replacen("\tWG\t", "\tcreated\t", 1);
        let rows = [(5usize, row5), (6, row6), (7, row7)];
        let get_row = |n: i64| {
            rows.iter()
                .find(|(rn, _)| *rn == n as usize)
                .map(|(_, r)| r.clone())
                .ok_or_else(|| format!("no row {n}"))
        };
        let no_log = |_level: &str, _message: &str| {};
        let outcome = find_ol_quote_in_lv_core(
            "GEN_1:1", &texts, 20, &get_row,&make_get_indexes(5, 7), 0, "bereshit & barah", false, &no_log,
        )
        .unwrap();
        assert_eq!(
            outcome,
            OlQuoteOutcome::Html("in-the-beginning & created".to_string())
        );
    }

    #[test]
    fn test_find_ol_quote_no_starting_word() {
        let texts = vec!["v~nothing here".to_string()];
        let get_row = make_get_row(vec![]);
        let no_log = |_level: &str, _message: &str| {};
        let outcome = find_ol_quote_in_lv_core(
            "MRK_1:1", &texts, 20, &get_row,&make_get_indexes(11, 12), 0, "καὶ", true, &no_log,
        )
        .unwrap();
        assert_eq!(outcome, OlQuoteOutcome::NoStartingWord);
    }

    #[test]
    fn test_find_ol_quote_empty_quote_rejected() {
        let texts = vec!["v~=x¦11".to_string()];
        let get_row = make_get_row(vec![]);
        let no_log = |_level: &str, _message: &str| {};
        // A pure-punctuation quote cleans down to '' → assertion error
        assert!(find_ol_quote_in_lv_core(
            "MRK_1:1", &texts, 20, &get_row,&make_get_indexes(11, 12), 0, ";", true, &no_log,
        )
        .is_err());
    }

    #[test]
    fn test_find_ol_quote_wrong_reference_row_is_error() {
        let texts = vec!["v~=x¦11".to_string()];
        // Rows belong to a different verse entirely
        let row = nt_row("LUK_9:9w1", "καὶ", "kai", "X", "1", "C", "None");
        let get_row = make_get_row(vec![(11, row)]);
        let no_log = |_level: &str, _message: &str| {};
        assert!(find_ol_quote_in_lv_core(
            "MRK_1:1", &texts, 20, &get_row,&make_get_indexes(11, 12), 0, "καὶ", true, &no_log,
        )
        .is_err());
    }
}
