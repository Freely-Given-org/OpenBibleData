#!/usr/bin/env -S uv run
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""Render the Markdown blocks and scripture links in unfoldingWord notes.

CHANGELOG:
    2026-10-30 Preserve nested lists and paragraphs, and link verse ranges to OET sections.
    2026-11-01 Recover relative scripture paths with an erroneous HTTP prefix.
"""
import logging
import re
from xml.sax.saxutils import escape

import bos_books_codes_py
from openbibledata_rust import findSectionNumber
from navigation import mappedReferences, scriptureLink


MARKDOWN_LINK = re.compile(r'\[([^\[\]\n]+)\]\(([^()\s]+)\)')
VERSE_RANGE = re.compile(r'\d+[a-z]?\s*[-–—]\s*\d+')
LIST_ITEM = re.compile(r'^(\s*)(?:([-+*])|(\d+)[.)])\s+(.+)$')


def livenUTNMarkdownLinks(text, level, BBB, C, V, state):
    """Use target paths for addresses and labels to distinguish verses/ranges.

    A range can span multiple OET sections; open the section containing its
    first verse. If that section is unavailable, retain a parallel verse link.
    Resolve from the site root so interlinear notes also link to parallel pages.
    """
    def replace(match):
        label, target = match.groups()
        if target.startswith(('http://../', 'https://../', 'http://./', 'https://./')):
            logging.warning('UTN %s %s:%s: removing HTTP prefix from relative Markdown target %r', BBB,C,V,target)
            target = target.split('://', 1)[1]
        if target.startswith(('https://', 'http://')):
            escapedTarget = escape(target, {'"':'&quot;'})
            return f'<a href="{escapedTarget}">{label}</a>'
        if target.startswith(('../', './')) and target.endswith('.md'):
            # Cross-book links occur as both ../mrk/14/22.md and
            # ../../mrk/14/22.md in the supplied notes.
            parts = re.sub(r'^(?:\.\.?/)+', '', target[:-3]).rstrip('/').split('/')
            if parts == ['front', 'intro']:
                return f'<a href="{"../"*level}par/{BBB}/Intro.htm#Top">{label}</a>'
            try:
                if len(parts) == 3:
                    book, chapter, verse = parts
                    book = {'i1kg':'1ki', '2kg':'2ki'}.get(book.lower(), book)
                    book = bos_books_codes_py.usfm_abbrev_to_bos_book_code(book)
                elif len(parts) == 2:
                    book, (chapter, verse) = BBB, parts
                elif len(parts) == 1 and target.startswith('./'):
                    book, chapter, verse = BBB, C, parts[0]
                else:
                    raise ValueError('unexpected scripture path')
                chapter = str(int(chapter))
                verse = '0' if verse == 'intro' else str(int(verse.lstrip('.')))
                if not book:
                    raise ValueError('unknown book')
            except (ValueError, KeyError) as error:
                logging.warning('UTN %s %s:%s: invalid Markdown target %r (%s)', BBB,C,V,target,error)
                return label

            reference = book, chapter, verse
            if VERSE_RANGE.search(label):
                refs = mappedReferences(reference, 'UTN', 'OET-RV', state)
                sectionsByBook = getattr(state, 'sectionsListsForSections', {}).get('OET-RV', {})
                if refs:
                    sectionBook, sectionC, sectionV, suffix = refs[0]
                    # Do not let test-mode findSectionNumber fabricate section 0
                    # for a book excluded from the build.
                    if sectionBook in sectionsByBook:
                        number = findSectionNumber('OET-RV', sectionBook, sectionC, sectionV, state)
                        if number is not None:
                            filename = sectionsByBook[sectionBook][number][-1]
                            href = f'{"../"*level}OET/bySec/{filename}#C{sectionC}V{sectionV}{suffix or ""}'
                            return f'<a title="View OET section" data-vref="mapped" href="{href}">{label}</a>'
                logging.warning('UTN %s %s:%s: no OET section for %r (%s %s:%s); using parallel verse',
                                BBB,C,V,label,*reference)
            return scriptureLink(level, reference, 'UTN', 'OET', 'par', label, state,
                                 title='View parallel verse')

        logging.warning('UTN %s %s:%s: unhandled Markdown target %r', BBB,C,V,target)
        return label

    return MARKDOWN_LINK.sub(replace, text)


def formatUTNMarkdownBlocks(text, reference):
    """Render headings, paragraphs and indented ordered/unordered lists.

    Inline markup has already been converted by the UTN formatter. List
    indentation in the source is inconsistent, so follow relative indentation
    instead of assuming a fixed number of spaces per nesting level.
    """
    output, paragraph, lists = [], [], []
    blankLine = False

    def flushParagraph():
        if paragraph:
            output.append(f'<p class="UTN">{" ".join(paragraph)}</p>')
            paragraph.clear()

    def closeList():
        _indent, tag = lists.pop()
        output.append(f'</li></{tag}>')

    for line in text.expandtabs(4).splitlines():
        if not line.strip():
            flushParagraph()
            blankLine = True
            continue
        if item := LIST_ITEM.match(line):
            flushParagraph()
            spaces, bullet, number, content = item.groups()
            indent, tag = len(spaces), 'ul' if bullet else 'ol'
            while lists and indent < lists[-1][0]:
                closeList()
            if lists and indent == lists[-1][0] and tag != lists[-1][1]:
                closeList()
            if not lists or indent > lists[-1][0]:
                start = f' start="{int(number)}"' if number and int(number) != 1 else ''
                output.append(f'<{tag}{start}>')
                lists.append((indent, tag))
            else:
                output.append('</li>')
            output.append(f'<li>{content}')
        elif heading := re.match(r'^(#{1,4})(?!#)(\s?)(.*)$', line):
            flushParagraph()
            while lists:
                closeList()
            hashes, space, content = heading.groups()
            if not space:
                logging.error('Bad markdown formatting in UTN %s line: %r', reference, line)
            output.append(f'<h{len(hashes)}>{content}</h{len(hashes)}>')
        elif lists and len(line)-len(line.lstrip()) > lists[-1][0]:
            if blankLine or paragraph:
                paragraph.append(line.strip())
            else:
                output.append(' ' + line.strip())
        else:
            if lists:
                flushParagraph()
            while lists:
                closeList()
            paragraph.append(line.strip())
        blankLine = False
    flushParagraph()
    while lists:
        closeList()
    return '\n'.join(output)
