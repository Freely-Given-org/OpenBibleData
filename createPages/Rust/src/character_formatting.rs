use crate::constants::{FIG_ALT_REGEX, FIG_SRC_REGEX};

/// Result type for character formatting
pub struct CharacterFormattingResult {
    pub html: String,
    pub background_colour: Option<String>,
    pub files_to_copy: Vec<(String, String)>, // (src_path, dest_filename)
}

pub fn convert_usfm_character_formatting(
    version_abbrev: &str,
    bbb: &str,
    segment_type: &str,
    usfm_field: &str,
    basic_only: bool,
    background_colour: &mut Option<String>,
    expanded_char_markers: &[String],
    booklist_nt27: &[String],
    is_net_version: bool,
    level: usize,
) -> CharacterFormattingResult {
    let mut html = usfm_field.replace("\\+", "\\");
    let mut files_to_copy: Vec<(String, String)> = Vec::new();

    // Validation
    if !usfm_field.contains("\\add <<") && !usfm_field.contains("\\add ?<<") {
        assert!(!usfm_field.contains("<<"), "Unexpected << in usfm_field");
    }

    // === Handle verse colouring in OET-RV Psalms/Songs ===
    // NOTE: `background_colour` is an in/out parameter (like Python's nonlocal
    // variable): once set by a \zN marker it persists for all following lines
    // until a new chapter ('c' marker) resets it.
    if version_abbrev == "OET-RV" && bbb == "PSA" {
        if basic_only {
            if html.contains("\\z") {
                html = html
                    .replace("\\zr ", "")
                    .replace("\\z1 ", "")
                    .replace("\\z2 ", "")
                    .replace("\\z3 ", "")
                    .replace("\\z4 ", "")
                    .replace("\\zrhilite ", "")
                    .replace("\\z1hilite ", "")
                    .replace("\\z2hilite ", "")
                    .replace("\\z3hilite ", "")
                    .replace("\\z4hilite ", "")
                    .replace("\\zrhilite*", "")
                    .replace("\\z1hilite*", "")
                    .replace("\\z2hilite*", "")
                    .replace("\\z3hilite*", "")
                    .replace("\\z4hilite*", "");
            }
        } else {
            // not basicOnly
            if html.contains("\\z") {
                // Only *change* the colour if this line carries a plain \zN marker
                if html.contains("\\zr ") {
                    *background_colour = Some("zr".to_string());
                } else if html.contains("\\z1 ") {
                    *background_colour = Some("z1".to_string());
                } else if html.contains("\\z2 ") {
                    *background_colour = Some("z2".to_string());
                } else if html.contains("\\z3 ") {
                    *background_colour = Some("z3".to_string());
                } else if html.contains("\\z4 ") {
                    *background_colour = Some("z4".to_string());
                }
            }

            // No \z in this line, but we might still be coloured (persisted from before)
            if let Some(ref bg_color) = *background_colour {
                html = format!("<span class=\"{}\">{}</span><!--{}-->", bg_color, html, bg_color);
            }

            html = html
                .replace("\\zr ", "")
                .replace("\\z1 ", "")
                .replace("\\z2 ", "")
                .replace("\\z3 ", "")
                .replace("\\z4 ", "")
                .replace("\\zrhilite ", "<span class=\"zrhilite\">")
                .replace("\\z1hilite ", "<span class=\"z1hilite\">")
                .replace("\\z2hilite ", "<span class=\"z2hilite\">")
                .replace("\\z3hilite ", "<span class=\"z3hilite\">")
                .replace("\\z4hilite ", "<span class=\"z4hilite\">")
                .replace("\\zrhilite*", "</span>")
                .replace("\\z1hilite*", "</span>")
                .replace("\\z2hilite*", "</span>")
                .replace("\\z3hilite*", "</span>")
                .replace("\\z4hilite*", "</span>");
        }
        assert!(!html.contains("\\z"), "Backslash z still in html after processing");
    }

    // === Handle \\fig entries (figure processing) ===
    if usfm_field.contains("\\fig") {
        html = process_figures(&html, &mut files_to_copy, level);
    }

    // === Handle \\jmp entries (jump links) ===
    if usfm_field.contains("\\jmp") {
        html = process_jump_links(&html, segment_type, bbb);
    }

    // === Handle \\w markers (word markers) ===
    if usfm_field.contains("\\w ") || usfm_field.contains("\\+w ") {
        html = process_word_markers(&html);
    }

    // === Handle \\tc markers (table cells) ===
    if usfm_field.contains("\\tc") {
        html = html
            .replace("\\tc1 ", "<td>")
            .replace("\\tc2 ", "</td><td>")
            .replace("\\tc3 ", "</td><td>")
            .replace("\\tc4 ", "</td><td>")
            .replace("\\tc5 ", "</td><td>")
            .replace("\\tc1", "<td>");
    }

    // === Replace basic character markers with HTML equivalents ===
    html = html
        .replace("\\bdit ", "<b><i>")
        .replace("\\bdit*", "</i></b>")
        .replace("\\bd ", "<b>")
        .replace("\\bd*", "</b>")
        .replace("\\it ", "<i>")
        .replace("\\it*", "</i>")
        .replace("\\em ", "<em>")
        .replace("\\em*", "</em>")
        .replace("\\sup ", "<sup>")
        .replace("\\sup*", "</sup>");

    // === Special handling for OT '\\nd LORD\\nd*' ===
    html = html.replace(
        "\\nd LORD\\nd*",
        "\\nd L<span style=\"font-size:.75em;\">ORD</span>\\nd*",
    );

    // === Replace all other character markers into HTML spans ===
    let mut all_markers = expanded_char_markers.to_vec();
    if is_net_version {
        all_markers.extend(vec![
            "heb".to_string(),
            "theb".to_string(),
            "grk".to_string(),
            "tgrk".to_string(),
            "ver".to_string(),
            "src".to_string(),
            "fx".to_string(),
        ]);
    }

    for marker in &all_markers {
        if marker == "nd" && version_abbrev.contains("OET") && booklist_nt27.contains(&bbb.to_string()) {
            html = html
                .replace(&format!("\\{} ", marker), "<span class=\"nominaSacra\">")
                .replace(&format!("\\{}*", marker), "</span>");
        } else {
            html = html
                .replace(&format!("\\{} ", marker), &format!("<span class=\"{}\">", marker))
                .replace(&format!("\\{}*", marker), "</span>");
        }
    }

    // === Handle OET-LV untranslated words ===
    if version_abbrev.contains("OET") {
        html = process_untranslated_words(&html);
    }

    CharacterFormattingResult {
        html,
        background_colour: background_colour.clone(),
        files_to_copy,
    }
}

