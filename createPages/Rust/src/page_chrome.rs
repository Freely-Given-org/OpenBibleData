//! Pure-Rust port of the page chrome builders from `html.py`:
//! `makeTop`, `_makeNavigationLinks`, `_makeWorkNavListParagraph`, and
//! `makeViewNavListParagraph`.
//!
//! All State-dependent data is snapshotted once into a [`PageChromeConfig`]
//! (built from Python by the PyO3 wrapper in lib.rs), so generating a page
//! top requires no Python interaction at all.
//!
//! Byte-for-byte output fidelity with the original Python functions is
//! guarded by createPages/golden_makeTop.py.

use std::collections::{HashMap, HashSet};

/// Separator used by Python's `'…'.join()` calls in html.py (EM SPACE).
const EM_SPACE: &str = "\u{2003}";

const NAV_LINK_PAGE_TYPES_FOR_KB_JS: [&str; 9] = [
    "chapter",
    "section",
    "sectionIndex",
    "book",
    "parallelVerse",
    "interlinearVerse",
    "relatedPassage",
    "topicPassages",
    "kingdom",
];

/// Versions that never get their own view-bar links even when they are the
/// current version (html.makeViewNavListParagraph).
const VIEW_BAR_EXCLUDED_VERSIONS: [&str; 11] = [
    "PLBL", "HAP", "TOSN", "TTN", "TOBD", "SOTN", "UTN", "UBS", "THBD", "BMM", "OBI",
];

/// Notes versions that are skipped in the work navigation list.
const NOTES_VERSIONS_TO_SKIP: [&str; 4] = ["TOSN", "TTN", "SOTN", "UTN"];

/// Snapshot of everything `html.makeTop` needs from the Python State object,
/// extracted once per build (or per distinct State in tests).
#[derive(Debug, Clone, Default)]
pub struct PageChromeConfig {
    pub test_mode_flag: bool,
    pub site_name: String,
    /// Ordered list of version abbreviations (state.BibleVersions).
    pub bible_versions: Vec<String>,
    pub versions_without_their_own_pages: HashSet<String>,
    /// state.TEST_VERSIONS_ONLY -- None means unrestricted.
    pub test_versions_only: Option<HashSet<String>>,
    /// Precomputed `makeSafeString(versionAbbreviation)` for each version.
    pub safe_names: HashMap<String, String>,
    /// Decoration key -> [prefix, suffix]; includes pseudo entries such as
    /// 'Related', 'Topics', 'Parallel', 'Interlinear', 'Reference',
    /// 'Dictionary', 'Search'.
    pub decorations: HashMap<String, [String; 2]>,
    /// Version abbreviation -> long Bible name (state.BibleNames).
    pub bible_names: HashMap<String, String>,
    /// All book codes loaded across versions (state.allBBBs).
    pub all_bbbs: Vec<String>,
    /// Preloaded versions whose discoveryResults say they have section
    /// headings. Keys match state.preloadedBibles keys (e.g. 'OET-RV').
    pub have_section_headings: HashSet<String>,
    /// Preloaded versions -> set of contained book codes, used for the
    /// `entryBBB in thisBible` membership checks. Versions absent from this
    /// map are treated as empty books, but only tolerated in TEST mode
    /// (mirroring the assert in html._makeWorkNavListParagraph).
    pub version_books: HashMap<String, HashSet<String>>,
}

impl PageChromeConfig {
    /// Section-headings flag for a version, using the preloadedBibles key
    /// convention ('OET' resolves to 'OET-RV'). Mirrors the try/except in
    /// html._makeWorkNavListParagraph: unknown versions simply report false.
    pub fn have_sections(&self, version_abbreviation: &str) -> bool {
        let key = if version_abbreviation == "OET" {
            "OET-RV"
        } else {
            version_abbreviation
        };
        self.have_section_headings.contains(key)
    }

    /// Book-set membership check (`entryBBB in thisBible`). Returns an error
    /// for versions that aren't preloaded unless we're in TEST mode, where
    /// Python substitutes an empty list.
    fn book_available(&self, version_key: &str, bbb: &str) -> Result<bool, PageChromeError> {
        match self.version_books.get(version_key) {
            Some(books) => Ok(books.contains(bbb)),
            None => {
                if self.test_mode_flag {
                    Ok(false)
                } else {
                    Err(PageChromeError::NotPreloaded(version_key.to_string()))
                }
            }
        }
    }
}

