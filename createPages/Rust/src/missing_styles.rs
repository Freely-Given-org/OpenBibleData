//! Fast CSS stylesheet loading and missing-style checking for generated pages.
//!
//! Rust port of `html.loadCSSStyles()` and `html.checkHtmlForMissingStyles()`.
//! The Python versions scan every line of every page with a regex (plus a
//! per-page dict copy/merge), which costs ~1 ms per page over a ~1.3M-page
//! site build.  This module keeps the parsed stylesheets (and the page+common
//! merged lookup) in static caches populated once per process, does the
//! per-line scan in one pass, and returns only the missing `(element, class)`
//! pairs for Python to report (byte-identical messages to the old code).

use std::collections::{HashMap, HashSet};
use std::sync::{Arc, Mutex};

use once_cell::sync::Lazy;
use regex::Regex;

use bos_internals::have_strict_checking_flag;

/// `<tag ... class="...">` regex (byte-identical to Python's `classRegex`).
static CLASS_REGEX: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r#"<([^>]+?) [^>]*?class="([^>"]+?)""#).expect("valid class regex")
});

/// class name -> element names styled by it.
/// An empty-string element entry means 'any element' (from generic selectors
/// like `.hebVrb {`), matching how Python treats an empty entry in the list.
type ElementSet = HashSet<String>;
pub type ClassMap = HashMap<String, ElementSet>;

/// Parsed per-stylesheet class maps, keyed by stylesheet name.
static CSS_PARSE_CACHE: Lazy<Mutex<HashMap<String, Arc<ClassMap>>>> =
    Lazy::new(|| Mutex::new(HashMap::new()));
/// Merged page-stylesheet+common.css maps, keyed by page stylesheet name.
static MERGED_CACHE: Lazy<Mutex<HashMap<String, Arc<ClassMap>>>> =
    Lazy::new(|| Mutex::new(HashMap::new()));

/// Every stylesheet that can appear in a page's <head>.
///   (Hand-kept in step with Python html.PAGE_STYLESHEET_NAMES.)
pub const PAGE_STYLESHEET_NAMES: [&str; 9] = [
    "OETChapter.css",
    "BibleChapter.css",
    "ParallelPassages.css",
    "TopicalPassages.css",
    "ParallelVerses.css",
    "InterlinearVerse.css",
    "BibleWord.css",
    "BibleDict.css",
    "BibleSite.css",
];

/// Keep the Python `assert <cond>, <msg>` checks, gated by the strict-checking
/// flag (which a non-strict build leaves unset, like Python running with -O).
fn strict_check(strict: bool, ok: bool, msg: impl Into<String>) -> Result<(), String> {
    if strict && !ok {
        Err(format!("AssertionError: {}", msg.into()))
    } else {
        Ok(())
    }
}