fn process_figures(html: &str, files_to_copy: &mut Vec<(String, String)>, level: usize) -> String {
    let mut result = html.to_string();
    let mut search_start_ix = 0;
    let mut safety_count = 0;

    while safety_count < 99 {
        safety_count += 1;

        if let Some(fig_start_ix) = result[search_start_ix..].find("\\fig ") {
            let fig_start_ix = search_start_ix + fig_start_ix;

            // Find the pipe after \\fig
            if let Some(pipe_ix) = result[fig_start_ix + 5..].find('|') {
                let pipe_ix = fig_start_ix + 5 + pipe_ix;

                // Find \\fig*
                if let Some(fig_end_ix) = result[pipe_ix + 1..].find("\\fig*") {
                    let fig_end_ix = pipe_ix + 1 + fig_end_ix;

                    let fig_guts = &result[fig_start_ix + 5..fig_end_ix];
                    let parts: Vec<&str> = fig_guts.splitn(2, '|').collect();

                    if parts.len() == 2 {
                        let fig_rest = parts[1];
                        let mut figure_html = "(Figure skipped)".to_string();

                        // Check if it's USFM v1/v2 (multiple pipes) or v3 (src= format)
                        if fig_rest.contains('|') {
                            // USFM v1 or v2 - not implemented
                        } else if fig_rest.trim_start().starts_with("src=\"") {
                            // USFM v3 figure
                            if let Some(cap) = FIG_SRC_REGEX.captures(fig_rest) {
                                if let Some(fig_src) = cap.get(1) {
                                    let fig_src_str = fig_src.as_str();
                                    let fig_filename = fig_src_str
                                        .split('/')
                                        .last()
                                        .unwrap_or(&fig_src_str)
                                        .to_string();
                                    files_to_copy.push((fig_src_str.to_string(), fig_filename.clone()));

                                    let alt_text = if let Some(cap) = FIG_ALT_REGEX.captures(fig_rest) {
                                        cap.get(1)
                                            .map(|m| m.as_str().to_string())
                                            .unwrap_or_else(|| {
                                                fig_filename
                                                    .replace(".jpg", "")
                                                    .replace(".png", "")
                                                    .replace('_', " ")
                                            })
                                    } else {
                                        fig_filename
                                            .replace(".jpg", "")
                                            .replace(".png", "")
                                            .replace('_', " ")
                                    };

                                    let alt_attr = if !alt_text.is_empty() {
                                        format!(" alt=\"{}\"", alt_text)
                                    } else {
                                        String::new()
                                    };

                                    figure_html = format!(
                                        "<img src=\"{}images/{}\"{}style=\"max-height:280px;\">",
                                        "../".repeat(level),
                                        fig_filename,
                                        alt_attr
                                    );
                                }
                            }
                        }

                        let new_html = format!(
                            "{}{}{}",
                            &result[..fig_start_ix],
                            figure_html,
                            &result[fig_end_ix + 5..]
                        );
                        search_start_ix = fig_start_ix + figure_html.len();
                        result = new_html;
                        continue;
                    }
                }
            }
            break;
        } else {
            break;
        }
    }

    result
}

