//! Per-word helpers ported from `createOETReferencePages`.
//!
//! These pure string/table helpers used to run once per word-form row (word
//! pages, lemma pages, app JSON files — ~78K Hebrew words and ~12K Greek
//! words in a full build):
//!
//!   * `tidy_hebrew_morphology` — turn an OSHB morphology code (like `Nc2ms`)
//!     into the "<small>Morphology=…</small> PoS=<b>…</b>" HTML, with UHG
//!     grammar-page links (from `createOETReferencePages.tidy_Hebrew_morphology`).
//!   * `format_nt_spans_gloss_words` — swap the ˱˲˓˒‹› `\add`/`\sup` marker
//!     characters for gloss HTML spans (from
//!     `createOETReferencePages.formatNTSpansGlossWords`).
//!   * `convert_hebrew_word_gloss_spans` / `tidy_hebrew_lemma_gloss` — the
//!     `\untr`/`\nd`/`\add`/`\sup` gloss-span chains for OT words and lemmas.
//!   * `tidy_gloss_of_greek_word` / `tidy_greek_lemma_gloss` — the `\add …`
//!     chains for NT word and lemma glosses.
//!   * `liven_strongs_refs` — replace `>H1234<` / `>G1234<` markers with links
//!     to the corresponding Strongs page (from
//!     `createOETReferencePages._strongs_ref_repl`, minus the Python regex
//!     callback).
//!
//! All ports must produce byte-identical output to the Python originals.
//!
//! Changelog:
//!  2026-09-10: Initial port of the helpers listed above.

use std::sync::OnceLock;

use pyo3::exceptions::{PyIndexError, PyKeyError};
use pyo3::prelude::*;
use regex::Regex;

// ── OSHB morphology code dictionaries (createOETReferencePages.py) ─────────

const OSHB_POS_DICT: [(&str, &str); 10] = [
    ("A", "adjective"),
    ("C", "conjunction"),
    ("D", "adverb"),
    ("N", "noun"),
    ("P", "pronoun"),
    ("R", "preposition"),
    ("S", "suffix"),
    ("T", "particle"),
    ("V", "verb"),
    ("x", "(unknown)"),
];

const OSHB_NOUN_DICT: [(&str, &str); 5] = [
    ("N", "noun"),
    ("Nc", "common_noun"),
    ("Ng", "noun_(gentilic)"),
    ("Np", "proper_noun"),
    ("Nx", "noun_(unknown_type)"),
];

const OSHB_ADJECTIVE_DICT: [(&str, &str); 5] = [
    ("Aa", "adjective"),
    ("Ac", "adjective_(cardinal_number)"),
    ("Ag", "adjective_(gentilic)"),
    ("Ao", "adjective_(ordinal_number)"),
    ("Ax", "adjective_(unknown_type)"),
];

const OSHB_HEBREW_VERB_STEM_DICT: [(&str, &str); 28] = [
    ("Vq", "qal_verb"),
    ("VN", "niphal_verb"),
    ("Vp", "piel_verb"),
    ("VP", "pual_verb"),
    ("Vh", "hiphil_verb"),
    ("VH", "hophal_verb"),
    ("Vt", "hithpael_verb"),
    ("Vo", "polel_verb"),
    ("VO", "polal_verb"),
    ("Vr", "hithpolel_verb"),
    ("Vm", "poel_verb"),
    ("VM", "poel_verb"),
    ("Vk", "pael_verb"),
    ("VK", "pulal_verb"),
    ("VQ", "qal_passive_verb"),
    ("Vl", "pilpel_verb"),
    ("VL", "polpal_verb"),
    ("Vf", "hithpalpel_verb"),
    ("VD", "nithpael_verb"),
    ("Vj", "pealal_verb"),
    ("Vi", "pilel_verb"),
    ("Vu", "hothpaal_verb"),
    ("Vc", "tiphil_verb"),
    ("Vv", "hishtaphel_verb"),
    ("Vw", "nithpael_verb"),
    ("Vy", "nithpoel_verb"),
    ("Vz", "hithpoel_verb"),
    ("Vx", "verb_(unknown_stem)"),
];

const OSHB_ARAMAIC_VERB_STEM_DICT: [(&str, &str); 27] = [
    ("Vq", "peal_verb"),
    ("VQ", "peil_verb"),
    ("Vu", "hithpeel_verb"),
    ("Vp", "pael_verb"),
    ("VP", "ithpaal_verb"),
    ("VM", "hithpaal_verb"),
    ("Va", "aphel_verb"),
    ("Vh", "haphel_verb"),
    ("Vs", "shaphel_verb"),
    ("Ve", "shaphel_verb"),
    ("VH", "hophal_verb"),
    ("Vi", "ithpeel_verb"),
    ("Vt", "hishtaphel_verb"),
    ("Vv", "ishtaphel_verb"),
    ("Vw", "hithaphel_verb"),
    ("Vo", "polel_verb"),
    ("Vz", "ithpoel_verb"),
    ("Vr", "hithpolel_verb"),
    ("Vf", "hithpalpel_verb"),
    ("Vb", "hephal_verb"),
    ("Vc", "tiphel"),
    ("Vm", "poel_verb"),
    ("Vl", "palpel_verb"),
    ("VL", "ithpalpel_verb"),
    ("VO", "ithpolel_verb"),
    ("VG", "ittaphal_verb"),
    ("Vx", "verb_(unknown_stem)"),
];

const OSHB_VERB_CONJUGATION_TYPE_DICT: [(&str, &str); 11] = [
    ("p", "perfect_(<i>qatal</i>)"),
    ("q", "sequential_perfect_(<i>weqatal</i>)"),
    ("i", "imperfect_(<i>yiqtol</i>)"),
    ("w", "sequential_imperfect_(<i>wayyiqtol</i>)"),
    ("h", "cohortative"),
    ("j", "jussive"),
    ("v", "imperative"),
    ("r", "active_participle"),
    ("s", "passive_participle"),
    ("a", "infinitive_absolute"),
    ("c", "infinitive_construct"),
];

const OSHB_PRONOUN_DICT: [(&str, &str); 5] = [
    ("Pd", "demonstrative_pronoun"),
    ("Pf", "indefinite_pronoun"),
    ("Pi", "interrogative_pronoun"),
    ("Pp", "personal_pronoun"),
    ("Pr", "relative_pronoun"),
];

