// SPDX-License-Identifier: GPL-3.0-or-later
//! Structure-aware helpers for the shared OET HTML customisation passes.
//!
//! Changelog:
//!   2026-10-23: Protect markup and notes from LV text substitutions and combine
//!               translation-formatting explanations with source-word titles.

use once_cell::sync::Lazy;
use regex::Regex;

// Tokenise generated HTML without reserialising it. In particular, a quoted
// `>` is not a tag boundary, and comments must remain opaque.
static TAG: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r#"(?s)<!--.*?-->|</?[A-Za-z][A-Za-z0-9:-]*(?:[^<>"']|"[^"]*"|'[^']*')*>"#).unwrap()
});
static ATTRIBUTE: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r#"\s+([A-Za-z_:][A-Za-z0-9_:.-]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))"#)
        .unwrap()
});

const FORMATS: &[(&str, &str)] = &[
    ("add", "added info"),
    ("RVadd", "added info"),
    ("addArticle", "added article"),
    ("addCopula", "added copula"),
    ("addDirectObject", "added direct object"),
    ("addExtra", "added implied info"),
    ("addElided", "added elided info"),
    ("addOwner", "added ‘owner’"),
    ("addPronoun", "used pronoun"),
    ("addReferent", "inserted referent"),
    ("addNumberChange", "changed number"),
    ("addPersonChange", "changed person"),
    ("addNegated", "negated"),
    ("addTradName", "traditional name"),
    ("addReword", "reworded"),
];

fn attribute<'a>(tag: &'a str, name: &str) -> Option<&'a str> {
    ATTRIBUTE.captures_iter(tag).find_map(|caps| {
        if caps[1].eq_ignore_ascii_case(name) {
            (2..=4).find_map(|i| caps.get(i).map(|m| m.as_str()))
        } else {
            None
        }
    })
}

fn set_attribute(tag: &str, name: &str, value: &str) -> String {
    // Existing attribute text is already entity-escaped. Preserve entities,
    // escaping only literal double quotes when changing the quote delimiter.
    let value = value.replace('"', "&quot;");
    for caps in ATTRIBUTE.captures_iter(tag) {
        if caps[1].eq_ignore_ascii_case(name) {
            let m = caps.get(0).unwrap();
            return format!(
                "{} {name}=\"{value}\"{}",
                &tag[..m.start()],
                &tag[m.end()..]
            );
        }
    }
    let end = tag.len() - if tag.ends_with("/>") { 2 } else { 1 };
    format!("{} {name}=\"{value}\"{}", &tag[..end], &tag[end..])
}

fn tag_name(tag: &str) -> &str {
    let rest = tag.trim_start_matches('<').trim_start_matches('/');
    rest.split(|c: char| c.is_ascii_whitespace() || c == '/' || c == '>')
        .next()
        .unwrap_or("")
}

fn is_void(tag: &str) -> bool {
    tag.ends_with("/>")
        || matches!(
            tag_name(tag),
            "area"
                | "base"
                | "br"
                | "col"
                | "embed"
                | "hr"
                | "img"
                | "input"
                | "link"
                | "meta"
                | "param"
                | "source"
                | "track"
                | "wbr"
        )
}

fn is_note_or_raw_text(tag: &str) -> bool {
    matches!(tag_name(tag), "script" | "style" | "textarea")
        || attribute(tag, "class").is_some_and(|classes| {
            classes.split_ascii_whitespace().any(|class| {
                matches!(
                    class,
                    "footnotes"
                        | "crossRefs"
                        | "fn"
                        | "fnCaller"
                        | "fnRef"
                        | "fnText"
                        | "ft"
                        | "fk"
                        | "fq"
                        | "fqa"
                        | "fl"
                        | "fw"
                        | "fp"
                        | "fv"
                        | "fdc"
                        | "xr"
                        | "xrCaller"
                        | "xrRef"
                        | "xrText"
                        | "xt"
                        | "xo"
                )
            })
        })
}

#[derive(Clone, Default)]
struct Context {
    name: String,
    protected: bool,
    formats: Vec<String>,
    word_title: Option<String>,
}

