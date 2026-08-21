#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Thin Python wrapper around the Rust convertVerseEntryListToHtml2 function.

Provides the same calling convention as the old usfm.py function so that
callers only need to change their import statement.
"""
import bos_books_codes_py
from openbibledata_rust import convertVerseEntryListToHtml2 as _rust_convert
from settings import State


def convertVerseEntryListToHtml( level:int, versionAbbreviation:str, refTuple:tuple, segmentType:str, contextList:list, verseEntryList:list, basicOnly:bool, state:State ) -> str: # type: ignore[override]
    """
    Convert a list of processed USFM verse entries to an HTML segment.

    This is a thin wrapper around the Rust implementation. All heavy
    processing (character formatting, footnotes, cross-references, figure
    copying, post-processing) happens in Rust.
    """
    BBB = refTuple[0]
    C = refTuple[1] if len(refTuple) > 1 else None
    V = refTuple[2] if len(refTuple) > 2 else None
    is_single_chapter_book = bos_books_codes_py.is_single_chapter_book( BBB )

    result = _rust_convert(
        level=level,
        version_abbreviation=versionAbbreviation,
        bbb=BBB,
        c=C,
        v=V,
        segment_type=segmentType,
        context_list=contextList,
        verse_entries=verseEntryList,
        basic_only=basicOnly,
        is_single_chapter_book=is_single_chapter_book,
        destination_folder=str(state.DESTINATION_FOLDER) if state.DESTINATION_FOLDER else None,
        state=state,
    )
    return result['html'] if isinstance( result, dict ) else result
