//! Fast HTML validation checks for generated pages.
//!
//! Implements the same checks as `html.checkHtml()` in Python but in pure Rust,
//! avoiding Python interpreter overhead for the inner loops that run ~500K+ times
//! per site build.

use pyo3::prelude::*;
use once_cell::sync::Lazy;
use regex::Regex;

use bos_internals::have_strict_checking_flag;

// ── Pre-compiled regexes (compiled once, reused across all calls) ──────────
static CLASS_ATTR_RE: Lazy<Regex> =
    Lazy::new(|| Regex::new(r#"class="([^"]+?)""#).unwrap());
static ID_ATTR_RE: Lazy<Regex> =
    Lazy::new(|| Regex::new(r#"id="([^"]+?)""#).unwrap());
static TITLE_ATTR_RE: Lazy<Regex> =
    Lazy::new(|| Regex::new(r#"title="([^"]+?)""#).unwrap());

// ── Result type ────────────────────────────────────────────────────────────
/// Every check returns either `Ok(())` or `Err(message)`.
pub type HtmlCheckResult = Result<(), String>;

// ── Helpers ────────────────────────────────────────────────────────────────
/// Return a short context snippet around `ix` in `s`.
fn snippet(s: &str, ix: usize, before: usize, after: usize) -> String {
    let start = ix.saturating_sub(before);
    let end = (ix + after).min(s.len());
    format!("…{}…", &s[start..end])
}

/// Count non-overlapping occurrences of `needle` in `haystack`.
fn count_sub(haystack: &str, needle: &str) -> usize {
    haystack.matches(needle).count()
}

// ── Main validation entry point ────────────────────────────────────────────
/// Run every check that `html.checkHtml()` performs (segment-only and full-page).
///
/// Returns `Ok(())` on success, or `Err(message)` with a human-readable
/// description of the first problem found.
pub fn check_html(html: &str, where_: &str, segment_only: bool) -> HtmlCheckResult {
    let strict = have_strict_checking_flag() || cfg!(debug_assertions);

    // ── 1. Double newlines ─────────────────────────────────────────────────
    if let Some(ix) = html.find("\n\n") {
        return Err(format!(
            "checkHtml({}) found unexpected double newlines in {}",
            where_,
            snippet(html, ix, 30, 50),
        ));
    }

    // ── 2. <br> followed by newline ────────────────────────────────────────
    if let Some(ix) = html.find("<br>\n") {
        return Err(format!(
            "checkHtml({}) found <br> followed by unexpected newline in {}",
            where_,
            snippet(html, ix, 30, 50),
        ));
    }

    // ── 2b. <br> immediately before a closing </span> ──────────────────────
    //  A <br> is a self-closing void element; putting one right before the
    //  closing </span> of a surrounding span leaves that tag orphaned after the
    //  break (the same class of problem as a <br> before a newline, above).
    if let Some(ix) = html.find("<br></span>") {
        return Err(format!(
            "checkHtml({}) found <br> immediately before </span> in {}",
            where_,
            snippet(html, ix, 30, 50),
        ));
    }

    // ── 3. Unprocessed word number marker ──────────────────────────────────
    //  (These two versions use ¦ in footnotes; parallel pages also have them.)
    if strict {
        let skip_barred =
            where_.contains("TCNT") || where_.contains("TC-GNT")
            || where_.starts_with("Parallel ") || where_.starts_with("End of parallel");
        if !skip_barred && html.contains('¦') {
            return Err(format!(
                "checkHtml() found unprocessed word number marker in '{}'",
                where_,
            ));
        }
    }

    // ── 4. Nested <span class="ul"><span class="ul"> ───────────────────────
    if strict {
        if html.contains(r#"<span class="ul"><span class="ul">"#) {
            let ix = html.find(r#"<span class="ul"><span class="ul">"#).unwrap();
            return Err(format!(
                "Nested <span class=\"ul\"><span class=\"ul\"> '{}' {}",
                where_,
                snippet(html, ix, 180, 180),
            ));
        }
    }

    // ── 5. Extra space in close tag ────────────────────────────────────────
    if strict {
        if let Some(ix) = html.find(" < /") {
            return Err(format!(
                "Extra space in close span '{}' {}",
                where_,
                snippet(html, ix, 180, 180),
            ));
        }
    }

    // ── 6. Literal `.ht#` ─────────────────────────────────────────────────
    if strict {
        if html.contains(".ht#") {
            return Err(format!("checkHtml({}) found '.ht#'", where_));
        }
    }

    // ── 7. Missing newline before chunkRV div ──────────────────────────────
    if strict {
        if let Some(ix) = html.find("><div class=\"chunkRV\">") {
            return Err(format!(
                "Missing newline in '{}' {}",
                where_,
                snippet(html, ix, 20, 20),
            ));
        }
    }

    // ── 8. Division balance ────────────────────────────────────────────────
    if strict {
        for div_name in &["section", "s1", "chunkRV", "rightS1Box", "RVLVcontainer"] {
            let open_single = count_sub(html, &format!("<div class=\"{}\">", div_name));
            let open_multi  = count_sub(html, &format!("<div class=\"{} ", div_name));
            let open_total  = open_single + open_multi;
            let close_total = count_sub(html, &format!("</div><!--{}-->", div_name));
            if open_total != close_total {
                return Err(format!(
                    "Unmatched '{}' divs: {} != {} '{}'",
                    div_name, open_total, close_total, where_,
                ));
            }
        }
    }

    // ── 9. html / head / body counts ──────────────────────────────────────
    if strict {
        for (tag, open_marker) in &[("html", "<html"), ("head", "<head"), ("body", "<body")] {
            let open_count = count_sub(html, open_marker);
            let close_marker = format!("</{}>", tag);
            let close_count = count_sub(html, &close_marker);
            if segment_only {
                if open_count != close_count {
                    return Err(format!(
                        "checkHtml({}) found mismatched {} tags: {} opens, {} closes",
                        where_, tag, open_count, close_count,
                    ));
                }
            } else {
                if open_count != 1 {
                    return Err(format!(
                        "checkHtml() found {} '{}' markers in '{}'",
                        open_count, tag, where_,
                    ));
                }
                if close_count != 1 {
                    return Err(format!(
                        "checkHtml() found {} '</{}>' markers in '{}'",
                        close_count, tag, where_,
                    ));
                }
            }
        }
    }

    // ── 10. Span nesting depth (skipped for certain versions) ──────────────
    if strict {
        let skip_span_check =
            where_.contains("ULT") || where_.contains("UST") || where_.contains("UTN")
            || html.contains("\"UTN\"") || where_.contains("OEB")
            || where_.contains("PSA") || where_.contains("JOB") || where_.contains("PRO")
            || where_.contains("JOL") || where_.contains("MAT") || where_.contains("ROM")
            || where_.contains("CO2") || where_.contains("GAL") || where_.contains("HEB")
            || where_.contains("REV");
        if !skip_span_check {
            let mut depth: i32 = 0;
            let mut search_from = 0usize;
            let mut last_unnested_span_ix = 0usize;
            loop {
                let span_ix = html[search_from..].find("<span").map(|i| i + search_from);
                let end_span_ix = html[search_from..].find("</span>").map(|i| i + search_from);
                let si = span_ix.unwrap_or(usize::MAX);
                let ei = end_span_ix.unwrap_or(usize::MAX);
                if si == ei {
                    // both == MAX → no more spans
                    break;
                } else if si < ei {
                    depth += 1;
                    if depth > 8 {
                        return Err(format!(
                            "Too many nested spans {} '{}' {}",
                            depth, where_, snippet(html, si, 0, 200),
                        ));
                    }
                    search_from = si + 5;
                } else {
                    depth -= 1;
                    if depth < 0 {
                        return Err(format!(
                            "Extra close span in '{}' {}",
                            where_, snippet(html, ei, 0, 200),
                        ));
                    }
                    if depth == 0 {
                        last_unnested_span_ix = si;
                    }
                    search_from = ei + 7;
                }
            }
            if depth != 0 {
                return Err(format!(
                    "\ncheckHTML() found unclosed span in '{}' {}",
                    where_,
                    snippet(html, last_unnested_span_ix, 0, 300),
                ));
            }
        }
    }

    // ── 11. Double angle brackets ──────────────────────────────────────────
    if strict {
        let skip_dbl_angle = segment_only
            && (html.contains(r#"<span class="add"><"#)
                || html.contains(r#"<span class="add">?<"#));
        if !skip_dbl_angle && html.contains("<<") {
            let ix = html.find("<<").unwrap();
            return Err(format!(
                "<span> '{}' {}",
                where_, snippet(html, ix, 180, 180),
            ));
        }

        let skip_dbl_angle2 =
            segment_only && html.contains(r#"<span class="add">>"#);
        if !skip_dbl_angle2 && !where_.contains("UTN ZEP_1:0") && !where_.contains("Parallel ZEP_1:0") {
            if let Some(ix) = html.find(">>") {
                return Err(format!(
                    "<span> '{}' {}",
                    where_, snippet(html, ix, 180, 180),
                ));
            }
        }
    }

    // ── 12. Bare <span> (unclassed) ────────────────────────────────────────
    if strict {
        if !html.contains("SOTN") {
            if let Some(ix) = html.find("<span>") {
                return Err(format!(
                    "<span> '{}' {}",
                    where_, snippet(html, ix, 180, 180),
                ));
            }
        }
    }

    // ── 13. `>span class` (missing opening angle bracket) ──────────────────
    if strict {
        if let Some(ix) = html.find(">span class") {
            return Err(format!(
                ">span class' '{}' {}",
                where_, snippet(html, ix, 180, 180),
            ));
        }
    }

    // ── 14. Empty elements and balanced open/close tags ────────────────────
    if strict {
        let markers: &[(&str, &str)] = &[
            ("div", "<div"), ("p", "<p "), ("h1", "<h1"), ("h2", "<h2"),
            ("h3", "<h3"), ("h4", "<h4"), ("span", "<span"), ("ol", "<ol"),
            ("ul", "<ul"), ("em", "<em>"), ("i", "<i>"), ("b", "<b>"),
            ("small", "<small "), ("sup", "<sup>"), ("sub", "<sub>"),
        ];
        let skip_empty =
            where_.contains("UTN") || html.contains("UTN");
        for &(tag, open_marker) in markers {
            let open_count = count_sub(html, open_marker);
            // If the open marker ends with ' ', also count the unspaced variant
            let mut total_open = open_count;
            if open_marker.ends_with(' ') {
                let unspaced = format!("<{tag}>");
                total_open += count_sub(html, &unspaced);
            }
            // Check for empty element (e.g. <p></p>)
            if total_open > 0 && !skip_empty {
                let empty_elem = format!("<{tag}></{tag}>");
                if html.contains(&empty_elem) {
                    let ix = html.find(&empty_elem).unwrap();
                    return Err(format!(
                        "Empty <{}> field '{}' {}",
                        tag, where_, snippet(html, ix, 180, 180),
                    ));
                }
            }
            let close_marker = format!("</{tag}>");
            let close_count = count_sub(html, &close_marker);
            if total_open != close_count {
                // Build a snippet between first open and last close
                let ix_start = html.find(open_marker).unwrap_or(0);
                let ix_end_close = html.rfind(&close_marker).unwrap_or(html.len());
                let snippet_str = if ix_start < ix_end_close {
                    let end = (ix_end_close + close_marker.len()).min(html.len());
                    snippet(html, ix_start, 0, end - ix_start)
                } else {
                    String::new()
                };
                return Err(format!(
                    "Mismatched '{}' start and end markers '{}' {} {}!={} {}",
                    tag, where_, segment_only, total_open, close_count, snippet_str,
                ));
            }
            // Check for doubled start marker (e.g. `<em><em>`)
            if open_marker.ends_with('>') {
                let doubled = format!("{}{}", open_marker, open_marker);
                if html.contains(&doubled) {
                    return Err(format!(
                        "Doubled {} in '{}' {}",
                        open_marker, where_, segment_only,
                    ));
                }
                let doubled_sp = format!("{} {}", open_marker, open_marker);
                if html.contains(&doubled_sp) {
                    return Err(format!(
                        "Doubled {} in '{}' {}",
                        open_marker, where_, segment_only,
                    ));
                }
            }
            // Check for doubled end marker (nested spans/divs/ol/ul are ok)
            if tag != "span" && tag != "div" && tag != "ol" && tag != "ul" {
                let doubled_end = format!("{}{}", close_marker, close_marker);
                if html.contains(&doubled_end) {
                    return Err(format!(
                        "Doubled end {} in '{}' {}",
                        close_marker, where_, segment_only,
                    ));
                }
                let doubled_end_sp = format!("{} {}", close_marker, close_marker);
                if html.contains(&doubled_end_sp) {
                    return Err(format!(
                        "Doubled end {} in '{}' {}",
                        close_marker, where_, segment_only,
                    ));
                }
            }
            // Check for reopened lists
            if tag == "ol" || tag == "ul" {
                let reopened = format!("{}{}", close_marker, open_marker);
                if html.contains(&reopened) {
                    return Err(format!(
                        "Reopened {} list in '{}' {}\n{}",
                        tag, where_, segment_only, html,
                    ));
                }
                let reopened_nl = format!("{}\n{}", close_marker, open_marker);
                if html.contains(&reopened_nl) {
                    return Err(format!(
                        "Reopened {} list in '{}' {}\n{}",
                        tag, where_, segment_only, html,
                    ));
                }
            }
        }
    }

    // ── 15. Improperly formed anchor ───────────────────────────────────────
    if strict {
        if html.contains(">a title=\"") {
            return Err(format!(
                "Improperly formed anchor in '{}' {}",
                where_, segment_only,
            ));
        }
    }

    // ── 16. Nested anchors ─────────────────────────────────────────────────
    if strict {
        let skip_nested_a = segment_only
            && html.contains(r#"<span class="add"><a "#);
        if !skip_nested_a {
            let mut search_from = 0usize;
            loop {
                let a_ix = html[search_from..].find("<a ").map(|i| i + search_from);
                match a_ix {
                    None => break,
                    Some(a_start) => {
                        let end_a = html[a_start..].find("</a>").map(|i| i + a_start + 4);
                        let next_a = html[a_start + 3..].find("<a ").map(|i| i + a_start + 3);
                        if let (Some(end), Some(next)) = (end_a, next_a) {
                            if end > next {
                                return Err(format!(
                                    "Nested anchors in '{}' {}",
                                    where_,
                                    snippet(html, a_start, 0, 200),
                                ));
                            }
                        }
                        search_from = end_a.unwrap_or(html.len());
                    }
                }
            }
        }
    }

    // ── 17. List items without list wrapper ────────────────────────────────
    if strict {
        if html.contains("<li>") || html.contains("<li ") || html.contains("</li>") {
            let has_ol = html.contains("<ol>") || html.contains("<ol ");
            let has_ul = html.contains("<ul>") || html.contains("<ul ");
            if !has_ol && !has_ul {
                return Err(format!(
                    "Missing list OPEN marker in '{}' {}\n{}",
                    where_, segment_only, html,
                ));
            }
            if !html.contains("</ol>") && !html.contains("</ul>") {
                return Err(format!(
                    "Missing list CLOSE marker in '{}' {}\n{}",
                    where_, segment_only, html,
                ));
            }
        }
    }

    // ── 18. Newline before anchor close ─────────────────────────────────────
    if strict {
        if html.contains("\n</a>") {
            return Err(format!(
                "'{}' {} has unexpected newline before anchor close",
                where_, segment_only,
            ));
        }
    }

    // ── 20. Class attribute validation ─────────────────────────────────────
    if strict {
        for caps in CLASS_ATTR_RE.captures_iter(html) {
            let class_guts = caps.get(1).unwrap().as_str();
            if class_guts.contains('\n') {
                return Err(format!(
                    "'{}' {} Bad class with newline in class_guts='{}'",
                    where_, segment_only, class_guts,
                ));
            }
            if class_guts.contains('<') {
                return Err(format!(
                    "'{}' {} Bad class with < in class_guts='{}'",
                    where_, segment_only, class_guts,
                ));
            }
            if class_guts.contains('>') {
                return Err(format!(
                    "'{}' {} Bad class with > in class_guts='{}'",
                    where_, segment_only, class_guts,
                ));
            }
            for class_name in class_guts.split(' ') {
                if class_name.len() > 23 {
                    return Err(format!(
                        "'{}' {} class is too long ({}) class_name='{}'",
                        where_, segment_only, class_name.len(), class_name,
                    ));
                }
            }
        }
    }

    // ── 21. ID attribute validation ────────────────────────────────────────
    if strict {
        let mut id_seen: Vec<(&str, usize, usize)> = Vec::new();
        for caps in ID_ATTR_RE.captures_iter(html) {
            let id_guts = caps.get(1).unwrap().as_str();
            let max_len: usize = if where_ == "DictionaryArticle" { 100 } else { 32 };
            if id_guts.len() > max_len {
                return Err(format!(
                    "'{}' {} id is too long ({}) id_guts='{}'",
                    where_, segment_only, id_guts.len(), id_guts,
                ));
            }
            if id_guts.contains(' ') {
                return Err(format!(
                    "'{}' {} Bad id with space in id_guts='{}'",
                    where_, segment_only, id_guts,
                ));
            }
            if id_guts.contains('\n') {
                return Err(format!(
                    "'{}' {} Bad id with newline in id_guts='{}'",
                    where_, segment_only, id_guts,
                ));
            }
            if id_guts.contains('<') {
                return Err(format!(
                    "'{}' {} Bad id with < in id_guts='{}'",
                    where_, segment_only, id_guts,
                ));
            }
            if id_guts.contains('>') {
                return Err(format!(
                    "'{}' {} Bad id with > in id_guts='{}'",
                    where_, segment_only, id_guts,
                ));
            }
            // Duplicate ID check (skip OEB, Moff, Wycl)
            if !where_.contains("OEB") && !where_.contains("Moff") && !where_.contains("Wycl") {
                for &(prev_id, prev_start, prev_end) in &id_seen {
                    if id_guts == prev_id {
                        return Err(format!(
                            "Duplicate id=\"{}\" FROM '{}' {} …{}… THEN …{}…",
                            id_guts,
                            where_,
                            segment_only,
                            snippet(html, prev_start.saturating_sub(300), 0, prev_end - prev_start + 600),
                            snippet(html, caps.get(0).unwrap().start().saturating_sub(300), 0, 600),
                        ));
                    }
                }
            }
            let m = caps.get(0).unwrap();
            id_seen.push((id_guts, m.start(), m.end()));
        }
    }

    // ── 22. Title attribute validation ─────────────────────────────────────
    if strict {
        for caps in TITLE_ATTR_RE.captures_iter(html) {
            let title_guts = caps.get(1).unwrap().as_str();
            let max_title_len: usize =
                if title_guts.trim_start().starts_with("OSHB ")
                    || title_guts.starts_with("Note")
                    || where_.contains("NET")
                    || where_.contains("TCNT")
                    || where_.contains("TC-GNT")
                    || where_.contains("T4T")
                    || where_.contains("Parallel")
                    || where_.contains("End of parallel")
                    || where_.contains("1611")
                {
                    1020
                } else {
                    150
                };
            if title_guts.len() > max_title_len {
                return Err(format!(
                    "{where_}={} {} title is too long ({}) title_guts='{}'",
                    where_, segment_only, title_guts.len(), title_guts,
                ));
            }
            if title_guts.contains('\n') {
                return Err(format!(
                    "'{}' {} Bad HTML title with newline in title_guts='{}'",
                    where_, segment_only, title_guts,
                ));
            }
            if title_guts.contains("<br") {
                return Err(format!(
                    "'{}' {} Bad HTML title with BR in title_guts='{}'",
                    where_, segment_only, title_guts,
                ));
            }
            if title_guts.contains("<span") {
                return Err(format!(
                    "'{}' {} Bad HTML title with SPAN in title_guts='{}'",
                    where_, segment_only, title_guts,
                ));
            }
            if title_guts.contains("class=\"") {
                return Err(format!(
                    "'{}' {} Bad HTML title with CLASS in title_guts='{}'",
                    where_, segment_only, title_guts,
                ));
            }
        }
    }

    // ── 23. Doubled ND spans ───────────────────────────────────────────────
    if strict {
        if html.contains(r#"<span class="nd"><span class="nd">"#) {
            let count = count_sub(html, r#"<span class="nd"><span class="nd">"#);
            return Err(format!(
                "'{}' {} Found {} doubled ND spans",
                where_, segment_only, count,
            ));
        }
    }

    // ── 24. OET-specific unprocessed annotations ───────────────────────────
    if strict {
        if where_.contains("OET") || where_.contains("Parallel") {
            // Skip certain known problematic references
            let skip_ref = where_.contains("NAH_2:7")
                || where_.contains("GAL_5:10")
                || where_.contains("CO1_10:24")
                || where_.contains("EPH_2:22");
            if !skip_ref {
                let annotations: &[(&str, &str)] = &[
                    ("+", "added article"), ("-", "dropped article"),
                    ("=", "added copula"), (">", "implied object"),
                    ("\u{2261}", "repeat ellided"), ("&", "added 'owner'"),
                    ("@", "expanded pronoun"), ("*", "reduced to pronoun"),
                    ("#", "changed number"), ("^", "used opposite"),
                    ("\u{2248}", "reworded"), ("?", "unsure"),
                ];
                for &(ch, reason) in annotations {
                    let needle = format!("<span class=\"add\">{}", ch);
                    if let Some(ix) = html.find(&needle) {
                        return Err(format!(
                            "'{}' {} Missed ADD {} in {}",
                            where_,
                            segment_only,
                            reason,
                            snippet(html, ix.saturating_sub(50), 0, 100),
                        ));
                    }
                }
            }
            // Check for unprocessed `<` in add fields
            {
                let mut search_from = 0usize;
                loop {
                    let needle = r#"<span class="add"><"#;
                    let ix = html[search_from..].find(needle).map(|i| i + search_from);
                    match ix {
                        None => break,
                        Some(ix) => {
                            let next_start = ix + 18;
                            if let Some(next) = html.get(next_start..next_start + 32) {
                                if !next.starts_with("<a title=") && !next.starts_with("<span ") {
                                    return Err(format!(
                                        "Unprocessed add field with next='{}' '{}'",
                                        next,
                                        where_,
                                    ));
                                }
                            }
                            search_from = ix + 18;
                        }
                    }
                }
            }
        }
    }

    Ok(())
}

// ── Python wrapper (called from `openbibledata_rust.checkHtml`) ────────────
/// Python-callable wrapper for `check_html`.
///
/// Returns `True` on success (matching the Python `checkHtml` contract).
/// Raises `ValueError` on validation failure.
#[pyfunction(name = "checkHtml", signature = (where_, html_to_check, segment_only=false))]
pub fn check_html_py(
    _py: Python<'_>,
    where_: &str,
    html_to_check: &str,
    segment_only: bool,
) -> PyResult<bool> {
    check_html(html_to_check, where_, segment_only)
        .map_err(|msg| pyo3::exceptions::PyValueError::new_err(msg))?;
    Ok(true)
}

// ── Unit tests ─────────────────────────────────────────────────────────────
#[cfg(test)]
mod tests {
    use super::*;

    fn ok(html: &str) -> bool {
        check_html(html, "TEST", false).is_ok()
    }

    fn ok_seg(html: &str) -> bool {
        check_html(html, "TEST", true).is_ok()
    }

    fn ok_seg_where(html: &str, where_: &str) -> bool {
        check_html(html, where_, true).is_ok()
    }

    fn err(html: &str) -> String {
        check_html(html, "TEST", false).unwrap_err()
    }

    fn err_seg(html: &str) -> String {
        check_html(html, "TEST", true).unwrap_err()
    }

    // -- Double newlines --
    #[test]
    fn test_double_newline() {
        assert!(!ok("<html><head></head><body>\n\n</body></html>"));
        assert!(err("<html><head></head><body>\n\n</body></html>").contains("double newlines"));
    }

    #[test]
    fn test_no_double_newline() {
        assert!(ok("<html><head></head><body>\n<p>Hello</p>\n</body></html>"));
    }

    // -- <br>\n --
    #[test]
    fn test_br_newline() {
        assert!(!ok("<html><head></head><body><br>\n</body></html>"));
    }

    // -- <br></span> --
    #[test]
    fn test_br_before_close_span() {
        assert!(!ok("<html><head></head><body><span>text<br></span></body></html>"));
        assert!(!ok_seg("<span>text<br></span>"));
    }

    #[test]
    fn test_no_br_before_close_span_ok() {
        assert!(ok_seg(r#"<span class="x">text</span>"#));
    }

    // -- Word number marker --
    #[test]
    fn test_unprocessed_barred() {
        assert!(!ok("Hello ¦ world"));
    }

    #[test]
    fn test_barred_skipped_for_tcnt() {
        assert!(ok_seg_where("Hello ¦ world", "TCNT_1:1"));
    }

    #[test]
    fn test_barred_skipped_for_parallel() {
        assert!(ok_seg_where("Hello ¦ world", "Parallel PSA_1:1"));
    }

    // -- Nested <span class="ul"> --
    #[test]
    fn test_nested_ul_span() {
        assert!(!ok(r#"<span class="ul"><span class="ul">text"#));
    }

    // -- Extra space in close tag --
    #[test]
    fn test_extra_space_close() {
        assert!(!ok("Hello < /span> world"));
    }

    // -- .ht# --
    #[test]
    fn test_ht_hash() {
        assert!(!ok("foo.ht#bar"));
    }

    // -- Division balance --
    #[test]
    fn test_unbalanced_div() {
        let html = "<html><head></head><body><div class=\"section\">hello</body></html>";
        assert!(!ok(html));
    }

    #[test]
    fn test_balanced_div() {
        let html = "<html><head></head><body>\n<div class=\"section\">hello</div><!--section-->\n</body></html>";
        assert!(ok(html));
    }

    // -- html/head/body counts --
    #[test]
    fn test_multiple_html_tags() {
        assert!(!ok("<html><html></html></html>"));
    }

    #[test]
    fn test_segment_only_ok() {
        assert!(ok_seg("<p>Hello</p>"));
    }

    // -- Empty element --
    #[test]
    fn test_empty_p() {
        assert!(!ok_seg("<p></p>text"));
    }

    // -- Doubled start marker --
    #[test]
    fn test_doubled_em() {
        assert!(!ok_seg("<em><em>bold</em></em>"));
    }

    // -- Doubled end marker --
    #[test]
    fn test_doubled_end_em() {
        assert!(!ok_seg("<em>bold</em></em>"));
    }

    // -- Nested anchors --
    #[test]
    fn test_nested_anchors() {
        assert!(!ok_seg("text <a href='a'><a href='b'>link</a></a> more"));
    }

    // -- List without wrapper --
    #[test]
    fn test_li_without_ol() {
        assert!(!ok_seg("<li>item</li>"));
    }

    // -- Missing list close --
    #[test]
    fn test_ol_without_close() {
        assert!(!ok_seg("<ol><li>item</li>"));
    }

    // -- Newline before anchor close --
    #[test]
    fn test_newline_before_a_close() {
        assert!(!ok_seg("<p><a href='x'>link\n</a></p>"));
    }

    // -- Class length --
    #[test]
    fn test_class_too_long() {
        let long_class = "a".repeat(24);
        assert!(!ok_seg(&format!("<p class=\"{}\">text</p>", long_class)));
    }

    #[test]
    fn test_class_max_length() {
        let ok_class = "a".repeat(23);
        assert!(ok_seg(&format!("<p class=\"{}\">text</p>", ok_class)));
    }

    // -- ID length --
    #[test]
    fn test_id_too_long() {
        let long_id = "b".repeat(33);
        assert!(!ok_seg(&format!("<p id=\"{}\">text</p>", long_id)));
    }

    // -- ID with space --
    #[test]
    fn test_id_with_space() {
        assert!(!ok_seg("<p id=\"my id\">text</p>"));
    }

    // -- Bare <span> --
    #[test]
    fn test_bare_span() {
        assert!(!ok_seg("<span>hello</span>"));
    }

    #[test]
    fn test_bare_span_skipped_for_sotn() {
        assert!(ok_seg("SOTN text <span>hello</span>"));
    }

    // -- >span class --
    #[test]
    fn test_missing_open_bracket() {
        assert!(!ok_seg(">span class=\"foo\">"));
    }

    // -- Doubled ND spans --
    #[test]
    fn test_doubled_nd() {
        assert!(!ok_seg(r#"<span class="nd"><span class="nd">YHWH</span></span>"#));
    }

    // -- Improved anchor >a title --
    #[test]
    fn test_malformed_anchor() {
        assert!(!ok_seg(">a title=\"foo\">link</a>"));
    }

    // -- Newline before anchor close --
    #[test]
    fn test_nl_before_a_close() {
        assert!(!ok_seg("<a href='x'>text\n</a>"));
    }

    // -- Reopened list --
    #[test]
    fn test_reopened_ol() {
        assert!(!ok_seg("<ol><li>a</li></ol><ol><li>b</li></ol>"));
    }

    // -- Full valid HTML page --
    #[test]
    fn test_full_valid_page() {
        let html = r#"<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
<h1>Hello</h1>
<p class="text">World</p>
</body>
</html>"#;
        assert!(ok(html));
    }

    // -- Segment-only <span> nesting depth --
    #[test]
    fn test_span_nesting_ok() {
        let mut html = String::from("<span");
        for _ in 0..7 {
            html.push_str(" class=\"a\"><span");
        }
        html.push_str(" class=\"a\">deep</span>");
        for _ in 0..7 {
            html.push_str("</span>");
        }
        assert!(ok_seg(&html));
    }

    #[test]
    fn test_span_nesting_too_deep() {
        let mut html = String::new();
        for _ in 0..9 {
            html.push_str("<span class=\"a\">");
        }
        for _ in 0..9 {
            html.push_str("</span>");
        }
        assert!(!ok_seg(&html));
        assert!(err_seg(&html).contains("Too many nested spans"));
    }
}