const OSHB_PARTICLE_DICT: [(&str, &str); 10] = [
    ("T", "particle"),
    ("Ta", "affirmation_particle"),
    ("Td", "definite_article"),
    ("Te", "exhortation_particle"),
    ("Ti", "interrogative_particle"),
    ("Tj", "interjection_particle"),
    ("Tm", "demonstrative_particle"),
    ("Tn", "negative_particle"),
    ("To", "direct_object_marker"),
    ("Tr", "relative_particle"),
];

const OSHB_PREPOSITION_DICT: [(&str, &str); 2] = [
    ("R", "preposition"),
    ("Rd", "preposition_with_definite_article"),
];

const OSHB_SUFFIX_DICT: [(&str, &str); 4] = [
    ("Sd", "directional_<i>he</i>_suffix"),
    ("Sh", "paragogic_<i>he</i>_suffix"),
    ("Sn", "paragogic_<i>nun</i>_suffix"),
    ("Sp", "pronominal_suffix"),
];

const OSHB_PERSON_DICT: [(&str, &str); 4] =
    [("1", "first"), ("2", "second"), ("3", "third"), ("x", "(unknown)")];

const OSHB_GENDER_DICT: [(&str, &str); 5] = [
    ("b", "both"),
    ("c", "common"),
    ("f", "feminine"),
    ("m", "masculine"),
    ("x", "(unknown)"),
];

const OSHB_NUMBER_DICT: [(&str, &str); 4] =
    [("d", "dual"), ("p", "plural"), ("s", "singular"), ("x", "(unknown)")];

const OSHB_STATE_DICT: [(&str, &str); 3] = [
    ("a", "absolute"),
    ("c", "construct"),
    ("d", "determined"),
];

// ── UHG grammar-page link tables (createOETReferencePages.py) ──────────────
// These map the decoded names above to links; any name not present is used
// as-is (mirroring the Python `try: table[name] / except KeyError` fallback).

const HEBREW_POS_TYPE_TABLE: [(&str, &str); 9] = [
    ("adverb", "<a title=\"Go to grammar page\" href=\"../UHG/adverb.htm#Top\">adverb</a>"),
    ("conjunction", "<a title=\"Go to grammar page\" href=\"../UHG/conjunction.htm#Top\">conjunction</a>"),
    ("noun", "<a title=\"Go to grammar page\" href=\"../UHG/noun.htm#Top\">noun</a>"),
    ("adjective", "<a title=\"Go to grammar page\" href=\"../UHG/adjective.htm#Top\">adjective</a>"),
    ("pronoun", "<a title=\"Go to grammar page\" href=\"../UHG/pronoun.htm#Top\">pronoun</a>"),
    ("particle", "<a title=\"Go to grammar page\" href=\"../UHG/particle.htm#Top\">particle</a>"),
    ("preposition", "<a title=\"Go to grammar page\" href=\"../UHG/preposition.htm#Top\">preposition</a>"),
    ("suffix", "<a title=\"Go to grammar page\" href=\"../UHG/suffix.htm#Top\">suffix</a>"),
    ("verb", "<a title=\"Go to grammar page\" href=\"../UHG/verb.htm#Top\">verb</a>"),
];

const HEBREW_NOUN_TYPE_TABLE: [(&str, &str); 4] = [
    ("noun", "<a title=\"Go to grammar page\" href=\"../UHG/noun.htm#Top\">noun</a>"),
    ("common_noun", "<a title=\"Go to grammar page\" href=\"../UHG/noun_common.htm#Top\">common_noun</a>"),
    ("noun_(gentilic)", "<a title=\"Go to grammar page\" href=\"../UHG/noun_gentilic.htm#Top\">noun_(gentilic)</a>"),
    ("proper_noun", "<a title=\"Go to grammar page\" href=\"../UHG/noun_proper_name.htm#Top\">proper_noun</a>"),
];

const HEBREW_VERB_TYPE_TABLE: [(&str, &str); 23] = [
    ("hiphil_verb", "<a title=\"Go to grammar page\" href=\"../UHG/stem_hiphil.htm#Top\">hiphil_verb</a>"),
    ("hishtaphel_verb", "<a title=\"Go to grammar page\" href=\"../UHG/stem_hishtaphel.htm#Top\">hishtaphel_verb</a>"),
    ("hithpael_verb", "<a title=\"Go to grammar page\" href=\"../UHG/stem_hithpael.htm#Top\">hithpael_verb</a>"),
    ("hithpalpel_verb", "<a title=\"Go to grammar page\" href=\"../UHG/stem_hithpalpel.htm#Top\">hithpalpel_verb</a>"),
    ("hithpoel_verb", "<a title=\"Go to grammar page\" href=\"../UHG/stem_hithpoel.htm#Top\">hithpoel_verb</a>"),
    ("hithpolel_verb", "<a title=\"Go to grammar page\" href=\"../UHG/stem_hithpolel.htm#Top\">hithpolel_verb</a>"),
    ("hophal_verb", "<a title=\"Go to grammar page\" href=\"../UHG/stem_hophal.htm#Top\">hophal_verb</a>"),
    ("hothpaal_verb", "<a title=\"Go to grammar page\" href=\"../UHG/stem_hothpaal.htm#Top\">hothpaal_verb</a>"),
    ("niphal_verb", "<a title=\"Go to grammar page\" href=\"../UHG/stem_niphal.htm#Top\">niphal_verb</a>"),
    ("nithpael_verb", "<a title=\"Go to grammar page\" href=\"../UHG/stem_nithpael.htm#Top\">nithpael_verb</a>"),
    ("pealal_verb", "<a title=\"Go to grammar page\" href=\"../UHG/stem_pealal.htm#Top\">pealal_verb</a>"),
    ("piel_verb", "<a title=\"Go to grammar page\" href=\"../UHG/stem_piel.htm#Top\">piel_verb</a>"),
    ("pilel_verb", "<a title=\"Go to grammar page\" href=\"../UHG/stem_pilel.htm#Top\">pilel_verb</a>"),
    ("pilpel_verb", "<a title=\"Go to grammar page\" href=\"../UHG/stem_pilpel.htm#Top\">pilpel_verb</a>"),
    ("poel_verb", "<a title=\"Go to grammar page\" href=\"../UHG/stem_poel.htm#Top\">poel_verb</a>"),
    ("polal_verb", "<a title=\"Go to grammar page\" href=\"../UHG/stem_polal.htm#Top\">polal_verb</a>"),
    ("polel_verb", "<a title=\"Go to grammar page\" href=\"../UHG/stem_polel.htm#Top\">polel_verb</a>"),
    ("polpal_verb", "<a title=\"Go to grammar page\" href=\"../UHG/stem_polpal.htm#Top\">polpal_verb</a>"),
    ("pual_verb", "<a title=\"Go to grammar page\" href=\"../UHG/stem_pual.htm#Top\">pual_verb</a>"),
    ("pulal_verb", "<a title=\"Go to grammar page\" href=\"../UHG/stem_pulal.htm#Top\">pulal_verb</a>"),
    ("qal_verb", "<a title=\"Go to grammar page\" href=\"../UHG/stem_qal.htm#Top\">qal_verb</a>"),
    ("qal_passive_verb", "<a title=\"Go to grammar page\" href=\"../UHG/stem_qal_passive.htm#Top\">qal_passive_verb</a>"),
    ("tiphil_verb", "<a title=\"Go to grammar page\" href=\"../UHG/stem_tiphil.htm#Top\">tiphil_verb</a>"),
];

