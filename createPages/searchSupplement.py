#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Capture already transformed text while its owning page generator runs.

CHANGELOG:
    2026-11-01 Export derived editions and study notes without crawling output.
"""
import json
from pathlib import Path

from searchText import FragmentParser, plainHtml


class DerivedTextParser(FragmentParser):
    def __init__(self, version):
        super().__init__()
        self.version, self.stack, self.fields = version, [], {}

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)
        classes = dict(attrs).get('class', '').split()
        field = ('modernised' if f'{self.version}_mod' in classes else
                 ('translation' if self.version in ('Luth', 'ClVg') else 'transliteration')
                 if f'{self.version}_trans' in classes else None)
        if tag not in ('br', 'hr', 'img', 'input', 'meta', 'link', 'wbr'):
            self.stack.append((tag, field, len(self.parts)))

    def handle_endtag(self, tag):
        super().handle_endtag(tag)
        if self.stack and self.stack[-1][0] == tag:
            _, field, start = self.stack.pop()
            if field:
                text = ' '.join(''.join(self.parts[start:]).split())
                if text and not text.startswith(('Same as ', 'Modernised spelling is same')):
                    self.fields.setdefault(field, []).append(text)


def captureSupplement(state, version, reference, fragment, href, *, field=None, sourceKey=''):
    if not getattr(state, 'CREATE_SEARCH_INDEX_FLAG', False):
        return
    if field:
        fields = {field: plainHtml(fragment)}
    else:
        parser = DerivedTextParser(version)
        parser.feed(fragment)
        fields = {key: ' '.join(values) for key, values in parser.fields.items()}
    if not fields:
        return
    book, chapter, verse = reference
    row = dict(key=f'{version}:{book}:{chapter}:{verse}{":"+sourceKey if sourceKey else ""}', version=version, ref=list(reference),
               language=(state.BibleLanguages.get(version) or ('en' if field=='note' else 'und')).lower(), fields=fields,
               links={'context': href, 'parallel': href}, mapped=[], mapping='source')
    # A native book can map to another navigation book. Use the worker's own
    # navigation-book file, then merge deterministically in the parent.
    workerBook = href.split('/')[1]
    folder = Path(state.TEMP_BUILD_FOLDER) / '.searchRecords' / workerBook
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / f'{version}-{book}.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + '\n')


def captureNote(state, resource, reference, fragment, *, sourceKey=''):
    """Capture source content before the page adds its repeated resource heading."""
    book,chapter,verse=reference
    filename='Intro' if str(chapter)=='-1' else f'C{chapter}V{verse}'
    anchor=f'OBD-note-{sourceKey}' if resource=='OBD-notes' else 'TSN' if resource=='TOSN' else resource
    captureSupplement(state,resource,reference,fragment,f'par/{book}/{filename}.htm#{anchor}',field='note',sourceKey=sourceKey)


def supplementFiles(root):
    groups = {}
    for path in sorted((Path(root) / '.searchRecords').glob('*/*.jsonl')):
        version, book = path.stem.rsplit('-', 1)
        groups.setdefault((version,book), []).append(path)
    return groups


def supplementRecords(paths, pages):
    records = {}
    for path in paths:
        with path.open(encoding='utf-8') as stream:
            for line in stream:
                row = json.loads(line)
                if not pages.available(row['links']['context']):
                    raise ValueError(f'Missing search supplement destination: {row["links"]["context"]}')
                old = records.setdefault(row['key'], row)
                for field,text in row['fields'].items():
                    if field in old['fields'] and old['fields'][field]!=text:
                        raise ValueError(f'Conflicting search supplement: {row["key"]} {field} in {path}')
                    old['fields'][field]=text
    return records
