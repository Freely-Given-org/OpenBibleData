#!/usr/bin/env -S uv run
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""Make otherwise missing study-page URLs usable in other versifications.

Run after ALL ordinary book pages have finished, including forked workers.
BOS supplies correspondence; this module only chooses existing site pages.
Ordinary navigation addresses always win, even when a different numbering
system uses the same address for different text. No mappings are guessed.

CHANGELOG:
    2026-10-26 Add explained copies and passage-choice pages for alternate references.
"""
from collections import defaultdict
import logging
from pathlib import Path
import posixpath
import re
from urllib.parse import urlsplit, urlunsplit
from xml.sax.saxutils import escape

from BibleOrgSys.Reference.BibleVersificationMappings import MappingStatus, get_default_mapping_engine
from versification import _referenceLabel, _storedReferences


def _pagePath(reference):
    BBB, C, V, _suffix = reference
    return Path(BBB, f'C{C}V{V}.htm')


def _availableBooks(bible):
    return ({ref[0] for ref in bible} if isinstance(bible, dict)
            else set(bible.availableBBBs) | set(bible.books))


def _sourceProfiles(state, books):
    """Use declared profiles of loaded editions, limited to this build's books.

    Source storage layouts are explicit in settings (e.g. combined LXX Ezra).
    Their physical book names must not be mistaken for profile book identities.
    """
    profiles = defaultdict(set)
    for version in state.BibleVersions:
        bible = state.preloadedBibles.get(version)
        if bible is None:
            continue
        profile = state.BibleVersifications.get(version)
        if not profile and not isinstance(bible, dict):
            profile = bible.getVersificationSystemName()
        if not profile or profile == state.navigationVersification:
            continue
        available = _availableBooks(bible)
        layouts = getattr(state, 'BibleSourceBookLayouts', {}).get(version, {})
        # Keep only logical books whose stored text is included in this build.
        logicalBooks = (available & set(books)) - {
            stored for layout in layouts.values() for _, _, stored, _ in layout}
        logicalBooks.update(book for book, layout in layouts.items()
            if any(stored in available and stored in books for _, _, stored, _ in layout))
        for book in logicalBooks:
            profiles[profile, book].add(version)
    return profiles


def alternateVerseMappings(folder, books, state):
    """Return exact mappings for missing URLs with ALL ordinary targets present.

    Enumerate BOS's public count tables, then validate every candidate through
    its passage mapper (including omissions and complete merge groups). Verse
    zero is reserved for the site's title/introduction pages. Unsupported or
    ambiguous mappings are reported, never converted into guessed redirects.
    """
    engine = get_default_mapping_engine()
    navigation = engine.get_legacy_tables(state.navigationVersification)['CV']
    profiles = _sourceProfiles(state, books)
    tables = {}
    available = {version:_availableBooks(state.preloadedBibles[version])
                 for versions in profiles.values() for version in versions}
    aliases = defaultdict(list)
    missing = defaultdict(int)
    for (profile, book), versions in sorted(profiles.items()):
        if engine.capabilities(profile)['status'] == 'unsupported':
            logging.warning(f'Cannot create alternate verse pages for {profile} {book}: no verified mapping profile')
            continue
        if profile not in tables:
            tables[profile] = engine.get_legacy_tables(profile)['CV']
        counts = tables[profile].get(book, {})
        for chapter, count in counts.items():
            if chapter == 'numChapters':
                continue
            chapterVersions = defaultdict(set)
            for version in versions:
                storedBook, storedChapter, _, _ = _storedReferences(version, ((book,chapter,'1',None),), state)[0]
                if storedBook in books and storedBook in available[version]:
                    chapterVersions[storedBook,storedChapter].add(version)
            for (storedBook, storedChapter), storedVersions in chapterVersions.items():
                ordinary = navigation.get(storedBook, {})
                # Reserve every ordinary address, even if its page was not built.
                for verse in range(int(ordinary.get(storedChapter, 0)) + 1, int(count) + 1):
                    reference = (book, chapter, str(verse), None)
                    storedReference = (storedBook, storedChapter, str(verse), None)
                    if (folder / _pagePath(storedReference)).exists():
                        continue # Never overwrite an existing page.
                    result = engine.convert_passage(profile, state.navigationVersification, (reference,))
                    if result.status != MappingStatus.EXACT or not result.references:
                        missing[profile, book, result.status.value] += 1
                        continue
                    targets = tuple(dict.fromkeys(_pagePath(ref) for ref in result.references))
                    if not all((folder / target).is_file() for target in targets):
                        missing[profile, book, 'target page not built'] += 1
                        continue
                    aliases[storedReference].append((tuple(sorted(storedVersions)), result))
    for (profile, book, reason), count in sorted(missing.items()):
        logging.warning(f'Skipped {count} alternate {profile} {book} references: {reason}')
    return dict(aliases)


def _relativeUrl(url, source, destination):
    """Preserve resources and navigation when copying between book folders."""
    parts = urlsplit(url)
    if parts.scheme or parts.netloc or not parts.path or parts.path.startswith('/'):
        return url
    path = posixpath.relpath(posixpath.normpath(posixpath.join(source.parent.as_posix(), parts.path)),
                            destination.parent.as_posix())
    return urlunsplit(('', '', path, parts.query, parts.fragment))


def alternateVerseHtml(reference, matches, folder, navigationName, pageType):
    """Copy a unique destination; show all links for groups or differing systems.

    Keep text, ids, scripts and controls from the ordinary page. Move #Top to
    the explanation so arrivals with that fragment see why the numbers differ.
    A canonical link identifies a duplicate; choice pages have no single one.
    """
    destination = _pagePath(reference)
    label = _referenceLabel((reference,))
    navigationLabel = 'OET-RV / English' if navigationName in ('eng', 'OET-RV') else navigationName
    paragraphs = []
    targets = set()
    for versions, result in matches:
        paths = tuple(dict.fromkeys(_pagePath(ref) for ref in result.references))
        targets.update(paths)
        links = []
        for path in paths:
            refs = tuple(ref for ref in result.references if _pagePath(ref) == path)
            href = posixpath.relpath(path.as_posix(), destination.parent.as_posix())
            links.append(f'<a href="{href}#Top">{escape(navigationLabel)} {_referenceLabel(refs)}</a>')
        coverage = (f' The complete passage is {escape(_referenceLabel(result.source_references))}.'
                    if result.is_expanded else '')
        paragraphs.append(f'<p class="note">In {escape(", ".join(versions))} '
            f'({escape(result.source_system)} numbering), <b>{label}</b> corresponds to '
            f'{" and ".join(links)}.{coverage}</p>')
    explanation = (f'<div id="Top"><h2>About verse numbering: {label}</h2>\n'
        f'<p class="note">Bible versions divide some chapters and verses differently '
        f'(called “versification”). {label} is valid in the numbering listed below, '
        f'but is outside the {escape(navigationLabel)} numbering used for the ordinary '
        f'{pageType} pages.</p>\n' + '\n'.join(paragraphs))
    title = f'{label} — alternate verse numbering — {pageType.title()}'
    if len(targets) == 1:
        target = next(iter(targets))
        document = (folder / target).read_text(encoding='utf-8')
        document = re.sub(r'\b(href|src|action|poster)="([^"]*)"',
            lambda match: f'{match[1]}="{_relativeUrl(match[2], target, destination)}"', document)
        document = document.replace(' id="Top"', '')
        document, count = re.subn(r'<title>.*?</title>', lambda _: f'<title>{escape(title)}</title>',
                                 document, count=1, flags=re.DOTALL)
        assert count == 1, f'Missing title in {folder / target}'
        canonical = posixpath.relpath(target.as_posix(), destination.parent.as_posix())
        document = document.replace('</head>', f'<link rel="canonical" href="{canonical}">\n</head>', 1)
        explanation += (f'<p class="note">The page below is a copy of the '
            f'<a href="{canonical}#Top">ordinary {escape(navigationLabel)} page</a>; '
            'its headings and navigation retain that numbering.</p></div>\n')
        document, count = re.subn(r'<body\b[^>]*>', lambda match: match[0] + '\n' + explanation,
                                 document, count=1)
        assert count == 1, f'Missing body in {folder / target}'
        return document
    explanation += ('<p class="note">This reference has more than one corresponding page. '
        'Follow the links above for the complete passage in the appropriate numbering.</p></div>')
    return (f'<!DOCTYPE html>\n<html lang="en-US"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{escape(title)}</title><link rel="stylesheet" href="../../common.css">'
        f'</head><body>\n{explanation}\n</body></html>')


def createAlternateVersePages(folder, books, state, pageType):
    """Add explained aliases after the ordinary parallel/interlinear page jobs."""
    from html import checkHtml
    aliases = alternateVerseMappings(folder, books, state)
    for reference, matches in aliases.items():
        document = alternateVerseHtml(reference, matches, folder, state.navigationVersification, pageType)
        assert checkHtml(f'Alternate {pageType} {_referenceLabel((reference,))}', document)
        destination = folder / _pagePath(reference)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('x', encoding='utf-8') as output:
            output.write(document)
    logging.info(f'Created {len(aliases)} alternate-numbered {pageType} pages')
    return len(aliases)