const HEBREW_CONJUGATION_TYPE_TABLE: [(&str, &str); 11] = [
    ("perfect_(<i>qatal</i>)", "<a title=\"Go to grammar page\" href=\"../UHG/verb_perfect.htm#Top\">perfect_(<i>qatal</i>)</a>"),
    ("sequential_perfect_(<i>weqatal</i>)", "<a title=\"Go to grammar page\" href=\"../UHG/verb_sequential_perfect.htm#Top\">sequential_perfect_(<i>weqatal</i>)</a>"),
    ("imperfect_(<i>yiqtol</i>)", "<a title=\"Go to grammar page\" href=\"../UHG/verb_imperfect.htm#Top\">imperfect_(<i>yiqtol</i>)</a>"),
    ("sequential_imperfect_(<i>wayyiqtol</i>)", "<a title=\"Go to grammar page\" href=\"../UHG/verb_sequential_imperfect.htm#Top\">sequential_imperfect_(<i>wayyiqtol</i>)</a>"),
    ("cohortative", "<a title=\"Go to grammar page\" href=\"../UHG/verb_cohortative.htm#Top\">cohortative</a>"),
    ("jussive", "<a title=\"Go to grammar page\" href=\"../UHG/verb_jussive.htm#Top\">jussive</a>"),
    ("imperative", "<a title=\"Go to grammar page\" href=\"../UHG/verb_imperative.htm#Top\">imperative</a>"),
    ("active_participle", "<a title=\"Go to grammar page\" href=\"../UHG/participle_active.htm#Top\">active_participle</a>"),
    ("passive_participle", "<a title=\"Go to grammar page\" href=\"../UHG/participle_passive.htm#Top\">passive_participle</a>"),
    ("infinitive_absolute", "<a title=\"Go to grammar page\" href=\"../UHG/infinitive_absolute.htm#Top\">infinitive_absolute</a>"),
    ("infinitive_construct", "<a title=\"Go to grammar page\" href=\"../UHG/infinitive_construct.htm#Top\">infinitive_construct</a>"),
];

const HEBREW_PERSON_TYPE_TABLE: [(&str, &str); 3] = [
    ("first", "<a title=\"Go to grammar page\" href=\"../UHG/person_first.htm#Top\">first</a>"),
    ("second", "<a title=\"Go to grammar page\" href=\"../UHG/person_second.htm#Top\">second</a>"),
    ("third", "<a title=\"Go to grammar page\" href=\"../UHG/person_third.htm#Top\">third</a>"),
];

const HEBREW_GENDER_TYPE_TABLE: [(&str, &str); 4] = [
    ("both", "<a title=\"Go to grammar page\" href=\"../UHG/gender_both.htm#Top\">both</a>"),
    ("common", "<a title=\"Go to grammar page\" href=\"../UHG/gender_common.htm#Top\">common</a>"),
    ("feminine", "<a title=\"Go to grammar page\" href=\"../UHG/gender_feminine.htm#Top\">feminine</a>"),
    ("masculine", "<a title=\"Go to grammar page\" href=\"../UHG/gender_masculine.htm#Top\">masculine</a>"),
];

const HEBREW_PRONOUN_TYPE_TABLE: [(&str, &str); 5] = [
    ("demonstrative_pronoun", "<a title=\"Go to grammar page\" href=\"../UHG/pronoun_demonstrative.htm#Top\">demonstrative_pronoun</a>"),
    ("indefinite_pronoun", "<a title=\"Go to grammar page\" href=\"../UHG/pronoun_indefinite.htm#Top\">indefinite_pronoun</a>"),
    ("interrogative_pronoun", "<a title=\"Go to grammar page\" href=\"../UHG/pronoun_interrogative.htm#Top\">interrogative_pronoun</a>"),
    ("personal_pronoun", "<a title=\"Go to grammar page\" href=\"../UHG/pronoun_personal.htm#Top\">personal_pronoun</a>"),
    ("relative_pronoun", "<a title=\"Go to grammar page\" href=\"../UHG/pronoun_relative.htm#Top\">relative_pronoun</a>"),
];

const HEBREW_PARTICLE_TYPE_TABLE: [(&str, &str); 10] = [
    ("particle", "<a title=\"Go to grammar page\" href=\"../UHG/particle.htm#Top\">particle</a>"),
    ("affirmation_particle", "<a title=\"Go to grammar page\" href=\"../UHG/particle_affirmation.htm#Top\">affirmation_particle</a>"),
    ("definite_article", "<a title=\"Go to grammar page\" href=\"../UHG/particle_definite_article.htm#Top\">definite_article</a>"),
    ("demonstrative_particle", "<a title=\"Go to grammar page\" href=\"../UHG/particle_demonstrative.htm#Top\">demonstrative_particle</a>"),
    ("direct_object_marker", "<a title=\"Go to grammar page\" href=\"../UHG/particle_direct_object_marker.htm#Top\">direct_object_marker</a>"),
    ("exhortation_particle", "<a title=\"Go to grammar page\" href=\"../UHG/particle_exhortation.htm#Top\">exhortation_particle</a>"),
    ("interjection_particle", "<a title=\"Go to grammar page\" href=\"../UHG/particle_interjection.htm#Top\">interjection_particle</a>"),
    ("interrogative_particle", "<a title=\"Go to grammar page\" href=\"../UHG/particle_interrogative.htm#Top\">interrogative_particle</a>"),
    ("negative_particle", "<a title=\"Go to grammar page\" href=\"../UHG/particle_negative.htm#Top\">negative_particle</a>"),
    ("relative_particle", "<a title=\"Go to grammar page\" href=\"../UHG/particle_relative.htm#Top\">relative_particle</a>"),
];