/// Parse the lines of one .css file into a class map, exactly like
/// `html.loadCSSStyles` (including its `' + '` skip and `common.css` line-wrap
/// `removesuffix(',\n')` handling).  Lines are split inclusively on '\n' so the
/// trailing newline is present exactly as it was when Python iterated the file.
pub fn parse_css_text(stylesheet_name: &str, text: &str) -> Result<ClassMap, String> {
    let strict = have_strict_checking_flag() || cfg!(debug_assertions);
    let mut map: ClassMap = HashMap::new();

    // common.css has some class names wrapping a line with a trailing ',\n'
    fn unwrap_common_suffix<'a>(stylesheet_name: &str, class_name: &'a str) -> &'a str {
        if stylesheet_name == "common.css" {
            class_name.strip_suffix(",\n").unwrap_or(class_name)
        } else {
            class_name
        }
    }

    for ss_line in text.split_inclusive('\n') {
        if ss_line.contains(" + ") {
            continue; // Don't need these
        }

        if let Some(tail) = ss_line.strip_prefix("select.") {
            let class_name =
                unwrap_common_suffix(stylesheet_name, tail.split(' ').next().unwrap_or(""))
                    .to_string();
            strict_check(
                strict,
                !class_name.contains(' ') && !class_name.contains(','),
                format!("select class {class_name:?}"),
            )?;
            map.entry(class_name).or_default().insert("select".to_string());
        } else if let Some(tail) = ss_line.strip_prefix("button.") {
            let class_name = tail
                .splitn(2, '{') // split( '{', 1 )[0]
                .next()
                .unwrap_or("")
                .replace(':', ",") // replace( ':', ',' )
                .splitn(2, ',') // split( ',', 1 )[0]
                .next()
                .unwrap_or("")
                .trim_end() // rstrip()
                .to_string();
            strict_check(
                strict,
                !class_name.contains(' ') && !class_name.contains(','),
                format!("button class {class_name:?}"),
            )?;
            map.entry(class_name).or_default().insert("button".to_string());
        } else if let Some(tail) = ss_line.strip_prefix("span.") {
            let class_name =
                unwrap_common_suffix(stylesheet_name, tail.split(' ').next().unwrap_or(""))
                    .to_string();
            strict_check(
                strict,
                !class_name.contains(' ') && !class_name.contains(','),
                format!("span class {class_name:?}"),
            )?;
            let lst = map.entry(class_name.clone()).or_default();
            if stylesheet_name != "common.css" {
                strict_check(
                    strict,
                    !lst.contains("span"),
                    format!("span.{class_name} already in {stylesheet_name}"),
                )?;
            }
            lst.insert("span".to_string());
        } else if let Some(tail) = ss_line.strip_prefix("p.") {
            let class_names = tail.split(' ').next().unwrap_or("").to_string();
            for class_name in class_names.split(',') {
                let class_name = class_name.replace("p.", "");
                strict_check(
                    strict,
                    !class_name.contains(' ') && !class_name.contains(','),
                    format!("p class {class_name:?}"),
                )?;
                let lst = map.entry(class_name.clone()).or_default();
                if stylesheet_name != "common.css" {
                    strict_check(
                        strict,
                        !lst.contains("p"),
                        format!("p.{class_name} already in {stylesheet_name}"),
                    )?;
                }
                lst.insert("p".to_string());
            }
        } else if let Some(tail) = ss_line.strip_prefix("div.") {
            // Python: className, rest = ssLine[4:].split( ' ', 1 )
            let (class_name, rest) = tail.split_once(' ').ok_or_else(|| {
                format!("ValueError: div selector without a space: {ss_line:?}")
            })?;
            let class_name = class_name.to_string();
            strict_check(
                strict,
                !class_name.contains(' ') && !class_name.contains(','),
                format!("div class {class_name:?}"),
            )?;
            let lst = map.entry(class_name.clone()).or_default();
            if stylesheet_name != "common.css" {
                strict_check(
                    strict,
                    !lst.contains("div"),
                    format!("div.{class_name} already in {stylesheet_name}"),
                )?;
            }
            lst.insert("div".to_string());
            if rest.starts_with("div.") {
                // Handle a line like 'div.topLine div.themeControls {'
                let class_name = rest[4..].split(' ').next().unwrap_or("").to_string();
                strict_check(
                    strict,
                    !class_name.contains(' ') && !class_name.contains(','),
                    format!("div class {class_name:?}"),
                )?;
                let lst = map.entry(class_name.clone()).or_default();
                if stylesheet_name != "common.css" {
                    strict_check(
                        strict,
                        !lst.contains("div"),
                        format!("div.{class_name} already in {stylesheet_name}"),
                    )?;
                }
                lst.insert("div".to_string());
            }
        } else if ss_line.starts_with("h1.") || ss_line.starts_with("h2.") {
            let element_name = &ss_line[..2]; // 'h1' or 'h2'
            let mut class_name = ss_line[3..].split(' ').next().unwrap_or("").to_string();
            if class_name.ends_with(',') {
                // Can have h1.PromisedLand, p.PromisedLand { color:gold; }
                class_name.pop();
            }
            strict_check(
                strict,
                !class_name.contains(' ') && !class_name.contains(','),
                format!("{element_name} class {class_name:?}"),
            )?;
            let lst = map.entry(class_name.clone()).or_default();
            strict_check(
                strict,
                !lst.contains(element_name),
                format!("{element_name}.{class_name} already in {stylesheet_name}"),
            )?;
            lst.insert(element_name.to_string());
        } else if let Some(tail) = ss_line.strip_prefix("ol.") {
            let class_name = tail.split(' ').next().unwrap_or("").to_string();
            strict_check(
                strict,
                !class_name.contains(' ') && !class_name.contains(','),
                format!("ol class {class_name:?}"),
            )?;
            if class_name != "verse" {
                // In InterlinearVerse.css these are specified for each language
                let lst = map.entry(class_name.clone()).or_default();
                strict_check(
                    strict,
                    !lst.contains("ol"),
                    format!("ol.{class_name} already in {stylesheet_name}"),
                )?;
            }
            map.entry(class_name).or_default().insert("ol".to_string());
        } else if let Some(tail) = ss_line.strip_prefix("li.") {
            let class_name = tail.split(' ').next().unwrap_or("").to_string();
            strict_check(
                strict,
                !class_name.contains(' ') && !class_name.contains(','),
                format!("li class {class_name:?}"),
            )?;
            let lst = map.entry(class_name.clone()).or_default();
            strict_check(
                strict,
                !lst.contains("li"),
                format!("li.{class_name} already in {stylesheet_name}"),
            )?;
            lst.insert("li".to_string());
        } else if let Some(tail) = ss_line.strip_prefix("body.") {
            let class_name = tail.split(' ').next().unwrap_or("").to_string();
            strict_check(
                strict,
                !class_name.contains(' ') && !class_name.contains(','),
                format!("body class {class_name:?}"),
            )?;
            let lst = map.entry(class_name.clone()).or_default();
            strict_check(
                strict,
                !lst.contains("body"),
                format!("body.{class_name} already in {stylesheet_name}"),
            )?;
            lst.insert("body".to_string());
        } else if let Some(tail) = ss_line.strip_prefix("img.") {
            let class_name = tail.split(' ').next().unwrap_or("").to_string();
            strict_check(
                strict,
                !class_name.contains(' ') && !class_name.contains(','),
                format!("img class {class_name:?}"),
            )?;
            let lst = map.entry(class_name.clone()).or_default();
            strict_check(
                strict,
                !lst.contains("img"),
                format!("img.{class_name} already in {stylesheet_name}"),
            )?;
            lst.insert("img".to_string());
        } else if let Some(tail) = ss_line.strip_prefix("hr.") {
            let class_name = tail.split(' ').next().unwrap_or("").to_string();
            strict_check(
                strict,
                !class_name.contains(' ') && !class_name.contains(','),
                format!("hr class {class_name:?}"),
            )?;
            let lst = map.entry(class_name.clone()).or_default();
            strict_check(
                strict,
                !lst.contains("hr"),
                format!("hr.{class_name} already in {stylesheet_name}"),
            )?;
            lst.insert("hr".to_string());
        } else if let Some(tail) = ss_line.strip_prefix("a.") {
            let class_name = tail.split(' ').next().unwrap_or("").to_string();
            strict_check(
                strict,
                !class_name.contains(' ') && !class_name.contains(','),
                format!("a class {class_name:?}"),
            )?;
            let lst = map.entry(class_name.clone()).or_default();
            strict_check(
                strict,
                !lst.contains("a"),
                format!("a.{class_name} already in {stylesheet_name}"),
            )?;
            lst.insert("a".to_string());
        } else if let Some(tail) = ss_line.strip_prefix('.') {
            let class_name = tail.split(' ').next().unwrap_or("").to_string();
            strict_check(
                strict,
                !class_name.contains(' ') && !class_name.contains(','),
                format!(".class {class_name:?}"),
            )?;
            // Skip selectors like '.wrkLst a {' that style a nested element
            let after = class_name.len() + 2;
            if !ss_line[after..].starts_with("a {") {
                let lst = map.entry(class_name.clone()).or_default();
                strict_check(
                    strict,
                    lst.is_empty(),
                    format!(".{class_name} already in {stylesheet_name}"),
                )?;
                lst.insert(String::new()); // '' means 'any element'
            }
        }
    }
    Ok(map)
}