/// Errors mirroring the ways the Python code asserts/crashes.
#[derive(Debug, PartialEq, Eq)]
pub enum PageChromeError {
    UnknownPageType(String),
    MissingDecoration(String),
    MissingName(String),
    NotPreloaded(String),
    MultipleBbbMatches(String),
    NoFilenameForAdaptation(String),
    StraySectionReference(String),
    MalformedEntry(String),
}

impl std::fmt::Display for PageChromeError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            PageChromeError::UnknownPageType(pt) => write!(f, "Unknown pageType: {pt}"),
            PageChromeError::MissingDecoration(key) => {
                write!(f, "Missing BibleVersionDecorations entry: {key}")
            }
            PageChromeError::MissingName(key) => write!(f, "Missing BibleNames entry: {key}"),
            PageChromeError::NotPreloaded(key) => {
                write!(f, "Version not preloaded (and not TEST mode): {key}")
            }
            PageChromeError::MultipleBbbMatches(entry) => {
                write!(f, "Found more than one BBB in nav entry: {entry}")
            }
            PageChromeError::NoFilenameForAdaptation(entry) => {
                write!(f, "Need a filename to adapt bad link: {entry}")
            }
            PageChromeError::StraySectionReference(entry) => {
                write!(f, "Found a possible section reference {entry}")
            }
            PageChromeError::MalformedEntry(entry) => {
                write!(f, "Couldn't parse version out of nav entry: {entry}")
            }
        }
    }
}

impl std::error::Error for PageChromeError {}

/// Select the stylesheet exactly like html.makeTop does. Note that
/// 'kingdomIndex' is deliberately absent: the original elif chain has no
/// branch for it either (it crashes there), so we report it as unknown.
fn css_filename_for(page_type: &str, version_abbreviation: Option<&str>) -> Result<&'static str, PageChromeError> {
    let oet_css = version_abbreviation.is_some_and(|va| va.contains("OET"));
    Ok(match page_type {
        "chapter" | "section" | "book" => {
            if oet_css {
                "OETChapter.css"
            } else {
                "BibleChapter.css"
            }
        }
        "relatedPassage" => "ParallelPassages.css",
        "topicPassages" => "TopicalPassages.css",
        "parallelVerse" => "ParallelVerses.css",
        "interlinearVerse" => "InterlinearVerse.css",
        "word" | "lemma" | "morpheme" | "person" | "location" | "StrongsPage" => "BibleWord.css",
        "dictionaryLetterIndex" | "dictionaryEntry" | "dictionaryIntro" => "BibleDict.css",
        "site" | "details" | "AllDetails" | "search" | "about" | "news" | "OETKey" | "TopIndex"
        | "kingdom" | "statistics" | "bookIndex" | "chapterIndex" | "sectionIndex"
        | "relatedSectionIndex" | "topicsIndex" | "dictionaryMainIndex" | "StrongsIndex"
        | "wordIndex" | "lemmaIndex" | "morphemeIndex" | "personIndex" | "locationIndex"
        | "statisticsIndex" | "referenceIndex" => "BibleSite.css",
        other => return Err(PageChromeError::UnknownPageType(other.to_string())),
    })
}

/// Extract the version abbreviation displayed between '">' and the following
/// '<' in a navigation entry (html uses .index() the same way).
fn extract_displayed_version(entry: &str) -> Result<&str, PageChromeError> {
    let start_ix = entry
        .find("\">")
        .map(|ix| ix + 2)
        .ok_or_else(|| PageChromeError::MalformedEntry(entry.to_string()))?;
    let end_ix = entry[start_ix..]
        .find('<')
        .map(|ix| ix + start_ix)
        .ok_or_else(|| PageChromeError::MalformedEntry(entry.to_string()))?;
    Ok(&entry[start_ix..end_ix])
}