const HEBREW_SUFFIX_TYPE_TABLE: [(&str, &str); 4] = [
    ("directional_<i>he</i>_suffix", "<a title=\"Go to grammar page\" href=\"../UHG/suffix_directional_he.htm#Top\">directional_<i>he</i>_suffix</a>"),
    ("paragogic_<i>he</i>_suffix", "<a title=\"Go to grammar page\" href=\"../UHG/suffix_paragogic_he.htm#Top\">paragogic_<i>he</i>_suffix</a>"),
    ("paragogic_<i>nun</i>_suffix", "<a title=\"Go to grammar page\" href=\"../UHG/suffix_paragogic_nun.htm#Top\">paragogic_<i>nun</i>_suffix</a>"),
    ("pronominal_suffix", "<a title=\"Go to grammar page\" href=\"../UHG/suffix_pronominal.htm#Top\">pronominal_suffix</a>"),
];

const HEBREW_ADJECTIVE_TYPE_TABLE: [(&str, &str); 4] = [
    ("adjective", "<a title=\"Go to grammar page\" href=\"../UHG/adjective.htm#Top\">adjective</a>"),
    ("adjective_(cardinal_number)", "<a title=\"Go to grammar page\" href=\"../UHG/adjective_cardinal_number.htm#Top\">adjective_(cardinal_number)</a>"),
    ("adjective_(gentilic)", "<a title=\"Go to grammar page\" href=\"../UHG/adjective_gentilic.htm#Top\">adjective_(gentilic)</a>"),
    ("adjective_(ordinal_number)", "<a title=\"Go to grammar page\" href=\"../UHG/adjective_ordinal_number.htm#Top\">adjective_(ordinal_number)</a>"),
];

const HEBREW_PREPOSITION_TYPE_TABLE: [(&str, &str); 2] = [
    ("preposition", "<a title=\"Go to grammar page\" href=\"../UHG/preposition.htm#Top\">preposition</a>"),
    ("preposition_with_definite_article", "<a title=\"Go to grammar page\" href=\"../UHG/preposition_definite_article.htm#Top\">preposition_with_definite_article</a>"),
];

const HEBREW_STATE_TYPE_TABLE: [(&str, &str); 2] = [
    ("construct", "<a title=\"Go to grammar page\" href=\"../UHG/state_construct.htm#Top\">construct</a>"),
    ("absolute", "<a title=\"Go to grammar page\" href=\"../UHG/state_absolute.htm#Top\">absolute</a>"),
];

const HEBREW_NUMBER_TYPE_TABLE: [(&str, &str); 3] = [
    ("dual", "<a title=\"Go to grammar page\" href=\"../UHG/number_dual.htm#Top\">dual</a>"),
    ("plural", "<a title=\"Go to grammar page\" href=\"../UHG/number_plural.htm#Top\">plural</a>"),
    ("singular", "<a title=\"Go to grammar page\" href=\"../UHG/number_singular.htm#Top\">singular</a>"),
];

// ── Error type mirroring the Python exceptions the original can raise ──────

#[derive(Debug)]
pub(crate) enum MorphError {
    /// A missing OSHB code lookup (Python would raise KeyError).
    Key(String),
    /// Indexing past the end of a morphology code (Python IndexError).
    Index,
}

/// Look up an OSHB code; missing codes raise (mirroring Python dict lookup).
fn lookup_osbb<'a>(table: &[(&'a str, &'a str)], key: &str) -> Result<&'a str, MorphError> {
    table
        .iter()
        .find(|(k, _)| *k == key)
        .map(|(_, v)| *v)
        .ok_or_else(|| MorphError::Key(key.to_string()))
}

/// Look up a UHG link table with the original's `except KeyError` fallback
/// (missing names are used verbatim).
fn table_or_fallback(table: &[(&str, &str)], key: &str) -> String {
    match table.iter().find(|(k, _)| *k == key) {
        Some((_, v)) => (*v).to_string(),
        None => key.to_string(),
    }
}

/// The `tHM_individualMorphology[i]` indexing from the Python original.
fn morph_char(chars: &[char], index: usize) -> Result<char, MorphError> {
    chars.get(index).copied().ok_or(MorphError::Index)
}

/// Build a comma-separated OSHB morphology string into the
/// "Morphology=… <small>…</small> PoS=<b>…</b>" HTML field.
///
/// Byte-identical port of `createOETReferencePages.tidy_Hebrew_morphology`.
pub(crate) fn tidy_hebrew_morphology(row_type: &str, morphology: &str) -> Result<String, MorphError> {
    let mut result = String::new();
    for individual in morphology.split(',') {
        if !individual.is_empty() {
            // The Python builds a per-item suffix and concatenates it with the
            // 'Aramaic ' prefix re-prepended on EVERY iteration (so multiple
            // Aramaic items stack the prefixes at the very front).
            let mut suffix = String::new();
            if !result.is_empty() {
                suffix.push_str("<br>\u{2003}");
            }
            suffix.push_str(
                "<small><a title=\"Learn more about OSHB morphology\" \
                 href=\"https://hb.OpenScriptures.org/HomeFiles/Morph.html\">Morphology</a>=\
                 <a title=\"See OSHB morphology codes\" \
                 href=\"https://hb.OpenScriptures.org/parsing/HebrewMorphologyCodes.html\">",
            );
            suffix.push_str(individual);
            suffix.push_str("</a></small>");
            let details = tidy_hebrew_morphology_details(row_type, individual)?;
            suffix.push('\u{2003}');
            suffix.push_str(&details);
            if row_type.contains('A') {
                result = format!("Aramaic {result}{suffix}");
            } else {
                result.push_str(&suffix);
            }
        } else {
            // A blank morphology item (e.g., AMO_6:14w14) replaces the whole field.
            result.clear();
            result.push_str("(MISSING)");
        }
    }
    Ok(result)
}