fn process_jump_links(html: &str, segment_type: &str, bbb: &str) -> String {
    let mut result = html.to_string();
    let mut search_start_ix = 0;
    let mut safety_count = 0;

    while safety_count < 99 {
        safety_count += 1;

        if let Some(jmp_start_ix) = result[search_start_ix..].find("\\jmp ") {
            let jmp_start_ix = search_start_ix + jmp_start_ix;

            if let Some(pipe_ix) = result[jmp_start_ix + 5..].find('|') {
                let pipe_ix = jmp_start_ix + 5 + pipe_ix;

                if let Some(jmp_end_ix) = result[pipe_ix + 1..].find("\\jmp*") {
                    let jmp_end_ix = pipe_ix + 1 + jmp_end_ix;

                    let jmp_display = &result[jmp_start_ix + 5..pipe_ix].to_string();
                    let jmp_link_bit = &result[pipe_ix + 1..jmp_end_ix].to_string();

                    let new_link = if jmp_link_bit.contains("http") || jmp_link_bit.contains("href") {
                        // External link
                        let link = if jmp_link_bit.starts_with("link-href=\"") && jmp_link_bit.ends_with('"') {
                            &jmp_link_bit[11..jmp_link_bit.len() - 1]
                        } else if jmp_link_bit.starts_with("href=\"") && jmp_link_bit.ends_with('"') {
                            &jmp_link_bit[6..jmp_link_bit.len() - 1]
                        } else {
                            jmp_link_bit
                        };

                        let display = if jmp_display.is_empty() {
                            link.replace("https://www.", "")
                                .replace("http://www.", "")
                                .replace("https://", "")
                                .replace("http://", "")
                        } else {
                            jmp_display.clone()
                        };

                        format!("<a title=\"Go to external jump link\" href=\"{}\">{}</a>", link, display)
                    } else if jmp_link_bit.starts_with('#') {
                        // Internal link
                        if jmp_link_bit.contains('V') {
                            if let Some(v_ix) = jmp_link_bit.find('V') {
                                let ref_c = &jmp_link_bit[2..v_ix];
                                let ref_v = &jmp_link_bit[v_ix + 1..];

                                match segment_type {
                                    "book" => {
                                        format!("<a title=\"Go to internal jump link reference document\" href=\"{}\">{}</a>", jmp_link_bit, jmp_display)
                                    }
                                    "chapter" => {
                                        format!("<a title=\"Go to internal jump link reference chapter\" href=\"{}_C{}.htm#C{}V{}\">{}</a>", bbb, ref_c, ref_c, ref_v, jmp_display)
                                    }
                                    seg_type if seg_type.ends_with("Verse") => {
                                        format!("<a title=\"Go to internal jump link reference verse\" href=\"C{}V{}.htm#Top\">{}</a>", ref_c, ref_v, jmp_display)
                                    }
                                    _ => {
                                        // section/relatedPassage - would need section lookup callback
                                        // For now, just create basic link
                                        format!("<a title=\"Go to internal jump link\" href=\"{}\">{}</a>", jmp_link_bit, jmp_display)
                                    }
                                }
                            } else {
                                format!("<a title=\"Go to internal jump link\" href=\"{}\">{}</a>", jmp_link_bit, jmp_display)
                            }
                        } else {
                            format!("<a title=\"Go to internal jump link\" href=\"{}\">{}</a>", jmp_link_bit, jmp_display)
                        }
                    } else {
                        // Unknown link type - fallback
                        format!("<a title=\"Go to internal jump link\" href=\"{}\">{}</a>", jmp_link_bit, jmp_display)
                    };

                    let new_html = format!(
                        "{}{}{}",
                        &result[..jmp_start_ix],
                        new_link,
                        &result[jmp_end_ix + 5..]
                    );
                    search_start_ix = jmp_start_ix + new_link.len();
                    result = new_html;
                    continue;
                }
            }
            break;
        } else {
            break;
        }
    }

    result
}

