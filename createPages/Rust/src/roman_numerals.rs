//! Conversion from integers/strings to Roman numerals.

const ROMAN_NUMERALS: &[(u32, &str)] = &[
    (1000, "M"),
    (900, "CM"),
    (500, "D"),
    (400, "CD"),
    (100, "C"),
    (90, "XC"),
    (50, "L"),
    (40, "XL"),
    (10, "X"),
    (9, "IX"),
    (5, "V"),
    (4, "IV"),
    (1, "I"),
];

/// Convert a non-negative integer into Roman numerals string.
///
/// Returns an empty string for 0.
pub fn to_roman_numerals(mut num: u32) -> String {
    let mut result = String::new();
    for &(value, numeral) in ROMAN_NUMERALS {
        if num == 0 {
            break;
        }
        let count = num / value;
        if count > 0 {
            for _ in 0..count {
                result.push_str(numeral);
            }
            num %= value;
        }
    }
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_to_roman_numerals_basic() {
        assert_eq!(to_roman_numerals(0), "");
        assert_eq!(to_roman_numerals(1), "I");
        assert_eq!(to_roman_numerals(2), "II");
        assert_eq!(to_roman_numerals(3), "III");
        assert_eq!(to_roman_numerals(4), "IV");
        assert_eq!(to_roman_numerals(5), "V");
        assert_eq!(to_roman_numerals(6), "VI");
        assert_eq!(to_roman_numerals(7), "VII");
        assert_eq!(to_roman_numerals(8), "VIII");
        assert_eq!(to_roman_numerals(9), "IX");
        assert_eq!(to_roman_numerals(10), "X");
    }

    #[test]
    fn test_to_roman_numerals_tens_and_hundreds() {
        assert_eq!(to_roman_numerals(14), "XIV");
        assert_eq!(to_roman_numerals(19), "XIX");
        assert_eq!(to_roman_numerals(20), "XX");
        assert_eq!(to_roman_numerals(40), "XL");
        assert_eq!(to_roman_numerals(49), "XLIX");
        assert_eq!(to_roman_numerals(50), "L");
        assert_eq!(to_roman_numerals(88), "LXXXVIII");
        assert_eq!(to_roman_numerals(90), "XC");
        assert_eq!(to_roman_numerals(99), "XCIX");
        assert_eq!(to_roman_numerals(100), "C");
        assert_eq!(to_roman_numerals(119), "CXIX");
        assert_eq!(to_roman_numerals(150), "CL");
        assert_eq!(to_roman_numerals(151), "CLI");
        assert_eq!(to_roman_numerals(3999), "MMMCMXCIX");
    }
}
