#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Build an isolated native-search preview against existing published pages.

Run from createPages. The output must be a new directory; published pages are
referenced through links and are never rewritten. The normal site build does
not require this utility.

CHANGELOG:
    2026-11-01 Add isolated search qualification and coverage measurements.
"""
import argparse
from copy import deepcopy, copy
import json
from pathlib import Path
import resource
import time
import gc


class PreviewSources:
    """Load and release one edition at a time, using the normal source loaders."""
    def __init__(self,state):
        self.state=state

    def __contains__(self,version):
        return version in self.state.BibleLocations

    def __getitem__(self,version):
        from Bibles import preloadVersions
        from versification import configureBibleVersification
        state=self.state
        state.OETRefData={}
        if 'lexicalAssociations' in vars(state):del state.lexicalAssociations
        gc.collect()
        local=copy(state)
        local.BibleVersions=[version]
        local.preloadedBibles={}
        preloadVersions(local)
        bible=local.preloadedBibles[version]
        if not isinstance(bible,dict):configureBibleVersification(bible,version,state)
        if version=='OET-LV':
            from openbibledata_rust import build_word_table_index
            from lexicalLinks import prepareLexicalAssociations
            state.OETRefData={'word_tables':{},'word_table_indexes':{}}
            for name in bible.ESFMWordTables:
                if bible.ESFMWordTables[name] is None:bible.loadESFMWordFile(name)
                rows=bible.ESFMWordTables[name]
                state.OETRefData['word_tables'][name]=rows
                state.OETRefData['word_table_indexes'][name]=build_word_table_index(rows)
            local.OETRefData=state.OETRefData
            state.lexicalAssociations=prepareLexicalAssociations(local)
        return bible


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    selection=parser.add_mutually_exclusive_group()
    selection.add_argument('--versions',nargs='+')
    selection.add_argument('--all-versions',action='store_true')
    parser.add_argument('--books',nargs='+')
    args=parser.parse_args()
    site=args.site.resolve(strict=True)
    output=args.output.resolve()
    if output.exists() or output==site or output.is_relative_to(site):
        parser.error('Choose a new preview directory outside the published site.')
    from settings import State
    import Bibles
    Bibles.WRITE_PICKLES_FLAG=False
    from searchIndex import buildSearch
    from searchPage import searchBody
    import BibleOrgSys.BibleOrgSysGlobals as globals
    globals.preloadCommonData()
    started=time.monotonic()
    state=deepcopy(State())
    args.versions=([v for v in state.BibleVersions if v in state.BibleLocations and v not in ('OET','TOSN','TTN','UTN','SOTN','UHG','UGG')] if args.all_versions else args.versions or ['OET-RV'])
    state.BibleVersions=args.versions[:]
    state.preloadedBibles=PreviewSources(state)
    state.TEST_VERSIONS_ONLY=args.versions[:]
    # This changes only this isolated state; settings.py remains in test mode.
    state.ALL_PRODUCTION_BOOKS_FLAG=not bool(args.books)
    state.TEST_MODE_FLAG=bool(args.books)
    state.TEST_BOOK_LIST=args.books or []
    state.REUSE_EXISTING_WORD_PAGES_FLAG=False
    state.UPDATE_ACTUAL_SITE_WHEN_BUILT_FLAG=False
    state.DESTINATION_FOLDER=site
    state.TEMP_BUILD_FOLDER=output
    state.booksToLoad=deepcopy(state.booksToLoad)
    for version in args.versions:
        if version not in state.BibleLocations:
            parser.error(f'No source configured for {version}')
        state.booksToLoad[version]=args.books or ['ALL']
    output.mkdir(parents=True)
    for path in site.iterdir():
        if path.is_dir() and path.name not in ('search','pagefind'):
            (output/path.name).symlink_to(path,target_is_directory=True)
        elif path.is_file() and path.suffix in ('.css','.js','.png','.jpg','.svg','.ico'):
            (output/path.name).symlink_to(path)
    report=buildSearch(output,state)
    page=f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>OBD Search preview</title><link rel="stylesheet" href="{state.searchClient}Search.css"><script type="module" src="{state.searchClient}search.js"></script></head><body>{searchBody(state.searchManifest)}</body></html>'
    (output/'Search.htm').write_text(page,encoding='utf-8')
    report.update(totalSeconds=round(time.monotonic()-started,3),peakMiB=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,1))
    (output/'search/qualification.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