/// The per-item `tHM_word_details_field` computation.
fn tidy_hebrew_morphology_details(row_type: &str, individual: &str) -> Result<String, MorphError> {
    let chars: Vec<char> = individual.chars().collect();
    let pos = morph_char(&chars, 0)?; // tHM_PoS
    let pos_with_type: String = chars.iter().take(2).collect(); // first two characters
    let mut details;

    match pos {
        'N' => {
            // noun
            let noun_type = lookup_osbb(&OSHB_NOUN_DICT, &pos_with_type)?;
            let noun_field = table_or_fallback(&HEBREW_NOUN_TYPE_TABLE, noun_type);
            details = format!("PoS=<b>{noun_field}</b>");
            if chars.len() > 2 {
                let gender_char = morph_char(&chars, 2)?;
                let gender = lookup_osbb(&OSHB_GENDER_DICT, &gender_char.to_string())?;
                let gender_field = table_or_fallback(&HEBREW_GENDER_TYPE_TABLE, gender);
                let number_char = morph_char(&chars, 3)?;
                let number = lookup_osbb(&OSHB_NUMBER_DICT, &number_char.to_string())?;
                let number_field = table_or_fallback(&HEBREW_NUMBER_TYPE_TABLE, number);
                let state_char = morph_char(&chars, 4)?;
                let state = lookup_osbb(&OSHB_STATE_DICT, &state_char.to_string())?;
                let state_field = table_or_fallback(&HEBREW_STATE_TYPE_TABLE, state);
                details.push_str(&format!(
                    "  Gender={gender_field}  Number={number_field}  State={state_field}"
                ));
            }
        }
        'V' => {
            // verb
            let verb_type = if row_type.contains('A') {
                lookup_osbb(&OSHB_ARAMAIC_VERB_STEM_DICT, &pos_with_type)?
            } else {
                lookup_osbb(&OSHB_HEBREW_VERB_STEM_DICT, &pos_with_type)?
            };
            let verb_field = table_or_fallback(&HEBREW_VERB_TYPE_TABLE, verb_type);
            let conj_char = morph_char(&chars, 2)?;
            let conj_type = lookup_osbb(&OSHB_VERB_CONJUGATION_TYPE_DICT, &conj_char.to_string())?;
            let conj_field = table_or_fallback(&HEBREW_CONJUGATION_TYPE_TABLE, conj_type);
            details = format!("PoS=<b>{verb_field}</b>  Type={conj_field}");
            match chars.len() {
                6 => {
                    if matches!(morph_char(&chars, 2)?, 'r' | 's') {
                        // active or passive PARTICIPLE (no person, but has a state)
                        let state_char = morph_char(&chars, 5)?;
                        let state = lookup_osbb(&OSHB_STATE_DICT, &state_char.to_string())?;
                        let state_field = table_or_fallback(&HEBREW_STATE_TYPE_TABLE, state);
                        let gender_char = morph_char(&chars, 3)?;
                        let gender = lookup_osbb(&OSHB_GENDER_DICT, &gender_char.to_string())?;
                        let gender_field = table_or_fallback(&HEBREW_GENDER_TYPE_TABLE, gender);
                        let number_char = morph_char(&chars, 4)?;
                        let number = lookup_osbb(&OSHB_NUMBER_DICT, &number_char.to_string())?;
                        let number_field = table_or_fallback(&HEBREW_NUMBER_TYPE_TABLE, number);
                        details.push_str(&format!(
                            "  Gender={gender_field}  Number={number_field}  State={state_field}"
                        ));
                    } else {
                        let person_char = morph_char(&chars, 3)?;
                        let person = lookup_osbb(&OSHB_PERSON_DICT, &person_char.to_string())?;
                        let person_field = table_or_fallback(&HEBREW_PERSON_TYPE_TABLE, person);
                        let gender_char = morph_char(&chars, 4)?;
                        let gender = lookup_osbb(&OSHB_GENDER_DICT, &gender_char.to_string())?;
                        let gender_field = table_or_fallback(&HEBREW_GENDER_TYPE_TABLE, gender);
                        let number_char = morph_char(&chars, 5)?;
                        let number = lookup_osbb(&OSHB_NUMBER_DICT, &number_char.to_string())?;
                        let number_field = table_or_fallback(&HEBREW_NUMBER_TYPE_TABLE, number);
                        details.push_str(&format!(
                            "  Person={person_field}  Gender={gender_field}  Number={number_field}"
                        ));
                    }
                }
                7 => {
                    let person_char = morph_char(&chars, 3)?;
                    let person = lookup_osbb(&OSHB_PERSON_DICT, &person_char.to_string())?;
                    let person_field = table_or_fallback(&HEBREW_PERSON_TYPE_TABLE, person);
                    let gender_char = morph_char(&chars, 4)?;
                    let gender = lookup_osbb(&OSHB_GENDER_DICT, &gender_char.to_string())?;
                    let gender_field = table_or_fallback(&HEBREW_GENDER_TYPE_TABLE, gender);
                    let number_char = morph_char(&chars, 5)?;
                    let number = lookup_osbb(&OSHB_NUMBER_DICT, &number_char.to_string())?;
                    let number_field = table_or_fallback(&HEBREW_NUMBER_TYPE_TABLE, number);
                    let state_char = morph_char(&chars, 6)?;
                    let state = lookup_osbb(&OSHB_STATE_DICT, &state_char.to_string())?;
                    let state_field = table_or_fallback(&HEBREW_STATE_TYPE_TABLE, state);
                    details.push_str(&format!(
                        "  Person={person_field}  Gender={gender_field}  Number={number_field}  State={state_field}"
                    ));
                }
                _ => {} // len 3, 4 or 5: nothing more (3 = infinitive absolute/construct)
            }
        }
        'A' => {
            // adjective
            let adjective_type = lookup_osbb(&OSHB_ADJECTIVE_DICT, &pos_with_type)?;
            let adjective_field = table_or_fallback(&HEBREW_ADJECTIVE_TYPE_TABLE, adjective_type);
            let gender_char = morph_char(&chars, 2)?;
            let gender = lookup_osbb(&OSHB_GENDER_DICT, &gender_char.to_string())?;
            let gender_field = table_or_fallback(&HEBREW_GENDER_TYPE_TABLE, gender);
            let number_char = morph_char(&chars, 3)?;
            let number = lookup_osbb(&OSHB_NUMBER_DICT, &number_char.to_string())?;
            let number_field = table_or_fallback(&HEBREW_NUMBER_TYPE_TABLE, number);
            let state_char = morph_char(&chars, 4)?;
            let state = lookup_osbb(&OSHB_STATE_DICT, &state_char.to_string())?;
            let state_field = table_or_fallback(&HEBREW_STATE_TYPE_TABLE, state);
            details = format!(
                "PoS=<b>{adjective_field}</b>  Gender={gender_field}  Number={number_field}  State={state_field}"
            );
        }
        'P' => {
            // pronoun
            let pronoun_type = lookup_osbb(&OSHB_PRONOUN_DICT, &pos_with_type)?;
            let pronoun_field = table_or_fallback(&HEBREW_PRONOUN_TYPE_TABLE, pronoun_type);
            details = format!("PoS=<b>{pronoun_field}</b>");
            if chars.len() > 2 {
                append_person_gender_number(
                    &mut details,
                    &chars,
                    2, // person
                    3, // gender
                    4, // number
                )?;
            }
        }
        'T' => {
            // particle
            if chars.len() == 1 {
                // e.g., at Aramaic DAN_4:12w11
                let particle_field = table_or_fallback(&HEBREW_PARTICLE_TYPE_TABLE, "particle");
                details = format!("PoS=<b>{particle_field}</b>");
            } else {
                let particle_type = lookup_osbb(&OSHB_PARTICLE_DICT, &pos_with_type)?;
                let particle_field = table_or_fallback(&HEBREW_PARTICLE_TYPE_TABLE, particle_type);
                details = format!("PoS=<b>{particle_field}</b>");
            }
        }
        'R' => {
            // preposition
            let preposition_type = if chars.len() == 2 {
                lookup_osbb(&OSHB_PREPOSITION_DICT, &pos_with_type)?
            } else {
                lookup_osbb(&OSHB_POS_DICT, &pos.to_string())?
            };
            let preposition_field =
                table_or_fallback(&HEBREW_PREPOSITION_TYPE_TABLE, preposition_type);
            details = format!("PoS=<b>{preposition_field}</b>");
        }
        'S' => {
            // suffix
            let suffix_type = lookup_osbb(&OSHB_SUFFIX_DICT, &pos_with_type)?;
            let suffix_field = table_or_fallback(&HEBREW_SUFFIX_TYPE_TABLE, suffix_type);
            details = format!("PoS=<b>{suffix_field}</b>");
            if chars.len() > 2 {
                append_person_gender_number(
                    &mut details,
                    &chars,
                    2, // person
                    3, // gender
                    4, // number
                )?;
            }
        }
        _ => {
            // conjunction (C) or adverb (D): only the PoS
            let pos_type = lookup_osbb(&OSHB_POS_DICT, &pos.to_string())?;
            let pos_field = table_or_fallback(&HEBREW_POS_TYPE_TABLE, pos_type);
            details = format!("PoS=<b>{pos_field}</b>");
        }
    }
    Ok(details)
}