/// Find the BBB code embedded in a nav entry by checking `<BBB>.`, `<BBB>_`,
/// and `<BBB>/` substrings against every loaded book code, exactly like
/// html._makeWorkNavListParagraph's detection loop.
fn find_embedded_bbb<'a>(all_bbbs: &'a [String], entry: &str) -> Result<Option<&'a str>, PageChromeError> {
    let mut found_bbb: Option<&str> = None;
    for try_bbb in all_bbbs {
        let found = entry.contains(&format!("{try_bbb}."))
            || entry.contains(&format!("{try_bbb}_"))
            || entry.contains(&format!("{try_bbb}/"));
        if found {
            if found_bbb.is_some() {
                return Err(PageChromeError::MultipleBbbMatches(entry.to_string()));
            }
            found_bbb = Some(try_bbb);
        }
    }
    Ok(found_bbb)
}

/// Pure-Rust equivalent of html.makeTop (including _makeNavigationLinks).
pub fn make_top_core(
    config: &PageChromeConfig,
    level: usize,
    version_abbreviation: Option<&str>,
    page_type: &str,
    file_or_folder: Option<&str>,
) -> Result<String, PageChromeError> {
    let prefix = "../".repeat(level);
    let css_filename = css_filename_for(page_type, version_abbreviation)?;

    // Site / About / News / OET Key links across the very top
    let test_suffix = if config.test_mode_flag { " TEST" } else { "" };
    let home_link = if page_type == "TopIndex" {
        format!("{}{test_suffix} Home", config.site_name)
    } else {
        format!(
            r#"<a href="{prefix}index.htm#Top">{}{test_suffix} Home</a>"#,
            config.site_name
        )
    };
    let about_link = if page_type == "about" {
        "About".to_string()
    } else {
        format!(r#"<a href="{prefix}About.htm#Top">About</a>"#)
    };
    let news_link = if page_type == "news" {
        "News".to_string()
    } else {
        format!(r#"<a href="{prefix}News.htm#Top">News</a>"#)
    };
    let oet_key_link = if page_type == "OETKey" {
        "OET Key".to_string()
    } else {
        format!(r#"<a href="{prefix}OETKey.htm#Top">OET Key</a>"#)
    };
    let top_link = format!(
        "<p class=\"site\">{home_link}{EM_SPACE}{EM_SPACE}{about_link}{EM_SPACE}{EM_SPACE}{news_link}{EM_SPACE}{EM_SPACE}{oet_key_link}</p><!--site-->"
    );

    let mut top = format!(
        "<!DOCTYPE html>\n<html lang=\"en-US\">\n<head>\n\
         \x20 <title>__TITLE__</title>\n\
         \x20 <meta charset=\"utf-8\">\n\
         \x20 <meta name=\"viewport\" content=\"user-scalable=yes, initial-scale=1, minimum-scale=1, width=device-width\">\n\
         \x20 <meta name=\"keywords\" content=\"__KEYWORDS__\">\n\
         \x20 <link rel=\"stylesheet\" type=\"text/css\" href=\"{prefix}{css_filename}\">\n\
         \x20 __SCRIPT__\n\
         </head>\n\
         <body class=\"container\"><!--Level{level}-->{top_link}\n"
    );

    // Insert second stylesheet if required
    if page_type == "OETKey" {
        top = top.replacen(
            "__SCRIPT__",
            &format!(
                "<link rel=\"stylesheet\" type=\"text/css\" href=\"{prefix}OETChapter.css\">\n  __SCRIPT__"
            ),
            1,
        );
    }
    // Insert javascript file(s) if required
    let wants_bible_js = (version_abbreviation.is_some_and(|va| va.contains("OET"))
        && page_type != "sectionIndex")
        || page_type == "parallelVerse"
        || page_type == "topicPassages";
    if wants_bible_js {
        top = top.replacen(
            "__SCRIPT__",
            &format!("<script src=\"{prefix}Bible.js\"></script>\n  __SCRIPT__"),
            1,
        );
    }
    let word_or_dict_css = css_filename.contains("Dict") || css_filename.contains("Word");
    if word_or_dict_css {
        top = top.replacen(
            "__SCRIPT__",
            &format!("<script src=\"{prefix}Dict.js\" defer></script>\n  __SCRIPT__"),
            1,
        );
    }
    if word_or_dict_css || NAV_LINK_PAGE_TYPES_FOR_KB_JS.contains(&page_type) {
        top = top.replacen(
            "__SCRIPT__",
            &format!("<script src=\"{prefix}KB.js\" defer></script>\n  __SCRIPT__"),
            1,
        );
    }
    top = top.replace("\n  __SCRIPT__", "");

    let version_html = work_nav_list_core(config, level, version_abbreviation, page_type, file_or_folder)?;
    let view_html = view_nav_list_core(config, level, version_abbreviation, page_type);

    Ok(format!(
        "{top}<div class=\"header\">{version_html}{}{view_html}</div><!--header-->",
        if view_html.is_empty() { "" } else { "\n" }
    ))
}

/// Pure-Rust equivalent of html._makeWorkNavListParagraph.
fn work_nav_list_core(
    config: &PageChromeConfig,
    level: usize,
    version_abbreviation: Option<&str>,
    page_type: &str,
    file_or_folder: Option<&str>,
) -> Result<String, PageChromeError> {
    let prefix = "../".repeat(level);
    let decoration = |key: &str| -> Result<&[String; 2], PageChromeError> {
        config
            .decorations
            .get(key)
            .ok_or_else(|| PageChromeError::MissingDecoration(key.to_string()))
    };

    let mut initial_version_list: Vec<String> = Vec::new();
    if config.test_mode_flag {
        initial_version_list.push("TEST".to_string());
    }

    for loop_version_abbreviation in &config.bible_versions {
        if NOTES_VERSIONS_TO_SKIP.contains(&loop_version_abbreviation.as_str()) {
            continue;
        }
        if config
            .versions_without_their_own_pages
            .contains(loop_version_abbreviation)
        {
            continue;
        }
        if config
            .test_versions_only
            .as_ref()
            .is_some_and(|tv| !tv.contains(loop_version_abbreviation))
        {
            continue;
        }
        // Rather than leave out versions without sections, we point them to chapter pages below
        let v_link = if Some(loop_version_abbreviation.as_str()) == version_abbreviation {
            prefix.clone()
        } else {
            let safe_name = config.safe_names.get(loop_version_abbreviation).map_or(
                loop_version_abbreviation.as_str(),
                String::as_str,
            );
            match file_or_folder {
                Some(ff) => format!("{prefix}{safe_name}/{ff}"),
                None => format!("{prefix}{safe_name}"),
            }
        };
        let decorations = decoration(loop_version_abbreviation)?;
        let bible_name = config
            .bible_names
            .get(loop_version_abbreviation)
            .ok_or_else(|| PageChromeError::MissingName(loop_version_abbreviation.clone()))?;
        initial_version_list.push(format!(
            "{}<a title=\"{}\" href=\"{}\">{}</a>{}",
            decorations[0], bible_name, v_link, loop_version_abbreviation, decorations[1]
        ));
    }

    // The special-purpose links at the end of the work navigation bar
    let append_pseudo_link = |list: &mut Vec<String>, plain_types: &[&str], label: &str, title: &str, href_tail: &str| -> Result<(), PageChromeError> {
        if plain_types.contains(&page_type) {
            list.push(label.to_string());
        } else {
            let dec = decoration(label)?;
            list.push(format!(
                "{}<a title=\"{}\" href=\"{}{}\">{}</a>{}",
                dec[0], title, prefix, href_tail, label, dec[1]
            ));
        }
        Ok(())
    };
    append_pseudo_link(
        &mut initial_version_list,
        &["relatedPassage", "relatedSectionIndex"],
        "Related",
        "Single OET-RV section with related verses from other books",
        "rel/",
    )?;
    append_pseudo_link(
        &mut initial_version_list,
        &["topicPassages", "topicsIndex"],
        "Topics",
        "Collections of OET passages organised by topic",
        "tpc/",
    )?;
    append_pseudo_link(
        &mut initial_version_list,
        &["parallelVerse"],
        "Parallel",
        "Single verse in many different translations",
        "par/",
    )?;
    append_pseudo_link(
        &mut initial_version_list,
        &["interlinearVerse"],
        "Interlinear",
        "Single verse in interlinear word view",
        "ilr/",
    )?;
    append_pseudo_link(
        &mut initial_version_list,
        &["referenceIndex"],
        "Reference",
        "Reference index",
        "ref/",
    )?;
    append_pseudo_link(
        &mut initial_version_list,
        &["dictionaryMainIndex"],
        "Dictionary",
        "Dictionary index",
        "dct/",
    )?;
    append_pseudo_link(
        &mut initial_version_list,
        &["search"],
        "Search",
        "Find Bible words",
        "Search.htm",
    )?;

    // Adjust links to books which aren't in a particular version
    let mut new_version_list: Vec<String> = Vec::with_capacity(initial_version_list.len());
    for mut entry in initial_version_list {
        if entry.contains("/par/") || entry.contains("/ilr/") {
            new_version_list.push(entry);
            continue; // Should always be able to link to these
        }
        if entry.contains("/bySec/") {
            debug_assert!(page_type == "section" || page_type == "sectionIndex");
            let displayed = extract_displayed_version(&entry)?;
            if !config.have_sections(displayed) {
                entry = entry.replace("/bySec/", "/byC/");
                let masked = entry
                    .replace("/SLT/", "/sLT/")
                    .replace("/SR-GNT/", "/sR-GNT/")
                    .replace("/SA", "/sA")
                    .replace("/SIR", "/sIR")
                    .replace("/SUS", "/sUS")
                    .replace("/SNG", "/sNG");
                if masked.contains("/S") {
                    return Err(PageChromeError::StraySectionReference(entry));
                }
            }
        }
        let entry_bbb = find_embedded_bbb(&config.all_bbbs, &entry)?;
        if let Some(bbb) = entry_bbb {
            let mut displayed = extract_displayed_version(&entry)?.to_string();
            if displayed == "OET" {
                displayed = "OET-RV".to_string(); // We look here in this case
            }
            if config.book_available(&displayed, bbb)? {
                new_version_list.push(entry);
                continue; // Should always be able to link to these
            }
            // Adapt the link up to the next higher-level folder
            let mut replacement = "";
            if let Some(ff) = file_or_folder {
                if let Some(ix) = ff.find('/').filter(|&ix| ix > 0 && ix < ff.len() - 1) {
                    replacement = &ff[..ix + 1];
                }
            } else {
                return Err(PageChromeError::NoFilenameForAdaptation(entry));
            }
            new_version_list.push(entry.replace(file_or_folder.unwrap(), replacement));
        } else {
            new_version_list.push(entry);
        }
    }

    Ok(format!(
        "<p class=\"wrkLst\">{}</p><!--wrkLst-->",
        new_version_list.join(EM_SPACE)
    ))
}

/// Pure-Rust equivalent of html.makeViewNavListParagraph ("ByDocument /
/// BySection" bar). Can return an empty string.
pub fn view_nav_list_core(
    config: &PageChromeConfig,
    level: usize,
    version_abbreviation: Option<&str>,
    page_type: &str,
) -> String {
    let prefix = "../".repeat(level);
    let mut view_links: Vec<String> = Vec::new();

    let applicable_page_type = matches!(
        page_type,
        "book" | "section" | "chapter" | "details" | "workIndex" | "bookIndex" | "sectionIndex"
            | "chapterIndex"
    );
    let not_excluded_version = version_abbreviation
        .is_none_or(|va| !VIEW_BAR_EXCLUDED_VERSIONS.contains(&va))
        && version_abbreviation
            .is_none_or(|va| !config.versions_without_their_own_pages.contains(va));

    if applicable_page_type && not_excluded_version {
        if config.test_mode_flag {
            view_links.push("TEST".to_string());
        }
        let version = match version_abbreviation {
            Some("") | None => "OET",
            Some(va) => va,
        };
        view_links.push(format!(
            "<a title=\"Select a different version\" href=\"{prefix}\">{version}</a>"
        ));
        if !page_type.contains("book") {
            view_links.push(format!(
                "<a title=\"View entire document\" href=\"{prefix}{version}/byDoc/\">By Document</a>"
            ));
        } else {
            view_links.push("By Document".to_string());
        }
        let sections_key = if version == "OET" { "OET-RV" } else { version };
        if config.have_sections(sections_key) {
            if !page_type.contains("section") {
                view_links.push(format!(
                    "<a title=\"View section\" href=\"{prefix}{version}/bySec/\">By Section</a>"
                ));
            } else {
                view_links.push("By Section".to_string());
            }
        }
        if !page_type.contains("chapter") {
            view_links.push(format!(
                "<a title=\"View chapter\" href=\"{prefix}{version}/byC/\">By Chapter</a>"
            ));
        } else {
            view_links.push("By Chapter".to_string());
        }
        if page_type != "details" {
            view_links.push(format!(
                "<a title=\"View version details\" href=\"{prefix}{version}/details.htm#Top\">Details</a>"
            ));
        } else {
            view_links.push("Details".to_string());
        }
        if config.test_mode_flag && version.contains("OET") {
            view_links.push(format!(
                "<a title=\"View verses not included in the OET\" href=\"{prefix}OET/missingVerses.htm#Top\"><small>Missing verses</small></a>"
            ));
        }
    }

    if view_links.is_empty() {
        String::new()
    } else {
        format!(
            "<p class=\"viewLst\">{}</p><!--viewLst-->",
            view_links.join(EM_SPACE)
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Build a config mirroring the stub State used by golden_makeTop.py so
    /// expectations stay aligned between the two test approaches.
    pub(crate) fn test_config() -> PageChromeConfig {
        let bbbs = ["FRT", "GEN", "EXO", "PSA", "ISA", "MRK", "GAL"]
            .iter()
            .map(|s| s.to_string())
            .collect::<Vec<_>>();
        let ot_books = ["GEN", "EXO", "PSA", "ISA"]
            .iter()
            .map(|s| s.to_string())
            .collect::<HashSet<_>>();
        let nt_books = ["MRK", "GAL"]
            .iter()
            .map(|s| s.to_string())
            .collect::<HashSet<_>>();
        let bold = ["<b>".to_string(), "</b>".to_string()];
        let plain = [String::new(), String::new()];
        let all_books = bbbs.iter().cloned().collect::<HashSet<_>>();
        PageChromeConfig {
            test_mode_flag: true,
            site_name: "Open Bible Data".to_string(),
            bible_versions: [
                "OET", "OET-RV", "OET-LV", "UHB", "SR-GNT", "T4T", "LSV", "TOSN",
            ]
            .iter()
            .map(|s| s.to_string())
            .collect(),
            versions_without_their_own_pages: ["Luth", "ClVg", "UGNT", "SBL-GNT", "RP-GNT", "TC-GNT", "TOSN", "SOTN", "UTN"]
                .iter()
                .map(|s| s.to_string())
                .collect(),
            test_versions_only: None,
            safe_names: [
                ("OET", "OET"),
                ("OET-RV", "OET-RV"),
                ("OET-LV", "OET-LV"),
                ("UHB", "UHB"),
                ("SR-GNT", "SR-GNT"),
                ("T4T", "T4T"),
                ("LSV", "LSV"),
            ]
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect(),
            decorations: [
                ("OET", bold.clone()),
                ("OET-RV", bold.clone()),
                ("OET-LV", bold.clone()),
                ("UHB", bold.clone()),
                ("SR-GNT", bold.clone()),
                ("T4T", plain.clone()),
                ("LSV", plain.clone()),
                ("Related", bold.clone()),
                ("Topics", bold.clone()),
                ("Parallel", bold.clone()),
                ("Interlinear", bold.clone()),
                ("Reference", bold.clone()),
                ("Dictionary", bold.clone()),
                ("Search", bold.clone()),
            ]
            .iter()
            .map(|(k, v)| (k.to_string(), v.clone()))
            .collect(),
            bible_names: [
                ("OET", "Open English Translation (2030)"),
                ("OET-RV", "Open English Translation—Readers’ Version (2030)"),
                ("OET-LV", "Open English Translation—Literal Version (2026)"),
                ("UHB", "Unlocked Hebrew Bible"),
                ("SR-GNT", "Systematic Romanized Greek New Testament"),
                ("T4T", "Translators Translation"),
                ("LSV", "Literal Standard Version"),
            ]
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect(),
            all_bbbs: bbbs,
            have_section_headings: ["OET-RV", "OET-LV", "UHB", "SR-GNT"]
                .iter()
                .map(|s| s.to_string())
                .collect(),
            version_books: [
                ("OET-RV", all_books.clone()),
                ("OET-LV", all_books.clone()),
                ("UHB", ot_books),
                ("SR-GNT", nt_books),
                ("T4T", all_books.clone()),
                ("LSV", all_books),
            ]
            .iter()
            .map(|(k, v)| (k.to_string(), v.clone()))
            .collect(),
        }
    }

    #[test]
    fn test_basic_chapter_page_structure() {
        let cfg = test_config();
        let top = make_top_core(&cfg, 2, Some("OET-RV"), "chapter", Some("byC/GEN_C1.htm"))
            .expect("should build");
        assert!(top.starts_with("<!DOCTYPE html>\n<html lang=\"en-US\">\n<head>\n  <title>__TITLE__</title>"));
        assert!(top.contains("href=\"../../OETChapter.css\""));
        assert!(top.contains("<!--Level2-->"));
        assert!(top.contains("__KEYWORDS__"));
        assert!(!top.contains("__SCRIPT__")); // placeholders must be resolved
        // Bible.js because OET version + KB.js because chapter page type
        assert!(top.contains("<script src=\"../../Bible.js\"></script>"));
        assert!(top.contains("<script src=\"../../KB.js\" defer></script>"));
        assert!(!top.contains("Dict.js"));
        // Header contains both bars
        assert!(top.contains(r#"<div class="header"><p class="wrkLst">"#));
        assert!(top.contains("</div><!--header-->"));
        assert!(top.contains("<p class=\"site\">"));
    }

    #[test]
    fn test_non_oet_chapter_css_and_no_bible_js() {
        let cfg = test_config();
        let top = make_top_core(&cfg, 1, Some("UHB"), "chapter", Some("byC/GEN_C1.htm")).unwrap();
        assert!(top.contains("BibleChapter.css"));
        assert!(!top.contains("Bible.js")); // UHB doesn't contain 'OET'
        assert!(top.contains("KB.js"));
    }

    #[test]
    fn test_work_list_skips_notes_and_unpaged_versions() {
        let cfg = test_config();
        let top = make_top_core(&cfg, 2, Some("OET-RV"), "chapter", Some("byC/GEN_C1.htm")).unwrap();
        let wrk_start = top.find("<p class=\"wrkLst\">").unwrap();
        let wrk_end = top.find("<!--wrkLst-->").unwrap();
        let wrk = &top[wrk_start..wrk_end];
        assert!(wrk.contains(">TEST<") || wrk.contains("TEST\u{2003}")); // TEST first
        assert!(!wrk.contains(">TOSN<")); // notes skipped
    }

    #[test]
    fn test_bysec_rewrite_and_book_adaptation_on_section_pages() {
        let cfg = test_config();
        // Mirrors verified Python behaviour for a T4T section page:
        // - versions WITH headings keep bySec links
        // - versions WITHOUT headings get bySec->byC
        // - versions without the book get adapted up one folder (UHB: no MRK)
        let top = make_top_core(&cfg, 2, Some("T4T"), "section", Some("bySec/MRK_S5.htm")).unwrap();
        let wrk = &top[top.find("<p class=\"wrkLst\">").unwrap()..top.find("<!--wrkLst-->").unwrap()];
        assert!(wrk.contains("href=\"../../OET/bySec/MRK_S5.htm\""));
        assert!(wrk.contains("href=\"../../SR-GNT/bySec/MRK_S5.htm\""));
        assert!(wrk.contains("href=\"../../LSV/byC/MRK_S5.htm\"")); // no section headings
        assert!(!wrk.contains("/bySec/LSV/"));
        assert!(wrk.contains("href=\"../../UHB/bySec/\"")); // OT-only: MRK missing
        // The current version (T4T) gets a bare prefix link without any filename
        assert!(wrk.contains("href=\"../../\">T4T</a>") || wrk.contains(">T4T<"));
    }

    #[test]
    fn test_no_adaptation_when_all_versions_have_the_book() {
        let cfg = test_config();
        // Everyone but SR-GNT itself carries GEN, and SR-GNT is the current
        // version here, so nothing may be rewritten
        let top = make_top_core(&cfg, 2, Some("SR-GNT"), "chapter", Some("byC/GEN_C1.htm")).unwrap();
        let wrk = &top[top.find("<p class=\"wrkLst\">").unwrap()..top.find("<!--wrkLst-->").unwrap()];
        assert!(wrk.contains("href=\"../../UHB/byC/GEN_C1.htm\""));
        assert!(wrk.contains("href=\"../../OET/byC/GEN_C1.htm\""));
        assert!(!wrk.contains("\">GEN")); // sanity: entries link versions, not books
    }

    #[test]
    fn test_view_bar_contents_for_chapter_page() {
        let cfg = test_config();
        let top = make_top_core(&cfg, 2, Some("OET-RV"), "chapter", Some("byC/PSA_C23.htm")).unwrap();
        let view = &top[top.find("<p class=\"viewLst\">").unwrap()..top.find("<!--viewLst-->").unwrap()];
        assert!(view.contains("viewLst\">TEST\u{2003}")); // TEST entry comes first
        assert!(view.contains("<a title=\"Select a different version\" href=\"../../\">OET-RV</a>"));
        assert!(view.contains("<a title=\"View entire document\" href=\"../../OET-RV/byDoc/\">By Document</a>"));
        assert!(view.contains("By Section")); // OET-RV has section headings
        assert!(view.contains("By Chapter")); // plain label on chapter pages
        assert!(!view.contains("/byC/")); // ...so no By Chapter link
        assert!(view.contains("<a title=\"View version details\" href=\"../../OET-RV/details.htm#Top\">Details</a>"));
        assert!(view.contains("Missing verses")); // TEST mode + OET version
    }

    #[test]
    fn test_view_bar_empty_for_parallel_pages() {
        let cfg = test_config();
        let top = make_top_core(&cfg, 1, None, "parallelVerse", Some("GAL_3_16.htm")).unwrap();
        assert!(top.trim_end().ends_with("</div><!--header-->"));
        assert!(!top.contains("viewLst"));
    }

    #[test]
    fn test_pseudo_plain_labels_on_own_page_types() {
        let cfg = test_config();
        let top = make_top_core(&cfg, 0, None, "topicPassages", None).unwrap();
        let wrk = &top[top.find("<p class=\"wrkLst\">").unwrap()..top.find("<!--wrkLst-->").unwrap()];
        assert!(wrk.contains("\u{2003}Topics\u{2003}")); // plain, unlinked Topics
        assert!(!wrk.contains("/tpc/")); // ...so no Topics link at all
        assert!(wrk.contains("href=\"par/\"")); // the other pseudo links stay live
        assert!(wrk.contains("href=\"rel/\""));
        assert!(top.contains("TopicalPassages.css"));
    }

    #[test]
    fn test_oetkey_extra_stylesheet() {
        let cfg = test_config();
        let top = make_top_core(&cfg, 1, Some("OET-RV"), "OETKey", None).unwrap();
        assert!(top.contains("BibleSite.css"));
        assert!(top.contains("OETChapter.css")); // second stylesheet injected
    }

    #[test]
    fn test_unknown_page_type_errors() {
        let cfg = test_config();
        assert_eq!(
            make_top_core(&cfg, 1, Some("OET-RV"), "kingdomIndex", None),
            Err(PageChromeError::UnknownPageType("kingdomIndex".to_string()))
        );
    }

    #[test]
    fn test_not_preloaded_errors_outside_test_mode() {
        let mut cfg = test_config();
        cfg.test_mode_flag = false;
        // Remove LSV's preloaded book set: its nav entry then can't be checked
        cfg.version_books.remove("LSV");
        // UHB is current (so gets a plain link); LSV gets a full GEN link whose
        // availability must now fail hard instead of being silently guessed
        assert!(matches!(
            make_top_core(&cfg, 1, Some("UHB"), "chapter", Some("byC/GEN_C1.htm")),
            Err(PageChromeError::NotPreloaded(ref key)) if key == "LSV"
        ));
    }

    #[test]
    fn test_word_page_gets_dict_scripts() {
        let cfg = test_config();
        let top = make_top_core(&cfg, 1, None, "word", Some("AGAPAW.htm")).unwrap();
        assert!(top.contains("BibleWord.css"));
        assert!(top.contains("Dict.js"));
        assert!(top.contains("KB.js"));
        assert!(!top.contains("Bible.js")); // word pages don't get Bible.js
    }
}