/// Read (and cache) one stylesheet's parsed class map from disk.
fn read_css(stylesheet_name: &str) -> Result<Arc<ClassMap>, String> {
    if let Some(cached) = CSS_PARSE_CACHE.lock().unwrap().get(stylesheet_name) {
        return Ok(cached.clone());
    }
    let filename = if stylesheet_name.contains("pagefind") {
        format!("../htmlPages/{stylesheet_name}")
    } else {
        stylesheet_name.to_string()
    };
    let text = std::fs::read_to_string(&filename).map_err(|err| {
        format!(
            "Error: loadCSSStyles couldn't read {stylesheet_name} from {filename}: {err}"
        )
    })?;
    let parsed = Arc::new(parse_css_text(stylesheet_name, &text)?);
    CSS_PARSE_CACHE
        .lock()
        .unwrap()
        .insert(stylesheet_name.to_string(), parsed.clone());
    Ok(parsed)
}

/// The lookup used while scanning a page: the page's own stylesheet unioned
/// with common.css (elements not already present appended), exactly like the
/// `styleDict` html.checkHtmlForMissingStyles builds.  Cached per stylesheet.
pub fn merged_style_map(stylesheet_name: &str) -> Result<Arc<ClassMap>, String> {
    if let Some(cached) = MERGED_CACHE.lock().unwrap().get(stylesheet_name) {
        return Ok(cached.clone());
    }
    let mut merged = (*read_css(stylesheet_name)?).clone();
    for (class, elements) in read_css("common.css")?.iter() {
        let dst = merged.entry(class.clone()).or_default();
        for element in elements {
            dst.insert(element.clone());
        }
    }
    let merged = Arc::new(merged);
    MERGED_CACHE
        .lock()
        .unwrap()
        .insert(stylesheet_name.to_string(), merged.clone());
    Ok(merged)
}

