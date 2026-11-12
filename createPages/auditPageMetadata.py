#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Check the HTML heads in a clean Open Bible Data production build before release.

CHANGELOG:
    2026-11-05 Report missing metadata, title collisions and invalid canonical targets by page family.
    2026-11-09 Resolve directory canonical URLs to their generated index.htm pages.
"""
import argparse
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote, urlsplit

from searchText import FragmentParser


class PageHead(FragmentParser):
    def __init__(self, path):
        super().__init__()
        self.titles, self.descriptions, self.canonicals = [], [], []
        self.inTitle = self.ended = self.inBody = False
        # Some static indexes are huge and do not have a newline after the head.
        with path.open(encoding='utf-8') as source:
            while not self.ended and not self.inBody and (chunk := source.read(4096)):
                self.feed(chunk)
        self.close()

    def handle_starttag(self, tag, attrs):
        if self.ended or self.inBody:
            return
        attrs = dict(attrs)
        if tag == 'body':
            self.inBody = True
        elif tag == 'title':
            self.inTitle = True
            self.titles.append('')
        elif tag == 'meta' and (attrs.get('name') or '').lower() == 'description':
            self.descriptions.append(attrs.get('content') or '')
        elif tag == 'link' and 'canonical' in (attrs.get('rel') or '').lower().split():
            self.canonicals.append(attrs.get('href') or '')

    def handle_data(self, value):
        if self.inTitle:
            self.titles[-1] += value

    def handle_endtag(self, tag):
        if tag == 'title':
            self.inTitle = False
        elif tag == 'head':
            self.ended = True
            self.inTitle = False


def pageFamily(parts):
    if len(parts) == 1:
        return 'site'
    if parts[0] in ('ref','UBS'):
        return '/'.join(parts[:2]) if len(parts) > 2 else parts[0]
    if parts[0] in ('par','lst','ilr','rel','tpc','dct'):
        return parts[0]
    return parts[-2] if len(parts)>2 else 'edition'


def canonicalTarget(href, base, root):
    try:
        url = urlsplit(href)
    except ValueError:
        return None
    if ((url.scheme, url.netloc) != (base.scheme, base.netloc)
            or not url.path.startswith(base.path) or url.query or url.fragment):
        return None
    target = Path(unquote(url.path.removeprefix(base.path)))
    if url.path.endswith('/'):
        target /= 'index.htm'
    if target.is_absolute() or '..' in target.parts or not (root/target).is_file():
        return None
    return target


def audit(root, publicBase):
    root = root.resolve()
    base = urlsplit(publicBase.rstrip('/') + '/')
    if base.scheme not in ('http','https') or not base.netloc or base.query or base.fragment:
        raise ValueError(f'Invalid public base URL: {publicBase!r}')
    totals, seenTitles, issues = Counter(), {}, defaultdict(Counter)

    def report(family, problem, path, detail):
        issues[family][problem] += 1
        if issues[family][problem] <= 3:
            print(f'{path}: {problem} ({detail})')

    for path in root.rglob('*.htm'):
        relative = path.relative_to(root)
        parts = relative.parts
        family = pageFamily(parts)
        totals[family] += 1
        head = PageHead(path)
        if not head.ended:
            report(family, 'unclosed head', relative, 'missing </head>')
        for field, values in (('title',head.titles), ('description',head.descriptions)):
            if len(values) != 1 or not values[0].strip() or '__TITLE__' in values[0] or '__KEYWORDS__' in values[0]:
                report(family, f'invalid {field}', relative, repr(values)[:200])
        preferred = relative
        if head.canonicals:
            target = canonicalTarget(head.canonicals[0], base, root)
            if len(head.canonicals) != 1 or target is None:
                report(family, 'invalid canonical', relative, repr(head.canonicals))
            else:
                preferred = target
        if family in ('par','lst','ilr','rel') and relative != Path(family,'index.htm'):
            book = relative.stem if len(parts) == 2 else parts[1]
            if len(parts) == 2 or path.name == 'index.htm':
                expected = Path(family,book,'index.htm')
                if not head.canonicals or preferred != expected:
                    report(family, 'incorrect book-index canonical', relative, f'expected {expected}')
        if len(head.titles) == 1 and head.titles[0].strip():
            title = ' '.join(head.titles[0].split())
            first = seenTitles.setdefault(title, preferred)
            if preferred != first:
                report(family, 'title collision', relative, f'{first} also uses {title}')
    if not totals:
        raise ValueError(f'No HTML pages found in {root}')
    for family, count in sorted(totals.items()):
        print(f'{family:18} {count:9,} pages   {dict(issues[family])}')
    print(f'{sum(totals.values()):,} pages checked.')
    return not any(issues.values())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('build', type=Path, help='Root of a clean production build')
    parser.add_argument('--public-base', required=True, help='Public URL configured for this build')
    args = parser.parse_args()
    raise SystemExit(0 if audit(args.build, args.public_base) else 1)