fn close_tag(stack: &mut Vec<Context>, tag: &str) {
    if let Some(index) = stack.iter().rposition(|frame| frame.name == tag_name(tag)) {
        stack.truncate(index);
    }
}

/// Markup and note contents temporarily replaced by collision-free opaque tokens.
/// Restore in one pass, avoiding repeated scans of whole-book HTML.
pub(crate) struct ProtectedHtml {
    pub text: String,
    prefix: String,
    fragments: Vec<String>,
}

impl ProtectedHtml {
    fn protect(&mut self, fragment: &str) {
        self.text
            .push_str(&format!("{}{}Z", self.prefix, self.fragments.len()));
        self.fragments.push(fragment.to_owned());
    }

    pub fn restore(&self, text: &str) -> String {
        let mut result = String::with_capacity(text.len());
        let mut remaining = text;
        while let Some((before, after)) = remaining.split_once(&self.prefix) {
            result.push_str(before);
            let Some((index, tail)) = after.split_once('Z') else {
                result.push_str(&self.prefix);
                result.push_str(after);
                return result;
            };
            if let Some(fragment) = index
                .parse::<usize>()
                .ok()
                .and_then(|i| self.fragments.get(i))
            {
                result.push_str(fragment);
            } else {
                result.push_str(&self.prefix);
                result.push_str(index);
                result.push('Z');
            }
            remaining = tail;
        }
        result.push_str(remaining);
        result
    }
}

/// Normalise LV addition markers, then hide all tags, attributes, comments and
/// note text before the existing sentence/word-joiner substitutions run.
pub(crate) fn protect_lv_html(html: &str) -> ProtectedHtml {
    let mut prefix = "OBDPROTECTED".to_owned();
    while html.contains(&prefix) {
        prefix.push('X');
    }
    let mut output = ProtectedHtml {
        text: String::with_capacity(html.len()),
        prefix,
        fragments: Vec::new(),
    };
    let mut stack: Vec<Context> = Vec::new();
    let mut cursor = 0;
    while let Some(m) = TAG.find_at(html, cursor) {
        let protected = stack.last().is_some_and(|frame| frame.protected);
        let text = &html[cursor..m.start()];
        if protected {
            output.protect(text);
        } else {
            output.text.push_str(text);
        }
        let tag = m.as_str();
        cursor = m.end();
        if tag.starts_with("<!--") {
            output.protect(tag);
            continue;
        }
        if tag.starts_with("</") {
            close_tag(&mut stack, tag);
            output.protect(tag);
            continue;
        }
        let protected = protected || is_note_or_raw_text(tag);
        let mut tag = tag.to_owned();
        if !protected && tag_name(&tag) == "span" && attribute(&tag, "class") == Some("add") {
            let rest = &html[cursor..];
            let class = match rest.chars().next() {
                Some('+') => Some("addArticle"),
                Some('=') => Some("addCopula"),
                Some('>') => Some("addExtra"),
                Some('&') if !rest.starts_with("&amp;") && !rest.starts_with("&lt;") => {
                    Some("addOwner")
                }
                Some('<') if !rest.starts_with("<a ") && !rest.starts_with("<span ") => {
                    Some("addDirectObject")
                }
                _ => None,
            };
            if let Some(class) = class {
                tag = set_attribute(&tag, "class", class);
                cursor += 1; // All LV addition markers are ASCII.
            }
        }
        if !is_void(&tag) {
            stack.push(Context {
                name: tag_name(&tag).to_owned(),
                protected,
                ..Context::default()
            });
        }
        output.protect(&tag);
    }
    if stack.last().is_some_and(|frame| frame.protected) {
        output.protect(&html[cursor..]);
    } else {
        output.text.push_str(&html[cursor..]);
    }
    output
}

fn format_description(tag: &str) -> Option<String> {
    let classes = attribute(tag, "class")?;
    let mut description = FORMATS.iter().find_map(|(class, description)| {
        classes
            .split_ascii_whitespace()
            .any(|c| c == *class)
            .then_some((*description).to_owned())
    })?;
    if classes.split_ascii_whitespace().any(|c| c == "unsure") {
        description.push_str(" (less certain)");
    }
    Some(description)
}