/// Scan `html` for classes missing from the page's stylesheet(s).
///
/// Returns the `(elementName, className, stylesheetName)` triples for every
/// occurrence that fails the check, byte-identical to the messages
/// `html.checkHtmlForMissingStyles` collects.  Like the Python version, the
/// scan starts after the first `rel="stylesheet"` line, and
/// `where == "OETKey"` disables scanning while still detecting stylesheets.
pub fn check_html_for_missing_styles(
    where_: &str,
    html: &str,
) -> Result<Vec<(String, String, String)>, String> {
    let mut started_check = false;
    let mut stylesheet_name = String::new();
    let mut style_map: Option<Arc<ClassMap>> = None;
    let mut missing: Vec<(String, String, String)> = Vec::new();

    for line in html.split('\n') {
        if !started_check || where_ == "OETKey" {
            if line.contains("rel=\"stylesheet\"") {
                let ix_start = line.find("href=\"").ok_or_else(|| {
                    format!(
                        "ValueError: checkHtmlForMissingStyles({where_}) stylesheet line without href=\": {line:?}"
                    )
                })?;
                let after = ix_start + 6;
                let ix_end = line[after..]
                    .find("\">")
                    .map(|ix| after + ix)
                    .ok_or_else(|| {
                        format!(
                            "ValueError: checkHtmlForMissingStyles({where_}) stylesheet line without '\">': {line:?}"
                        )
                    })?;
                stylesheet_name = line[after..ix_end].replace("../", "");
                style_map = Some(merged_style_map(&stylesheet_name)?);
                started_check = true;
            }
        } else if let Some(map) = &style_map {
            for caps in CLASS_REGEX.captures_iter(line) {
                let element_name = &caps[1];
                for class_name in caps[2].split(' ') {
                    let found = map.get(class_name).is_some_and(|elements| {
                        elements.contains(element_name) || elements.contains("")
                    });
                    if !found {
                        missing.push((
                            element_name.to_string(),
                            class_name.to_string(),
                            stylesheet_name.clone(),
                        ));
                    }
                }
            }
        }
    }
    Ok(missing)
}

