//! Hebrew/Greek text-cleaning helpers ported from the hot inner Python loops
//! in `BibleOrgSys/OriginalLanguages/Hebrew.py` and `Greek.py`.
//!
//! Each function is a byte-identical port of the corresponding Python method
//! (which previously used O(marks × text) `str.replace` chains — Python has
//! since been optimised to `str.translate`; these Rust ports match that
//! output exactly).

/// Remove all characters in `chars` from `text`.
fn strip_chars(text: &str, chars: &[char]) -> String {
    text.chars().filter(|c| !chars.contains(c)).collect()
}

const METEG_OR_SILUQ: char = '\u{5bd}';
const PATAH: char = '\u{5b7}';
const SEGOL: char = '\u{5b6}';

const CANTILLATION_MARKS: &[char] = &['\u{591}', '\u{592}', '\u{593}', '\u{594}', '\u{595}', '\u{596}', '\u{597}', '\u{598}', '\u{599}', '\u{59a}', '\u{59b}', '\u{59c}', '\u{59d}', '\u{59e}', '\u{59f}', '\u{5a0}', '\u{5a1}', '\u{5a2}', '\u{5a3}', '\u{5a4}', '\u{5a5}', '\u{5a6}', '\u{5a7}', '\u{5a8}', '\u{5a9}', '\u{5aa}', '\u{5ab}', '\u{5ac}', '\u{5ad}', '\u{5ae}', '\u{5af}'];
const VOWEL_POINTS: &[char] = &['\u{5b0}', '\u{5b1}', '\u{5b2}', '\u{5b3}', '\u{5b4}', '\u{5b5}', '\u{5b6}', '\u{5b7}', '\u{5b8}', '\u{5b9}', '\u{5ba}', '\u{5bb}'];
const OTHER_MARKS: &[char] = &['\u{5bc}', '\u{5bf}', '\u{5c0}', '\u{5c1}', '\u{5c2}', '\u{5c4}', '\u{5c5}', '\u{5c7}'];
const SIN_DOT: char = '\u{5c2}';
const SHIN_DOT: char = '\u{5c1}';

/// Byte-identical port of `Hebrew._removeMetegOrSiluq`.
///
/// Scans for `metegOrSiluq` marks; a mark immediately after patah or segol is
/// treated as a vowel-point meteg (removed when `as_vowel` is true, kept
/// otherwise); any other meteg/siluq is treated as a cantillation mark
/// (removed when `as_vowel` is false, kept otherwise).
fn remove_meteg_or_siluq(text: &str, as_vowel: bool) -> String {
    let mut chars: Vec<char> = text.chars().collect();
    loop {
        let mut made_changes = false;
        let mut j = 0;
        while j < chars.len() {
            if chars[j] != METEG_OR_SILUQ {
                j += 1;
                continue;
            }
            let previous_mark = if j > 0 { chars[j - 1] } else { '\u{0}' };
            if previous_mark == PATAH || previous_mark == SEGOL {
                if as_vowel {
                    chars.remove(j);
                    made_changes = true;
                    break;
                }
            } else if !as_vowel {
                chars.remove(j);
                made_changes = true;
                break;
            }
            j += 1;
        }
        if !made_changes {
            break;
        }
    }
    chars.into_iter().collect()
}

/// Byte-identical port of `Hebrew.removeCantillationMarks`.
pub fn remove_hebrew_cantillation_marks(text: &str, remove_meteg_or_siluq_marks: bool) -> String {
    let adjusted = if remove_meteg_or_siluq_marks {
        remove_meteg_or_siluq(text, false)
    } else {
        text.to_string()
    };
    strip_chars(&adjusted, CANTILLATION_MARKS)
}

/// Byte-identical port of `Hebrew.removeVowelPointing`.
pub fn remove_hebrew_vowel_pointing(text: &str, remove_meteg_or_siluq_marks: bool) -> String {
    let adjusted = if remove_meteg_or_siluq_marks {
        remove_meteg_or_siluq(text, true)
    } else {
        text.to_string()
    };
    strip_chars(&adjusted, VOWEL_POINTS)
}