fn combined_title(formats: &[String], word_title: Option<&str>) -> String {
    let mut parts: Vec<&str> = Vec::new();
    for part in formats.iter().map(String::as_str) {
        if !part.is_empty() && !parts.contains(&part) {
            parts.push(part);
        }
    }
    // Only deduplicate formatting prefixes. The source metadata itself is
    // opaque and may legitimately contain repeated text or semicolons.
    let mut source = word_title.unwrap_or("");
    while let Some((prefix, remaining)) = source.split_once("; ") {
        if !is_format_description(prefix) {
            break;
        }
        if !parts.contains(&prefix) {
            parts.push(prefix);
        }
        source = remaining;
    }
    if !source.is_empty() {
        parts.push(source);
    }
    parts.join("; ")
}

fn is_format_description(description: &str) -> bool {
    let label = description
        .strip_suffix(" (less certain)")
        .unwrap_or(description);
    FORMATS.iter().any(|(_, description)| label == *description)
}

/// Preserve the existing word-title length allowance after adding formatting
/// descriptions. Other titles still use the validator's original limits.
pub(crate) fn formatting_prefix_len(title: &str) -> usize {
    let mut length = 0;
    for part in title.split("; ") {
        if !is_format_description(part) {
            break;
        }
        length += part.len() + 2;
    }
    length.min(title.len())
}