/// Parse and cache every page stylesheet (merged with common.css) so forked
/// multiprocessing children inherit the caches copy-on-write.
pub fn preload_css_styles() -> Result<(), String> {
    for stylesheet_name in PAGE_STYLESHEET_NAMES {
        merged_style_map(stylesheet_name)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn seed(stylesheet_name: &str, map: ClassMap) {
        CSS_PARSE_CACHE
            .lock()
            .unwrap()
            .insert(stylesheet_name.to_string(), Arc::new(map));
        // Force any previously merged entry to be rebuilt from this seed.
        MERGED_CACHE
            .lock()
            .unwrap()
            .remove(stylesheet_name);
    }

    #[test]
    fn parses_all_selector_kinds() {
        let css = "\
select.lang { color:black; }\n\
button.minus:hover { color:red; }\n\
button.x:active { color:blue; }\n\
span.wj { color:red; }\n\
p.verseText, p.verseText2 { color:black; }\n\
div.topLine div.themeControls { color:black; }\n\
h1.PromisedLand, p.PromisedLand { color:gold; }\n\
ol.verse { color:black; }\n\
ol.foo { color:black; }\n\
li.foo { color:black; }\n\
body.container { color:black; }\n\
img.icon { color:black; }\n\
hr.foo { color:black; }\n\
a.PLS { color:black; }\n\
.wrkLst a { color:white; }\n\
.hebVrb { color:black; }\n";
        let map = parse_css_text("Test.css", css).unwrap();
        assert!(map["lang"].contains("select"));
        assert!(map["minus"].contains("button"));
        assert!(map["x"].contains("button"));
        assert!(map["wj"].contains("span"));
        assert!(map["verseText"].contains("p"));
        // 'p.verseText, p.verseText2 {' only yields 'verseText' + '' (the empty
        // class name left by the trailing comma) -- matching Python's split.
        assert!(map[""].contains("p"));
        assert!(map["topLine"].contains("div")); // 'div.topLine div.themeControls'
        assert!(map["themeControls"].contains("div"));
        assert!(map["PromisedLand"].contains("h1"));
        assert!(map["verse"].contains("ol"));
        assert!(map["foo"].contains("ol"));
        assert!(map["foo"].contains("li"));
        assert!(map["container"].contains("body"));
        assert!(map["icon"].contains("img"));
        assert!(map["PLS"].contains("a"));
        // '.wrkLst a {' is skipped entirely; '.hebVrb {' means any element
        assert!(!map.contains_key("wrkLst"));
        assert!(map["hebVrb"].contains(""));
    }

    #[test]
    fn common_css_line_wrap_suffix() {
        // common.css wraps multi-selector lines with a trailing ',\n'
        let css = "span.v,\nspan.c { color:black; }\n";
        let map = parse_css_text("common.css", css).unwrap();
        assert!(map["v"].contains("span"));
        assert!(map["c"].contains("span"));
        // Non-common stylesheets keep the wrapped suffix as the class name,
        // which Python's loadCSSStyles then rejects (strict builds assert).
        let strict = have_strict_checking_flag() || cfg!(debug_assertions);
        if strict {
            let err = parse_css_text("Other.css", css).unwrap_err();
            assert!(err.starts_with("AssertionError: span class \"v,\\n\""), "{err}");
        } else {
            let map = parse_css_text("Other.css", css).unwrap();
            assert!(map["c"].contains("span"));
            assert_eq!(map[&"v,\n".to_string()].contains("span"), true);
        }
    }

    #[test]
    fn merges_common_css_elements() {
        seed(
            "MergeTest.css",
            HashMap::from([
                ("d".to_string(), HashSet::from(["span".to_string()])),
                ("own".to_string(), HashSet::from(["p".to_string()])),
            ]),
        );
        seed(
            "common.css",
            HashMap::from([
                ("d".to_string(), HashSet::from(["p".to_string()])),
                ("shared".to_string(), HashSet::from(["div".to_string()])),
            ]),
        );
        let merged = merged_style_map("MergeTest.css").unwrap();
        // span.d from Test.css isn't clobbered by p.d from common.css
        assert!(merged["d"].contains("span"));
        assert!(merged["d"].contains("p"));
        assert!(merged["own"].contains("p"));
        assert!(merged["shared"].contains("div"));
    }

    #[test]
    fn detects_missing_classes_after_stylesheet() {
        seed("ScanTest.css", HashMap::from([("ok".to_string(), HashSet::new())]));
        let mut merged: ClassMap = HashMap::from([("ok".to_string(), HashSet::from(["span".to_string()]))]);
        merged.insert("any".to_string(), HashSet::from([String::new()]));
        merged.insert("owned".to_string(), HashSet::from(["p".to_string()]));
        MERGED_CACHE
            .lock()
            .unwrap()
            .insert("ScanTest.css".to_string(), Arc::new(merged));

        let html = "<html><head>\n\
            <link rel=\"stylesheet\" type=\"text/css\" href=\"../ScanTest.css\">\n\
            </head><body>\n\
            <span class=\"ok\"></span>\n\
            <span class=\"bad\"></span>\n\
            <div class=\"any\"></div>\n\
            <p class=\"owned\"></p>\n\
            <p class=\"missing\"></p>\n\
            </body></html>";
        let missing = check_html_for_missing_styles("where", html).unwrap();
        let pairs: Vec<(&String, &String)> =
            missing.iter().map(|(e, c, _)| (e, c)).collect();
        assert!(pairs.contains(&(&"span".to_string(), &"bad".to_string())));
        assert!(pairs.contains(&(&"p".to_string(), &"missing".to_string())));
        // ok (present), any++ (empty-string wildcard) and owned are not missing
        assert_eq!(
            pairs
                .iter()
                .filter(|(_, c)| c.as_str() == "bad")
                .count(),
            1
        );
        assert!(!pairs.iter().any(|(_, c)| c.as_str() == "ok"));
        assert!(!pairs.iter().any(|(_, c)| c.as_str() == "owned"));
        assert!(!pairs.iter().any(|(_, c)| c.as_str() == "any"));
    }

    #[test]
    fn oetkey_disables_scanning() {
        seed("OetKeyTest.css", HashMap::new());
        MERGED_CACHE
            .lock()
            .unwrap()
            .insert("OetKeyTest.css".to_string(), Arc::new(HashMap::new()));
        let html = "<head>\n<link rel=\"stylesheet\" type=\"text/css\" href=\"../OetKeyTest.css\">\n\
            </head>\n<span class=\"nope\"></span>\n";
        let missing = check_html_for_missing_styles("OETKey", html).unwrap();
        assert!(missing.is_empty());
        // A non-OETKey where value does scan
        let missing = check_html_for_missing_styles("SomePage", html).unwrap();
        assert_eq!(missing.len(), 1);
        assert_eq!(missing[0].0, "span");
        assert_eq!(missing[0].1, "nope");
        assert_eq!(missing[0].2, "OetKeyTest.css");
    }

    #[test]
    fn href_replaces_all_parent_links() {
        seed("HrefTest.css", HashMap::new());
        MERGED_CACHE
            .lock()
            .unwrap()
            .insert("HrefTest.css".to_string(), Arc::new(HashMap::new()));
        let html = "<link rel=\"stylesheet\" type=\"text/css\" href=\"../../../HrefTest.css\">\n\
            <span class=\"gone\"></span>\n";
        let missing = check_html_for_missing_styles("where", html).unwrap();
        assert_eq!(missing.len(), 1);
        assert_eq!(missing[0].2, "HrefTest.css");
    }

    #[test]
    fn page_with_no_stylesheet_is_not_scanned() {
        let missing = check_html_for_missing_styles("where", "<span class=\"x\"></span>").unwrap();
        assert!(missing.is_empty());
    }
}