/// Byte-identical port of `Hebrew.removeOtherMarks`.
pub fn remove_hebrew_other_marks(text: &str, remove_sin_shin_dots: bool) -> String {
    let no_meteg = strip_chars(text, &[METEG_OR_SILUQ]);
    if remove_sin_shin_dots {
        strip_chars(&no_meteg, OTHER_MARKS)
    } else {
        no_meteg
            .chars()
            .filter(|c| !OTHER_MARKS.contains(c) || *c == SIN_DOT || *c == SHIN_DOT)
            .collect()
    }
}

/// Byte-identical port of `Greek.removeAccents`.
pub fn strip_greek_accents(text: &str) -> String {
    let mut result = String::with_capacity(text.len());
    for c in text.chars() {
        match c {
                                '\u{1fbd}' => result.push_str(""),
                '\u{301}' => result.push_str(""),
                '\u{1f08}' => result.push_str("Α"),
                '\u{1f0c}' => result.push_str("Α"),
                '\u{1f0e}' => result.push_str("Α"),
                '\u{1f09}' => result.push_str("Α"),
                '\u{1f0d}' => result.push_str("Α"),
                '\u{1f0b}' => result.push_str("Α"),
                '\u{1f8d}' => result.push_str("Α"),
                '\u{3ac}' => result.push_str("α"),
                '\u{1f71}' => result.push_str("α"),
                '\u{1f70}' => result.push_str("α"),
                '\u{1f00}' => result.push_str("α"),
                '\u{1f01}' => result.push_str("α"),
                '\u{1fb3}' => result.push_str("α"),
                '\u{1f04}' => result.push_str("α"),
                '\u{1fb6}' => result.push_str("α"),
                '\u{1f05}' => result.push_str("α"),
                '\u{1f03}' => result.push_str("α"),
                '\u{1f06}' => result.push_str("α"),
                '\u{1f02}' => result.push_str("α"),
                '\u{1fb7}' => result.push_str("α"),
                '\u{1f85}' => result.push_str("α"),
                '\u{1fb4}' => result.push_str("α"),
                '\u{1f84}' => result.push_str("α"),
                '\u{3ad}' => result.push_str("ε"),
                '\u{1f72}' => result.push_str("ε"),
                '\u{1f10}' => result.push_str("ε"),
                '\u{1f11}' => result.push_str("ε"),
                '\u{1f14}' => result.push_str("ε"),
                '\u{1f13}' => result.push_str("ε"),
                '\u{1f15}' => result.push_str("ε"),
                '\u{3ae}' => result.push_str("η"),
                '\u{1f74}' => result.push_str("η"),
                '\u{1f21}' => result.push_str("η"),
                '\u{1fc6}' => result.push_str("η"),
                '\u{1f26}' => result.push_str("η"),
                '\u{1fc7}' => result.push_str("η"),
                '\u{1f24}' => result.push_str("η"),
                '\u{1fc3}' => result.push_str("η"),
                '\u{1f20}' => result.push_str("η"),
                '\u{1f25}' => result.push_str("η"),
                '\u{1f94}' => result.push_str("η"),
                '\u{1f22}' => result.push_str("η"),
                '\u{1f96}' => result.push_str("η"),
                '\u{1f90}' => result.push_str("η"),
                '\u{1f97}' => result.push_str("η"),
                '\u{1f27}' => result.push_str("η"),
                '\u{1f23}' => result.push_str("η"),
                '\u{1fc4}' => result.push_str("η"),
                '\u{1f91}' => result.push_str("η"),
                '\u{3af}' => result.push_str("ι"),
                '\u{1f77}' => result.push_str("ι"),
                '\u{1f76}' => result.push_str("ι"),
                '\u{1f30}' => result.push_str("ι"),
                '\u{1f31}' => result.push_str("ι"),
                '\u{1fd6}' => result.push_str("ι"),
                '\u{1f37}' => result.push_str("ι"),
                '\u{1f36}' => result.push_str("ι"),
                '\u{390}' => result.push_str("ι"),
                '\u{1fd2}' => result.push_str("ι"),
                '\u{1f35}' => result.push_str("ι"),
                '\u{1f34}' => result.push_str("ι"),
                '\u{1f33}' => result.push_str("ι"),
                '\u{3ca}' => result.push_str("ι"),
                '\u{1fd3}' => result.push_str("ι"),
                '\u{3cc}' => result.push_str("ο"),
                '\u{1f78}' => result.push_str("ο"),
                '\u{1f40}' => result.push_str("ο"),
                '\u{1f41}' => result.push_str("ο"),
                '\u{1f43}' => result.push_str("ο"),
                '\u{1f45}' => result.push_str("ο"),
                '\u{1f44}' => result.push_str("ο"),
                '\u{1f42}' => result.push_str("ο"),
                '\u{3ce}' => result.push_str("ω"),
                '\u{1f7c}' => result.push_str("ω"),
                '\u{1f60}' => result.push_str("ω"),
                '\u{1f61}' => result.push_str("ω"),
                '\u{1ff6}' => result.push_str("ω"),
                '\u{1ff7}' => result.push_str("ω"),
                '\u{1ff3}' => result.push_str("ω"),
                '\u{1fa7}' => result.push_str("ω"),
                '\u{1f65}' => result.push_str("ω"),
                '\u{1f66}' => result.push_str("ω"),
                '\u{1f67}' => result.push_str("ω"),
                '\u{1ff4}' => result.push_str("ω"),
                '\u{1f64}' => result.push_str("ω"),
                '\u{1fa0}' => result.push_str("ω"),
                '\u{1f62}' => result.push_str("ω"),
                '\u{3cd}' => result.push_str("υ"),
                '\u{1f7a}' => result.push_str("υ"),
                '\u{1f50}' => result.push_str("υ"),
                '\u{1f51}' => result.push_str("υ"),
                '\u{1fe6}' => result.push_str("υ"),
                '\u{1f55}' => result.push_str("υ"),
                '\u{1f56}' => result.push_str("υ"),
                '\u{1f57}' => result.push_str("υ"),
                '\u{3cb}' => result.push_str("υ"),
                '\u{1f53}' => result.push_str("υ"),
                '\u{1f54}' => result.push_str("υ"),
                '\u{1f52}' => result.push_str("υ"),
                '\u{3b0}' => result.push_str("υ"),
                '\u{1fe2}' => result.push_str("υ"),
                '\u{1fe5}' => result.push_str("ρ"),
                _ => result.push(c),
        }
    }
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_strip_greek_accents() {
        assert_eq!(strip_greek_accents("λόγος"), "λογος");
        assert_eq!(strip_greek_accents("Ἀρχὴ"), "Αρχη");
        assert_eq!(strip_greek_accents(""), "");
    }

    #[test]
    fn test_remove_hebrew_cantillation_marks() {
        assert!(!remove_hebrew_cantillation_marks("בְּרֵאשִׁ֖ית", false).contains('\u{591}'));
    }

    #[test]
    fn test_remove_hebrew_vowel_pointing() {
        assert_eq!(remove_hebrew_vowel_pointing("בְּרֵאשִׁ֖ית", false), "בְּרֵאשִׁ֖ית".chars().filter(|c| !['\u{5b0}','\u{5b1}','\u{5b2}','\u{5b3}','\u{5b4}','\u{5b5}','\u{5b6}','\u{5b7}','\u{5b8}','\u{5b9}','\u{5ba}','\u{5bb}'].contains(c)).collect::<String>());
    }

    #[test]
    fn test_remove_hebrew_other_marks_keeps_sin_shin_dots() {
        // Shin dot (U+5C1) and sin dot (U+5C2) must be kept when remove_sin_shin_dots=false
        let text = "שְׁנַ֣ת";
        let stripped = remove_hebrew_other_marks(text, false);
        assert!(stripped.contains('\u{5c1}'));
        let stripped_all = remove_hebrew_other_marks(text, true);
        assert!(!stripped_all.contains('\u{5c1}'));
    }
}