/// Append the common "  Person=…  Gender=…  Number=…" trailing segment.
fn append_person_gender_number(
    details: &mut String,
    chars: &[char],
    person_i: usize,
    gender_i: usize,
    number_i: usize,
) -> Result<(), MorphError> {
    let person_char = morph_char(chars, person_i)?;
    let person = lookup_osbb(&OSHB_PERSON_DICT, &person_char.to_string())?;
    let person_field = table_or_fallback(&HEBREW_PERSON_TYPE_TABLE, person);
    let gender_char = morph_char(chars, gender_i)?;
    let gender = lookup_osbb(&OSHB_GENDER_DICT, &gender_char.to_string())?;
    let gender_field = table_or_fallback(&HEBREW_GENDER_TYPE_TABLE, gender);
    let number_char = morph_char(chars, number_i)?;
    let number = lookup_osbb(&OSHB_NUMBER_DICT, &number_char.to_string())?;
    let number_field = table_or_fallback(&HEBREW_NUMBER_TYPE_TABLE, number);
    details.push_str(&format!(
        "  Person={person_field}  Gender={gender_field}  Number={number_field}"
    ));
    Ok(())
}

// ── Gloss-span chains ───────────────────────────────────────────────────────

/// UTF-8 characters swapped for gloss spans (only the FIRST occurrence):
/// ˱=U+02F1, ˲=U+02F2, ˓=U+02D3, ˒=U+02D2, ‹=U+2039, ›=U+203A.
pub fn format_nt_spans_gloss_words(gloss_words: &str) -> String {
    gloss_words
        .replacen('\u{02f1}', "<span class=\"glossPre\">", 1)
        .replacen('\u{02f2}', "</span>", 1)
        .replacen('\u{02d3}', "<span class=\"glossHelper\">", 1)
        .replacen('\u{02d2}', "</span>", 1)
        .replacen('\u{2039}', "<span class=\"glossPost\">", 1)
        .replacen('\u{203a}', "</span>", 1)
        .replace("\\add >", "<span class=\"addExtra\">")
        .replace("\\add*", "</span>")
        .replace("\\add ", "<span class=\"add\">")
        .replace("\\sup ", "<sup>")
        .replace("\\sup*", "</sup>")
        .replace("__SLASH__", "/")
}

/// Shared `\\untr`/`\\nd`/`\\add`/`\\sup`/underscore gloss-span chain
/// (identical in `convert_Hebrew_word_gloss_spans` and
/// `tidy_Hebrew_lemma_gloss`).
fn hebrew_gloss_spans_common(eng_gloss: &str) -> String {
    eng_gloss
        .replace("\\untr ", "<span class=\"untr\">")
        .replace("\\untr*", "</span>")
        .replace("\\nd ", "<span class=\"nd\">")
        .replace("\\nd*", "</span>")
        .replace("\\add >", "<span class=\"addExtra\">")
        .replace("\\add*", "</span>")
        .replace("\\add ", "<span class=\"addExtra\">")
        .replace("\\sup ", "<sup>")
        .replace("\\sup*", "</sup>")
        .replace('_', "<span class=\"ul\">_</span>")
}

/// Byte-identical port of `createOETReferencePages.convert_Hebrew_word_gloss_spans`.
pub fn convert_hebrew_word_gloss_spans(eng_gloss: &str) -> String {
    hebrew_gloss_spans_common(eng_gloss)
}

/// Byte-identical port of `createOETReferencePages.tidy_Hebrew_lemma_gloss`.
pub fn tidy_hebrew_lemma_gloss(eng_gloss: &str) -> String {
    hebrew_gloss_spans_common(eng_gloss)
}

/// Byte-identical port of `createOETReferencePages.tidyGlossOfGreekWord`.
pub fn tidy_gloss_of_greek_word(eng_gloss: &str) -> String {
    eng_gloss
        .replace("\\add +", "<span class=\"addArticle\">")
        .replace("\\add =", "<span class=\"addCopula\">")
        .replace("\\add <", "<span class=\"addDirectObject\">")
        .replace("\\add >", "<span class=\"addExtra\">")
        .replace("\\add &", "<span class=\"addOwner\">")
        .replace("\\add ", "<span class=\"add\">")
        .replace("\\add*", "</span>")
        .replace('_', "<span class=\"ul\">_</span>")
}

/// Byte-identical port of `createOETReferencePages.tidy_Greek_lemma_gloss`.
pub fn tidy_greek_lemma_gloss(eng_gloss: &str) -> String {
    eng_gloss
        .replace("\\add +", "<span class=\"addArticle\">")
        .replace("\\add >", "<span class=\"addExtra\">")
        .replace("\\add ", "<span class=\"add\">")
        .replace("\\add*", "</span>")
}