/// Combine all enclosing OET addition descriptions with each Hebrew/Greek word
/// title. A formatted span inside a link also receives its word information.
/// Footnotes/navigation keep their own titles; links, classes and text survive
/// byte-for-byte. Reapplying this helper does not duplicate descriptions.
pub(crate) fn combine_oet_titles(html: &str) -> String {
    let mut output = String::with_capacity(html.len());
    let mut stack: Vec<Context> = Vec::new();
    let mut cursor = 0;
    for m in TAG.find_iter(html) {
        output.push_str(&html[cursor..m.start()]);
        cursor = m.end();
        let tag = m.as_str();
        if tag.starts_with("<!--") {
            output.push_str(tag);
            continue;
        }
        if tag.starts_with("</") {
            close_tag(&mut stack, tag);
            output.push_str(tag);
            continue;
        }
        let mut context = stack.last().cloned().unwrap_or_default();
        context.name = tag_name(tag).to_owned();
        context.protected |= is_note_or_raw_text(tag);
        let mut updated = tag.to_owned();
        if !context.protected {
            let description = if context.name == "span" {
                format_description(tag)
            } else {
                None
            };
            if let Some(description) = &description
                && !context.formats.contains(description)
            {
                context.formats.push(description.clone());
            }
            let word_link = context.name == "a"
                && attribute(tag, "href").is_some_and(|href| {
                    href.contains("ref/HebWrd/") || href.contains("ref/GrkWrd/")
                });
            if word_link {
                context.word_title = attribute(tag, "title").map(str::to_owned);
            }
            if description.is_some() || (word_link && !context.formats.is_empty()) {
                updated = set_attribute(
                    tag,
                    "title",
                    &combined_title(&context.formats, context.word_title.as_deref()),
                );
            }
        }
        if !is_void(tag) {
            stack.push(context);
        }
        output.push_str(&updated);
    }
    output.push_str(&html[cursor..]);
    output
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn jeremiah_rewording_preserves_word_link_and_unlinked_phrase_title() {
        let source = r#"<span class="addReword" title="reworded">is able to <a title="יַעֲמֹד (yaˊₐmod, Vqi3ms)" href="../../ref/HebWrd/JERc50v44w26.htm#Top" class="hebVrb">resist</a></span> <a title="next" href="../../ref/HebWrd/next.htm">me</a>"#;
        let expected = source.replacen("title=\"יַעֲמֹד", "title=\"reworded; יַעֲמֹד", 1);
        let result = combine_oet_titles(source);
        assert_eq!(result, expected);
        assert_eq!(combine_oet_titles(&result), result);
    }

    #[test]
    fn all_addition_types_and_uncertainty_reach_word_titles() {
        for (class, label) in FORMATS {
            for uncertainty in ["", " unsure"] {
                let input = format!(
                    r#"<span class="{class}{uncertainty}">a <i><a title="λόγος (logos)" href="../ref/GrkWrd/test.htm">word</a></i> b</span>"#
                );
                let suffix = if uncertainty.is_empty() {
                    ""
                } else {
                    " (less certain)"
                };
                let out = combine_oet_titles(&input);
                assert!(
                    out.contains(&format!(r#"title="{label}{suffix}">a"#)),
                    "{out}"
                );
                assert!(
                    out.contains(&format!(r#"title="{label}{suffix}; λόγος (logos)""#)),
                    "{out}"
                );
            }
        }
    }

    #[test]
    fn nested_formats_and_formats_inside_links_keep_all_information() {
        let input = r#"<span class="addReword"><a title="word (untranslated)" href="../ref/HebWrd/test.htm"><span class="addNumberChange unsure">words</span></a> <span class="addOwner">his</span></span>"#;
        let out = combine_oet_titles(input);
        assert!(out.contains(r#"<a title="reworded; word (untranslated)""#));
        assert!(out.contains(r#"class="addNumberChange unsure" title="reworded; changed number (less certain); word (untranslated)""#));
        assert!(out.contains(r#"class="addOwner" title="reworded; added ‘owner’">his"#));
        assert_eq!(combine_oet_titles(&out), out);
    }

    #[test]
    fn note_and_navigation_titles_are_not_word_tooltips() {
        let input = r##"<span class="addReword" title="reworded"><span class="fnCaller"><a title="Note: original" href="#fn1">fn</a></span><a title="Navigation" href="../OET/byC/JER_C50.htm">chapter</a></span>"##;
        assert_eq!(combine_oet_titles(input), input);
    }

    #[test]
    fn quoted_attributes_entities_and_comments_survive() {
        let input = r#"<!-- title="a > b_!" --><span class='addExtra'><a href='../ref/HebWrd/test.htm?a=b_c&amp;d=e' title='word "quoted" &amp; more > less'>word</a></span>"#;
        let out = combine_oet_titles(input);
        assert!(
            out.contains(
                r#"title="added implied info; word &quot;quoted&quot; &amp; more > less""#
            )
        );
        assert!(out.contains("href='../ref/HebWrd/test.htm?a=b_c&amp;d=e'"));
        assert!(out.starts_with("<!-- title=\"a > b_!\" -->"));
    }

    #[test]
    fn lv_protection_covers_note_fragments_and_all_attributes() {
        let html = r#"<!-- a_b=c. --><a href='JER_C50.htm?q=a_b&amp;x=y' title='a > b: c_d!' data-value="_=.:">word_word</a><span class="ft">lemma=7323 n=1.1.0 id=a_b <i>more: metadata!</i></span>"#;
        let protected = protect_lv_html(html);
        let formatted = protected
            .text
            .replace('_', "JOIN")
            .replace('=', "EQUAL")
            .replace('.', "PERIOD")
            .replace(':', "COLON")
            .replace('!', "BANG");
        assert_eq!(
            protected.restore(&formatted),
            html.replace("word_word", "wordJOINword")
        );
    }

    #[test]
    fn protection_tokens_cannot_collide_with_source_text() {
        let html = "OBDPROTECTED0Z <b>x_y</b>";
        let protected = protect_lv_html(html);
        assert_eq!(protected.restore(&protected.text), html);
    }

    #[test]
    fn repeated_source_metadata_is_not_deduplicated() {
        let source = r#"<span class="addReword"><a title="word; word; &amp; &amp; more" href="../ref/HebWrd/test.htm">word</a></span>"#;
        let result = combine_oet_titles(source);
        assert!(result.contains(r#"title="reworded; word; word; &amp; &amp; more""#));
        assert_eq!(combine_oet_titles(&result), result);
    }
}
