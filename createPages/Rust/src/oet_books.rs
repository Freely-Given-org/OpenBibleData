//! Book code lookup utilities matching OpenBibleData conventions.

/// Look up BBB 3-letter code from OET custom book names table.
pub fn get_oet_bbb(uppered_name: &str) -> Option<&'static str> {
    match uppered_name {
        "1SAMUEL" => Some("SA1"),
        "2SAMUEL" => Some("SA2"),
        "1KINGS" => Some("KI1"),
        "2KINGS" => Some("KI2"),
        "3KINGS" => Some("KI1"),
        "4KINGS" => Some("KI2"),
        "1CHRONICLES" => Some("CH1"),
        "2CHRONICLES" => Some("CH2"),
        "YOB" => Some("JOB"),
        "SONGOFSOLOMON" => Some("SNG"),
        "YESHAYAH" => Some("ISA"),
        "YIRMEYAH" => Some("JER"),
        "YONAH" | "YNA" => Some("JNA"),
        "YOEL" => Some("JOL"),
        "YOCHANAN" | "YHN" => Some("JHN"),
        "1CORINTHIANS" => Some("CO1"),
        "2CORINTHIANS" => Some("CO2"),
        "1TIMOTHY" => Some("TI1"),
        "2TIMOTHY" => Some("TI2"),
        "1THESSALONIANS" => Some("TH1"),
        "2THESSALONIANS" => Some("TH2"),
        "YAC" => Some("JAM"),
        "1PETER" => Some("PE1"),
        "2PETER" => Some("PE2"),
        "1YHN" => Some("JN1"),
        "2YHN" => Some("JN2"),
        "3YHN" => Some("JN3"),
        "YUD" => Some("JDE"),
        "2PS" => Some("PS2"),
        _ => None,
    }
}

/// Convert an original book name string to a 3-character BOS Book Code (BBB).
///
/// Removes spaces, narrow non-breaking spaces, and periods, then checks the OET
/// table and falls back to BibleOrgSys book code mappings.
pub fn get_bbb_from_oet_book_name(original_book_name: &str) -> Option<&'static str> {
    let uppered: String = original_book_name
        .chars()
        .filter(|&c| c != ' ' && c != '\u{202F}' && c != '.')
        .flat_map(|c| c.to_uppercase())
        .collect();

    if let Some(bbb) = get_oet_bbb(&uppered) {
        return Some(bbb);
    }

    if let Some(bbb) = bos_books_codes::english_name_to_bos_book_code(&uppered) {
        if bos_books_codes::is_valid_bos_book_code(bbb) {
            return Some(bbb);
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_get_bbb_from_oet_book_name() {
        assert_eq!(get_bbb_from_oet_book_name("Acts"), Some("ACT"));
        assert_eq!(get_bbb_from_oet_book_name("Col."), Some("COL"));
        assert_eq!(get_bbb_from_oet_book_name("1 Peter"), Some("PE1"));
        assert_eq!(get_bbb_from_oet_book_name("1Peter"), Some("PE1"));
        assert_eq!(get_bbb_from_oet_book_name("1 Peter."), Some("PE1"));
        assert_eq!(get_bbb_from_oet_book_name("Matt"), Some("MAT"));
        assert_eq!(get_bbb_from_oet_book_name("Matthew"), Some("MAT"));
        assert_eq!(get_bbb_from_oet_book_name("Yonah"), Some("JNA"));
        assert_eq!(get_bbb_from_oet_book_name("Song of Solomon"), Some("SNG"));
        assert_eq!(get_bbb_from_oet_book_name("UnknownBook"), None);
    }
}
