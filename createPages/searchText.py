#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Shared search text rules and parsing of existing HTML fragments.

CHANGELOG:
    2026-11-01 Define searchable tokens and preserve browser highlight offsets.
"""
import importlib.util
from pathlib import Path
import re
import sys
import sysconfig
import unicodedata


def _htmlParser():
    # The site's html.py shadows the standard library. Load the stdlib parser
    # once, restoring the site's module identities even if initialization fails.
    names = ('html', 'html.entities', 'html.parser')
    saved = {name: sys.modules.get(name) for name in names}
    try:
        for name in names:
            sys.modules.pop(name, None)
        path = Path(sysconfig.get_path('stdlib')) / 'html' / '__init__.py'
        spec = importlib.util.spec_from_file_location('html', path)
        module = importlib.util.module_from_spec(spec)
        sys.modules['html'] = module
        spec.loader.exec_module(module)
        from html.parser import HTMLParser
        return HTMLParser
    finally:
        for name in names:
            sys.modules.pop(name, None)
            if saved[name] is not None:
                sys.modules[name] = saved[name]


class FragmentParser(_htmlParser()):
    """Extract visible text and destinations without executing embedded HTML."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.ids, self.hidden = [], set(), 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.add(attrs['id'])
        if tag in ('script', 'style'):
            self.hidden += 1
        if tag in ('p', 'div', 'br', 'li', 'h1', 'h2', 'h3', 'hr'):
            self.parts.append(' ')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)
        if tag in ('p', 'div', 'li', 'h1', 'h2', 'h3'):
            self.parts.append(' ')

    def handle_data(self, value):
        if not self.hidden:
            self.parts.append(value)


def plainHtml(value):
    parser = FragmentParser()
    parser.feed(value)
    parser.close()
    return ' '.join(''.join(parser.parts).split())


def normalize(value, *, accents=False):
    """NFD + lowercase, with final sigma unified; identical to searchCore.js."""
    value = unicodedata.normalize('NFD', value).lower().replace('ς', 'σ').replace('\u2060','')
    if not accents:
        value = ''.join(c for c in value if not unicodedata.category(c).startswith('M'))
    return unicodedata.normalize('NFC', value)


def tokens(value):
    """Return (normalized key, exact-accent key, UTF-16 start, UTF-16 end)."""
    start = None
    offset = 0
    word = []
    result = []
    for c in value + ' ':
        category = unicodedata.category(c)[0]
        if category in ('L', 'N') or (category == 'M' or c=='\u2060') and start is not None:
            if start is None:
                start = offset
            word.append(c)
        elif start is not None:
            text = ''.join(word)
            result.append((normalize(text), normalize(text, accents=True), start, offset))
            start, word = None, []
        offset += 2 if ord(c) > 0xFFFF else 1
    return result


_MARKER = re.compile(r'\\(\+?[A-Za-z][A-Za-z0-9-]*)(\*|\s?)')


def usfmText(value):
    """Read inline fields, omitting callers, reference labels and word attributes.

    BOS already separates extras for normal Bibles. This also handles the small
    selected-verse dictionaries and the marker-bearing text in BOS note extras.
    """
    fields = {'body': [], 'note': [], 'heading': []}
    destination, blocked, in_word = 'body', False, False
    cursor = 0
    for match in list(_MARKER.finditer(value)) + [None]:
        end = match.start() if match else len(value)
        text = value[cursor:end]
        if in_word:
            text = text.split('|', 1)[0]
        if not blocked:
            fields[destination].append(text)
        if match is None:
            break
        marker, closing = match[1].lstrip('+'), match[2] == '*'
        if marker in ('f', 'fe', 'x'):
            destination, blocked = ('body', False) if closing else ('note', True)
        elif marker in ('fr', 'xo', 'fm', 'fv', 'va', 'vp', 'ca', 'cp'):
            blocked = not closing
        elif marker in ('ft', 'fq', 'fqa', 'fk', 'fl', 'fw', 'fp', 'xt', 'xq'):
            blocked = False
        elif marker.startswith('s') and marker in ('s', 's1', 's2', 's3', 's4'):
            destination, blocked = 'heading', False
        elif marker in ('p', 'm', 'q1', 'q2', 'q3', 'b', 'nb', 'li1', 'li2'):
            destination, blocked = 'body', False
            fields[destination].append(' ')
        elif marker == 'w':
            in_word = not closing
        cursor = match.end()
    return {name: cleanText(''.join(parts)) for name, parts in fields.items() if parts}


def cleanText(value):
    value = re.sub(r'¦\d+', '', value)
    value = value.replace('_', ' ').replace('=', ' ').replace('◙', '')
    return ' '.join(value.split())
