#!/usr/bin/env -S uv run
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""Apply machine-local test settings without exposing them in the repository.

CHANGELOG:
    2026-10-23 Separate private destinations, staging, and Bible definitions.
    2026-11-01 Reserve the native search output folder.
"""
from copy import deepcopy
from pathlib import Path
import re
import tomllib


PRIVATE_SETTINGS_PATH = Path(__file__).with_name('privateSettings.toml')
_PAGE_FOLDERS = {'par', 'lst', 'ilr', 'rel', 'tpc', 'ref', 'app', 'dct', 'UBS',
                 'pagefind', 'search', 'PLBL', 'HAP', 'SOTN', 'UTN', 'TOSN', 'TOBD', 'THBD', 'BMM', 'OBI'}


def configurePrivateBuild(state, *, debug=False, configPath=PRIVATE_SETTINGS_PATH):
    """Configure a test/debug destination; apply private sources only in TEST mode.

    A production import never reads the local file. Missing/invalid private
    configuration stops a test build before any files are written or removed.
    """
    if not state.TEST_MODE_FLAG and not debug:
        return
    try:
        with Path(configPath).open('rb') as source:
            config = tomllib.load(source)
    except FileNotFoundError as error:
        raise RuntimeError('Private test settings are missing. Copy privateSettings.example.toml '
                           'to createPages/privateSettings.toml and choose a local destination.') from error
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f'Invalid privateSettings.toml: {error}') from error
    if config.keys() - {'destination_folder', 'versions'}:
        raise ValueError('privateSettings.toml supports only destination_folder and versions.')
    folder = config.get('destination_folder')
    if not isinstance(folder, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', folder):
        raise ValueError('privateSettings.toml: destination_folder must be a single folder name '
                         'containing letters, digits, underscores or hyphens.')
    reserved = _PAGE_FOLDERS | set(state.BibleNames)
    if folder.casefold() in {name.casefold() for name in reserved}:
        raise ValueError('privateSettings.toml: destination_folder conflicts with a public page folder.')
    destination = state.NORMAL_DESTINATION_FOLDER / folder
    if destination.is_symlink() or destination.resolve().parent != state.NORMAL_DESTINATION_FOLDER.resolve():
        raise ValueError('privateSettings.toml: destination_folder must not be a symbolic link.')
    state.DEBUG_DESTINATION_FOLDER_NAME = folder
    state.DEBUG_DESTINATION_FOLDER_PATH = state.DESTINATION_FOLDER = destination
    # Never leave private-only edition folders in production's staging directory.
    state.TEMP_BUILD_FOLDER = state.NORMAL_DESTINATION_FOLDER.parent / '.cache' / 'privateBuild' / folder
    if not state.TEST_MODE_FLAG:
        return

    # Private editions must not populate the public source caches, even when
    # their files share a directory with a publicly configured edition.
    state.PICKLE_FILENAME_END = '.OBD_Private_Bible.pickle'
    state.SUBSTITUTED_VERSIONS_FOLDER = state.SUBSTITUTED_VERSIONS_FOLDER / 'private' / folder

    versions = config.get('versions', {})
    if not isinstance(versions, dict):
        raise ValueError('privateSettings.toml: versions must contain tables keyed by abbreviation.')
    # Copy inherited collections so configuring an instance cannot change public defaults.
    for attribute in ('BibleVersions', 'BibleLocations', 'BibleNames', 'BibleLanguages',
                      'BibleVersifications', 'BibleSourceFormats', 'BibleVersionDecorations',
                      'booksToLoad', 'detailsHtml', 'VERSIONS_WITHOUT_OT', 'VERSIONS_WITHOUT_NT'):
        setattr(state, attribute, deepcopy(getattr(state, attribute)))
    for abbreviation, definition in versions.items():
        _configurePrivateVersion(state, abbreviation, definition)
    state.allPossibleBibleVersions = state.BibleVersions[:]


def _configurePrivateVersion(state, abbreviation, definition):
    """Add a full local edition, or replace a public edition for test builds only."""
    context = f'privateSettings.toml: versions.{abbreviation}'
    if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', abbreviation)
            or abbreviation in _PAGE_FOLDERS or abbreviation in state.auxilliaryVersions):
        raise ValueError(f'{context}: use a Bible abbreviation, not a page-folder name.')
    fields = {'location', 'format', 'name', 'language', 'versification', 'after',
              'books', 'testament', 'own_pages', 'details'}
    if not isinstance(definition, dict) or definition.keys() - fields:
        raise ValueError(f'{context}: unsupported setting; see privateSettings.example.toml.')
    required = {'location', 'format'}
    if abbreviation not in state.BibleVersions:
        required |= {'name', 'language', 'versification', 'details'}
    if missing := required - definition.keys():
        raise ValueError(f'{context}: missing {", ".join(sorted(missing))}.')
    for field in ('location', 'format', 'name', 'language', 'versification', 'after'):
        if field in definition and (not isinstance(definition[field], str) or not definition[field].strip()):
            raise ValueError(f'{context}.{field}: expected a nonempty string.')
    if definition['format'] not in ('USFM', 'USX'):
        raise ValueError(f'{context}.format: supported private source formats are USFM and USX.')
    if 'own_pages' in definition and not isinstance(definition['own_pages'], bool):
        raise ValueError(f'{context}.own_pages: expected true or false.')
    testament = definition.get('testament')
    if testament is not None and testament not in ('OT', 'NT', 'both'):
        raise ValueError(f'{context}.testament: expected OT, NT or both.')
    books = definition.get('books',
        state.TEST_OT_BOOK_LIST if testament == 'OT' else
        state.TEST_NT_BOOK_LIST if testament == 'NT' else
        state.booksToLoad.get(abbreviation, state.TEST_BOOK_LIST))
    if not isinstance(books, list) or not books or any(not isinstance(book, str) or not book for book in books):
        raise ValueError(f'{context}.books: expected a nonempty list of book codes.')
    details = dict(state.detailsHtml.get(abbreviation, {}))
    extraDetails = definition.get('details', {})
    if not isinstance(extraDetails, dict) or any(not isinstance(value, str) for value in extraDetails.values()):
        raise ValueError(f'{context}.details: expected HTML strings.')
    details.update(extraDetails)
    if not {'about', 'copyright', 'licence'} <= details.keys():
        raise ValueError(f'{context}.details: include about, copyright and licence HTML.')
    after = definition.get('after')
    if after is not None and (after == abbreviation or after not in state.BibleVersions):
        raise ValueError(f'{context}.after: choose an earlier configured Bible abbreviation.')

    if abbreviation not in state.BibleVersions:
        state.BibleVersions.append(abbreviation)
    if after is not None:
        state.BibleVersions.remove(abbreviation)
        state.BibleVersions.insert(state.BibleVersions.index(after) + 1, abbreviation)
    for field, attribute in (('location', 'BibleLocations'), ('format', 'BibleSourceFormats'),
                             ('name', 'BibleNames'), ('language', 'BibleLanguages'),
                             ('versification', 'BibleVersifications')):
        if field in definition:
            getattr(state, attribute)[abbreviation] = definition[field]
    state.booksToLoad[abbreviation] = books[:]
    state.detailsHtml[abbreviation] = details
    state.BibleVersionDecorations.setdefault(abbreviation, ('', ''))
    if testament is not None:
        for attribute, included in (('VERSIONS_WITHOUT_OT', testament == 'NT'),
                                    ('VERSIONS_WITHOUT_NT', testament == 'OT')):
            versions = getattr(state, attribute)
            if abbreviation in versions:
                versions.remove(abbreviation)
            if included:
                versions.append(abbreviation)
    # A local full edition can replace a publicly quoted, selected-verse edition.
    selected = [(version, limit) for version, limit in
                zip(state.selectedVersesOnlyVersions, state.numAllowedSelectedVerses)
                if version != abbreviation]
    state.selectedVersesOnlyVersions = tuple(version for version, _ in selected)
    state.numAllowedSelectedVerses = tuple(limit for _, limit in selected)
    if 'own_pages' in definition:
        withoutPages = tuple(version for version in state.versionsWithoutTheirOwnPages if version != abbreviation)
        state.versionsWithoutTheirOwnPages = withoutPages if definition['own_pages'] else withoutPages + (abbreviation,)