// ── Strongs reference linking ───────────────────────────────────────────────

/// Regex from `createOETReferencePages.STRONGS_NUMBER_REGEX` (a `>H1234<` marker,
/// where the number has 1–5 digits and doesn't start with zero).
static STRONGS_REGEX: OnceLock<Regex> = OnceLock::new();

/// Link every `>H1234<` / `>G1234<` marker in `middle` to its Strongs page.
///
/// Byte-identical port of `STRONGS_NUMBER_REGEX.sub( _strongs_ref_repl, middle )`
/// using `STRONGS_FOLDER_DICT = {'G':'GrkStrng', 'H':'HebStrng'}`.
pub fn liven_strongs_refs(middle: &str) -> String {
    let regex = STRONGS_REGEX.get_or_init(|| Regex::new(r">[GH][1-9][0-9]{0,4}<").unwrap());
    regex
        .replace_all(middle, |caps: &regex::Captures| {
            let matched = &caps[0];
            let letter_and_number = &matched[1..matched.len() - 1]; // strip '>' and '<'
            let folder = if letter_and_number.starts_with('G') {
                "GrkStrng"
            } else {
                "HebStrng"
            };
            format!("><a href=\"../{folder}/{letter_and_number}.htm#Top\">{letter_and_number}</a><")
        })
        .into_owned()
}

// ── PyO3 wrappers ───────────────────────────────────────────────────────────

/// Map a `MorphError` to the matching Python exception.
fn morph_err_to_pyerr(error: MorphError) -> PyErr {
    match error {
        MorphError::Key(key) => PyKeyError::new_err(key),
        MorphError::Index => PyIndexError::new_err("string index out of range"),
    }
}

#[pyfunction(name = "formatNTSpansGlossWords")]
#[allow(non_snake_case)]
pub fn format_nt_spans_gloss_words_py(glossWords: &str) -> String {
    format_nt_spans_gloss_words(glossWords)
}

#[pyfunction(name = "convertHebrewWordGlossSpans")]
#[allow(non_snake_case)]
pub fn convert_hebrew_word_gloss_spans_py(engGloss: &str) -> String {
    convert_hebrew_word_gloss_spans(engGloss)
}

#[pyfunction(name = "tidyHebrewMorphology")]
#[allow(non_snake_case)]
pub fn tidy_hebrew_morphology_py(rowType: &str, morphology: &str) -> PyResult<String> {
    tidy_hebrew_morphology(rowType, morphology).map_err(morph_err_to_pyerr)
}

#[pyfunction(name = "tidyHebrewLemmaGloss")]
#[allow(non_snake_case)]
pub fn tidy_hebrew_lemma_gloss_py(engGloss: &str) -> String {
    tidy_hebrew_lemma_gloss(engGloss)
}

#[pyfunction(name = "tidyGlossOfGreekWord")]
#[allow(non_snake_case)]
pub fn tidy_gloss_of_greek_word_py(engGloss: &str) -> String {
    tidy_gloss_of_greek_word(engGloss)
}

#[pyfunction(name = "tidyGreekLemmaGloss")]
#[allow(non_snake_case)]
pub fn tidy_greek_lemma_gloss_py(engGloss: &str) -> String {
    tidy_greek_lemma_gloss(engGloss)
}

#[pyfunction(name = "livenStrongsRefs")]
#[allow(non_snake_case)]
pub fn liven_strongs_refs_py(middle: &str) -> String {
    liven_strongs_refs(middle)
}

