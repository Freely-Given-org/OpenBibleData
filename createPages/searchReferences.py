#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Book aliases shared by search reference catalogues.

CHANGELOG:
    2026-11-01 Export BOS and OET names without assuming a 66-book corpus.
"""
def bookAliases(book):
    import bos_books_codes_py as codes
    from openbibledata_rust import getOETBookName
    values = [book]
    for function in ('get_english_name_nr','bos_book_code_to_usfm_abbrev','get_short_abbreviation', 'get_sbl_abbreviation', 'bos_to_osis_book_code'):
        try:
            value = getattr(codes, function)(book)
        except (KeyError, ValueError):
            continue
        if value:
            values.append(value)
    try:
        values.append(getOETBookName(book))
    except (AssertionError, KeyError, ValueError):
        pass
    common = {'JHN': ('Jn', 'Joh'), 'MRK': ('Mk',), 'MAT': ('Mt',), 'LUK': ('Lk',),
              'PSA': ('Psalm', 'Psalms', 'Ps'), 'JDE': ('Jude',), 'PHM': ('Philemon',)}
    values.extend(common.get(book, ()))
    import re
    for value in values[:]:
        prefix=re.match(r'^[1-4] ',value)
        for part in value.split('/'):
            part=part.strip('()')
            if prefix and not part.startswith(prefix[0]):part=prefix[0]+part
            values.append(part)
    return sorted(set(value for value in values if value))


def searchBookName(book, version):
    from navigation import bookName
    import bos_books_codes_py as codes
    try:
        return bookName(book, version)
    except (AssertionError, KeyError, ValueError):
        try:
            return codes.get_english_name_nr(book) or book
        except (KeyError,ValueError):
            return book