fn process_word_markers(html: &str) -> String {
    let mut result = html.to_string();
    let mut search_start_ix = 0;
    let mut safety_count = 0;

    while safety_count < 299 {
        safety_count += 1;

        let search_string = if result[search_start_ix..].contains("\\w ") {
            "\\w "
        } else if result[search_start_ix..].contains("\\+w ") {
            "\\+w "
        } else {
            // No more word markers
            return result;
        };

        if let Some(w_start_ix) = result[search_start_ix..].find(search_string) {
            let w_start_ix = search_start_ix + w_start_ix;
            let w_end_marker = format!("{}*", &search_string[..search_string.len() - 1]);

            if let Some(w_end_ix) = result[w_start_ix + search_string.len()..].find(&w_end_marker) {
                let w_end_ix = w_start_ix + search_string.len() + w_end_ix;

                // Check if there's a pipe within this word marker
                if let Some(pipe_ix) = result[w_start_ix + search_string.len()..w_end_ix].find('|') {
                    let pipe_ix = w_start_ix + search_string.len() + pipe_ix;
                    let figure_html = &result[w_start_ix + search_string.len()..pipe_ix];
                    let new_result = format!(
                        "{}{}{}",
                        &result[..w_start_ix],
                        figure_html,
                        &result[w_end_ix + search_string.len()..]
                    );
                    search_start_ix = w_start_ix + figure_html.len();
                    result = new_result;
                } else {
                    // No pipe - just remove the markers
                    let figure_html = &result[w_start_ix + search_string.len()..w_end_ix];
                    let new_result = format!(
                        "{}{}{}",
                        &result[..w_start_ix],
                        figure_html,
                        &result[w_end_ix + search_string.len()..]
                    );
                    search_start_ix = w_start_ix + figure_html.len();
                    result = new_result;
                }
                continue;
            }
            break;
        } else {
            break;
        }
    }

    result
}

fn process_untranslated_words(html: &str) -> String {
    let mut result = html.to_string();
    let mut search_start_index = 0;
    let mut safety_count = 0;

    while safety_count < 900 {
        safety_count += 1;

        if let Some(ix) = result[search_start_index..].find("<span class=\"untr\"><a title=\"") {
            let ix = search_start_index + ix;
            let ix_title_start = ix + 29;

            if let Some(ix_title_end) = result[ix_title_start..].find("\" href=") {
                let ix_title_end = ix_title_start + ix_title_end;

                let have_dom_flag = result[ix_title_start..ix_title_end].contains("(ʼēt, To)");
                let suffix = if have_dom_flag {
                    " (untranslated direct-object marker)"
                } else {
                    " (untranslated)"
                };

                let new_result = format!(
                    "{}{}{}",
                    &result[..ix_title_end],
                    suffix,
                    &result[ix_title_end..]
                );
                search_start_index = ix_title_end + suffix.len();
                result = new_result;
                continue;
            }
            break;
        } else {
            break;
        }
    }

    result
}