// ── Tests ───────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn tidy_morph(row_type: &str, morphology: &str) -> String {
        tidy_hebrew_morphology(row_type, morphology).unwrap()
    }

    #[test]
    fn common_noun_exact() {
        // Ground truth: real output for 'Ncmsa' in the generated word pages.
        let got = tidy_morph("", "Ncmsa");
        let expected = "<small><a title=\"Learn more about OSHB morphology\" href=\"https://hb.OpenScriptures.org/HomeFiles/Morph.html\">Morphology</a>=<a title=\"See OSHB morphology codes\" href=\"https://hb.OpenScriptures.org/parsing/HebrewMorphologyCodes.html\">Ncmsa</a></small>\u{2003}PoS=<b><a title=\"Go to grammar page\" href=\"../UHG/noun_common.htm#Top\">common_noun</a></b>  Gender=<a title=\"Go to grammar page\" href=\"../UHG/gender_masculine.htm#Top\">masculine</a>  Number=<a title=\"Go to grammar page\" href=\"../UHG/number_singular.htm#Top\">singular</a>  State=<a title=\"Go to grammar page\" href=\"../UHG/state_absolute.htm#Top\">absolute</a>";
        assert_eq!(got, expected);
    }

    #[test]
    fn active_participle_verb_exact() {
        // Ground truth: real output for 'Vmrmsc' (poel active participle).
        let got = tidy_morph("", "Vmrmsc");
        let expected = "<small><a title=\"Learn more about OSHB morphology\" href=\"https://hb.OpenScriptures.org/HomeFiles/Morph.html\">Morphology</a>=<a title=\"See OSHB morphology codes\" href=\"https://hb.OpenScriptures.org/parsing/HebrewMorphologyCodes.html\">Vmrmsc</a></small>\u{2003}PoS=<b><a title=\"Go to grammar page\" href=\"../UHG/stem_poel.htm#Top\">poel_verb</a></b>  Type=<a title=\"Go to grammar page\" href=\"../UHG/participle_active.htm#Top\">active_participle</a>  Gender=<a title=\"Go to grammar page\" href=\"../UHG/gender_masculine.htm#Top\">masculine</a>  Number=<a title=\"Go to grammar page\" href=\"../UHG/number_singular.htm#Top\">singular</a>  State=<a title=\"Go to grammar page\" href=\"../UHG/state_construct.htm#Top\">construct</a>";
        assert_eq!(got, expected);
    }

    #[test]
    fn pronominal_suffix_exact() {
        // Ground truth: real output for 'Sp3ms'.
        let got = tidy_morph("", "Sp3ms");
        let expected = "<small><a title=\"Learn more about OSHB morphology\" href=\"https://hb.OpenScriptures.org/HomeFiles/Morph.html\">Morphology</a>=<a title=\"See OSHB morphology codes\" href=\"https://hb.OpenScriptures.org/parsing/HebrewMorphologyCodes.html\">Sp3ms</a></small>\u{2003}PoS=<b><a title=\"Go to grammar page\" href=\"../UHG/suffix_pronominal.htm#Top\">pronominal_suffix</a></b>  Person=<a title=\"Go to grammar page\" href=\"../UHG/person_third.htm#Top\">third</a>  Gender=<a title=\"Go to grammar page\" href=\"../UHG/gender_masculine.htm#Top\">masculine</a>  Number=<a title=\"Go to grammar page\" href=\"../UHG/number_singular.htm#Top\">singular</a>";
        assert_eq!(got, expected);
    }

    #[test]
    fn aramaic_verb_tidy() {
        // 'Va' (aphel) only exists in the Aramaic stem dict; rowType with an
        // 'A' both selects it and adds the 'Aramaic ' prefix.
        let got = tidy_morph("ARA", "Vaa");
        // The 'Aramaic ' prefix is re-prepended at the very front of the whole
        // accumulated field on every item, exactly as in Python's
        // `{'Aramaic ' if 'A' in rowType}{field} {details}`.
        let expected_prefix = "Aramaic <small><a title=\"Learn more about OSHB morphology\" \
            href=\"https://hb.OpenScriptures.org/HomeFiles/Morph.html\">Morphology</a>=\
            <a title=\"See OSHB morphology codes\" \
            href=\"https://hb.OpenScriptures.org/parsing/HebrewMorphologyCodes.html\">Vaa</a></small>\u{2003}PoS=<b>aphel_verb</b>";
        assert!(got.starts_with(expected_prefix), "got: {got}");
        // Same code without an 'A' in the row type must use the Hebrew dict
        // (which has no 'Va' -- the original raises KeyError).
        assert!(tidy_hebrew_morphology("", "Vaa").is_err());
    }

    #[test]
    fn aramaic_prefix_doubles_per_item() {
        // Ground truth: 'Rd,Rd' with an A row type yields TWO front prefixes.
        let got = tidy_morph("ARA", "Rd,Rd");
        let expected = concat!(
            "Aramaic Aramaic <small><a title=\"Learn more about OSHB morphology\" ",
            "href=\"https://hb.OpenScriptures.org/HomeFiles/Morph.html\">Morphology</a>=",
            "<a title=\"See OSHB morphology codes\" ",
            "href=\"https://hb.OpenScriptures.org/parsing/HebrewMorphologyCodes.html\">Rd",
            "</a></small>\u{2003}PoS=<b><a title=\"Go to grammar page\" ",
            "href=\"../UHG/preposition_definite_article.htm#Top\">",
            "preposition_with_definite_article</a></b><br>\u{2003}<small><a title=\"Learn more ",
            "about OSHB morphology\" href=\"https://hb.OpenScriptures.org/HomeFiles/Morph.html\">",
            "Morphology</a>=<a title=\"See OSHB morphology codes\" ",
            "href=\"https://hb.OpenScriptures.org/parsing/HebrewMorphologyCodes.html\">Rd",
            "</a></small>\u{2003}PoS=<b><a title=\"Go to grammar page\" ",
            "href=\"../UHG/preposition_definite_article.htm#Top\">",
            "preposition_with_definite_article</a></b>"
        );
        assert_eq!(got, expected);
    }

    #[test]
    fn multiple_items_use_br_separator() {
        // Ground truth: real output for 'Rd,Ncmsa'.
        let got = tidy_morph("", "Rd,Ncmsa");
        assert!(got.contains("<br>\u{2003}"), "unexpected output: {got}");
        assert!(got.contains(
            "PoS=<b><a title=\"Go to grammar page\" href=\"../UHG/preposition_definite_article.htm#Top\">preposition_with_definite_article</a></b>"
        ));
        assert!(got.contains(
            "PoS=<b><a title=\"Go to grammar page\" href=\"../UHG/noun_common.htm#Top\">common_noun</a></b>"
        ));
    }

    #[test]
    fn blank_morphology_is_missing() {
        // AMO_6:14w14-style blank item replaces the whole accumulated field.
        assert_eq!(tidy_morph("", ""), "(MISSING)");
        assert_eq!(tidy_morph("", "Ncmsa,"), "(MISSING)");
    }

    #[test]
    fn hebrew_gloss_underscore() {
        // Ground truth: 'a_psalm' rendered in the generated word pages.
        assert_eq!(
            convert_hebrew_word_gloss_spans("a_psalm"),
            "a<span class=\"ul\">_</span>psalm"
        );
        assert_eq!(tidy_hebrew_lemma_gloss("a_psalm"),
            "a<span class=\"ul\">_</span>psalm");
        // \add variants
        assert_eq!(
            convert_hebrew_word_gloss_spans("x\\add >y\\add*"),
            "x<span class=\"addExtra\">y</span>"
        );
    }

    #[test]
    fn greek_gloss_add_classes() {
        assert_eq!(
            tidy_gloss_of_greek_word("\\add +x\\add*"),
            "<span class=\"addArticle\">x</span>"
        );
        assert_eq!(
            tidy_gloss_of_greek_word("\\add =x\\add*"),
            "<span class=\"addCopula\">x</span>"
        );
        assert_eq!(
            tidy_greek_lemma_gloss("\\add +x\\add*"),
            "<span class=\"addArticle\">x</span>"
        );
    }

    #[test]
    fn format_nt_spans_special_markers() {
        // Only the FIRST occurrence of each marker character is replaced.
        assert_eq!(
            format_nt_spans_gloss_words("\u{02f1}one\u{02f2} \u{02f1}two\u{02f2}"),
            "<span class=\"glossPre\">one</span> \u{02f1}two\u{02f2}"
        );
        assert_eq!(
            format_nt_spans_gloss_words("\\add >x\\add* __SLASH__"),
            "<span class=\"addExtra\">x</span> /"
        );
    }

    #[test]
    fn strongs_refs_exact() {
        // Ground truth: real refs in the generated Strongs pages.
        assert_eq!(
            liven_strongs_refs(">H1098<"),
            "><a href=\"../HebStrng/H1098.htm#Top\">H1098</a><"
        );
        assert_eq!(
            liven_strongs_refs(">G1011<"),
            "><a href=\"../GrkStrng/G1011.htm#Top\">G1011</a><"
        );
        // Multiple markers in one string; non-matching text is untouched.
        assert_eq!(
            liven_strongs_refs("a >H1< b >G12345< c >H0123< d"),
            "a ><a href=\"../HebStrng/H1.htm#Top\">H1</a>< b ><a href=\"../GrkStrng/G12345.htm#Top\">G12345</a>< c >H0123< d"
        );
    }
}