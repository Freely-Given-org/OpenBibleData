#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Deterministic, bounded Bible search indexes for a static host.

CHANGELOG:
    2026-11-01 Build immutable positional shards and independent passage catalogues.
"""
from collections import defaultdict
from hashlib import sha256
import gzip
import json
from pathlib import Path
import shutil
import time
import re

from searchRecords import FORMAT_VERSION, PublishedPages, exportBook
from searchText import tokens, normalize

BUCKETS = 32
BLOCK_SIZE = 128


def jsonBytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def bucket(term):
    value = 2166136261
    for byte in term.encode('utf-8'):
        value = ((value ^ byte) * 16777619) & 0xffffffff
    return value % BUCKETS


def artifact(root, prefix, value):
    data = jsonBytes(value)
    # Explicit gzip payloads avoid depending on the static host's HTTP compression.
    # The .bin suffix prevents servers from transparently decoding this payload.
    data = gzip.compress(data, compresslevel=6, mtime=0)
    name = f'{prefix}-{sha256(data).hexdigest()[:24]}.bin'
    path = root / name
    if not path.exists():
        path.write_bytes(data)
    return name


def buildPartition(records, root, *, version, book, name='', aliases=(), group='OTHER', order=0, cached=None, cacheRoot=None):
    """One version/book in memory; term shards and result blocks are independent."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    records = list(records)
    implementation = sha256(b''.join(Path(__file__).with_name(name).read_bytes() for name in
        ('searchText.py','searchRecords.py','searchReferences.py','searchIndex.py','searchSupplement.py','searchLexical.py'))).hexdigest()
    fingerprint = sha256(jsonBytes([implementation,version,book,name,list(aliases),group,order,records])).hexdigest()
    if cached and cached.get('inputHash') == fingerprint and cacheRoot:
        filenames = set(cached['blocks']) | set(cached['buckets'].values()) | {cached['catalogue']}
        valid = True
        for filename in filenames:
            path = Path(cacheRoot) / filename
            if Path(filename).name != filename or not path.is_file() or sha256(path.read_bytes()).hexdigest()[:24] != path.stem.rsplit('-',1)[1]:
                valid = False
                break
        if valid:
            for filename in filenames:
                if (Path(cacheRoot)/filename).resolve() != (root/filename).resolve():
                    shutil.copy2(Path(cacheRoot)/filename,root/filename)
            return dict(cached)
    postings = [defaultdict(list) for _ in range(BUCKETS)]
    documents, references, blockFiles, documentRefs = [], [], [], []
    fields = set()
    sourceKeys = set()
    count = 0
    fieldCounts = defaultdict(int)
    language = 'und'
    for record in records:
        if record['key'] in sourceKeys:
            raise ValueError(f'Duplicate search record: {record["key"]}')
        sourceKeys.add(record['key'])
        language = record['language']
        for field, text in sorted(record['fields'].items()):
            wordTokens = tokens(text)
            if not wordTokens:
                continue
            fields.add(field)
            fieldCounts[field] += 1
            row = dict(reference=len(references), field=field, text=text)
            documents.append(row)
            documentRefs.append([len(references), field])
            byTerm = defaultdict(list)
            for position, token in enumerate(wordTokens):
                byTerm[token[0], token[1]].append(position)
            for (term, exact), positions in byTerm.items():
                postings[bucket(term)][term].append([count, field, positions, exact])
            count += 1
            if len(documents) == BLOCK_SIZE:
                blockFiles.append(artifact(root, 'records', documents))
                documents = []
        if record.get('annotations'):
            fields.add('original')
            fieldCounts['original'] += 1
            row=dict(reference=len(references),field='original',text=record['fields'].get('body',''),annotations=record['annotations'])
            documents.append(row)
            documentRefs.append([len(references),'original'])
            byTerm=defaultdict(list)
            for position,word in enumerate(record['annotations']):
                for kind in ('lemma','form','strong'):
                    values=word.get(kind,[])
                    if isinstance(values,str):values=[values]
                    for value in values:
                        if value:
                            byTerm[f'@{kind}:{normalize(value)}',normalize(value,accents=True),word.get('morphology','')].append(position)
            for (term,exact,morphology),positions in byTerm.items():
                postings[bucket(term)][term].append([count,'original',positions,exact,morphology])
            count+=1
            if len(documents)==BLOCK_SIZE:
                blockFiles.append(artifact(root,'records',documents));documents=[]
        references.append(dict(key=record['key'],ref=record['ref'], links=record['links'],mapped=record.get('mapped',[]),mapping=record.get('mapping','unavailable')))
    if documents:
        blockFiles.append(artifact(root, 'records', documents))
    if not count:
        return None
    import bos_books_codes_py
    partition = dict(version=version, book=book, name=name or book, aliases=list(aliases),inputHash=fingerprint,
                     singleChapter=bos_books_codes_py.is_single_chapter_book(book),
                     group=group, order=order, language=language, count=count, passages=len(references),
                     fields=sorted(fields), fieldCounts=dict(fieldCounts), blocks=blockFiles, blockSize=BLOCK_SIZE,
                     chapters=sorted({r['ref'][1] for r in references}, key=int),
                     catalogue=artifact(root,'catalogue',dict(references=references,documents=documentRefs)),
                     buckets={str(i): artifact(root, 'terms', terms) for i, terms in enumerate(postings) if terms})
    return partition


def _buildSearch(root, state, pages):
    """Build from loaded sources after pages exist, before releasing the Bibles."""
    import bos_books_codes_py as codes
    from searchReferences import bookAliases, searchBookName as bookName
    from BibleOrgSys.BibleOrgSysGlobals import BOOKLIST_OT39, BOOKLIST_NT27
    from searchSupplement import supplementFiles, supplementRecords
    started = time.monotonic()
    root = Path(root)
    output = root / 'search'
    output.mkdir(parents=True, exist_ok=True)
    partitions = []
    versions = []
    supplements = supplementFiles(root)
    cacheRoot = Path(state.DESTINATION_FOLDER) / 'search'
    cached = {}
    try:
        prior = json.loads((cacheRoot/'manifest.json').read_text())
        if prior['format'] == FORMAT_VERSION:
            cached = {(p['version'],p['book']):p for p in prior['partitions']}
    except (FileNotFoundError,KeyError,ValueError,TypeError):
        pass # A missing or incompatible search generation is rebuilt from sources.
    for version in state.BibleVersions:
        if version in ('OET', 'TOSN', 'TTN', 'UTN', 'SOTN', 'UHG', 'UGG') or version not in state.preloadedBibles:
            continue
        bible = state.preloadedBibles[version]
        books = sorted({ref[0] for ref in bible}) if isinstance(bible, dict) else list(bible.books)
        selected = state.booksToLoad.get(version, ())
        books = [b for b in books if 'ALL' in selected or b in selected
                 or 'OT' in selected and codes.is_old_testament_nr(b)
                 or 'NT' in selected and codes.is_new_testament_nr(b)]
        books = codes.get_sequence_list(books)
        for book in books:
            if book in ('FRT', 'INT', 'BAK') or book.startswith('XX'):
                continue
            order = state.OET_BOOK_ORDER.index(book) if book in state.OET_BOOK_ORDER else 999
            extras = supplementRecords(supplements.pop((version,book), ()), pages)
            def rows():
                for record in exportBook(version, book, bible, state, pages):
                    if extra := extras.pop(record['key'], None):
                        record['fields'].update(extra['fields'])
                    yield record
                yield from extras.values()
            partition = buildPartition(rows(), output,
                version=version, book=book, name=bookName(book, version), aliases=bookAliases(book),
                group='OT' if codes.is_old_testament_nr(book) else 'NT' if codes.is_new_testament_nr(book) else 'DC',
                order=order, cached=cached.get((version,book)),cacheRoot=cacheRoot)
            if partition:
                partition['traditionalOrder'] = codes.get_sequence_number(book)
                partitions.append(partition)
                print(f"  Indexed {version} {book}: {partition['passages']:,} passages", flush=True)
        if any(p['version'] == version for p in partitions):
            versions.append(dict(id=version, name=state.BibleNames.get(version, version)))
        del bible
    for (version,book), paths in sorted(supplements.items()):
        rows = supplementRecords(paths, pages)
        partition = buildPartition(rows.values(), output, version=version, book=book,
            name=bookName(book, 'OET'), aliases=bookAliases(book),
            group='OT' if codes.is_old_testament_nr(book) else 'NT' if codes.is_new_testament_nr(book) else 'DC',
            order=state.OET_BOOK_ORDER.index(book) if book in state.OET_BOOK_ORDER else 999)
        if partition:
            partition['traditionalOrder'] = codes.get_sequence_number(book)
            partitions.append(partition)
            if not any(v['id']==version for v in versions):
                versions.append(dict(id=version,name=state.BibleNames.get(version,version)))
    if not partitions:
        raise ValueError('Search index has no published passages; refusing to publish an empty search.')
    clientNames = ('search.js', 'searchCore.js', 'searchWorker.js', 'Search.css')
    clientHash = sha256(b''.join(Path(__file__).with_name(name).read_bytes() for name in clientNames)).hexdigest()[:24]
    client = f'client-{clientHash}'
    (output/client).mkdir(exist_ok=True)
    for filename in clientNames:
        shutil.copy2(Path(__file__).with_name(filename), output/client/filename)
    manifest = dict(format=FORMAT_VERSION, buckets=BUCKETS, versions=versions, partitions=partitions,client=client,
                    limits=dict(cacheMiB=getattr(state,'SEARCH_CACHE_MIB',64),concurrency=getattr(state,'SEARCH_FETCH_CONCURRENCY',6)),
                    books=[dict(book=b,name=bookName(b,'OET'),aliases=bookAliases(b),singleChapter=codes.is_single_chapter_book(b))
                           for b in dict.fromkeys([*state.OET_BOOK_ORDER,*BOOKLIST_OT39,*BOOKLIST_NT27])
                           if b not in ('INT','FRT','CNC','GLS','GLO','TDX','NDX','OTH','BAK') and not b.startswith('XX')],
                    test=bool(state.TEST_MODE_FLAG), normalization='nfd-lower-sigma-joiner-marks-v2',
                    omissions=[dict(version=v,book=b,count=counts['malformedReferences']) for (v,b),counts in sorted(pages.coverage.items()) if counts['malformedReferences']])
    manifest['generation'] = sha256(jsonBytes(manifest)).hexdigest()[:24]
    manifestName = artifact(output, 'manifest', manifest)
    (output / 'manifest.json').write_bytes(jsonBytes(manifest))
    summary = dict(generation=manifest['generation'], manifest=manifestName,
                   passages=sum(p['passages'] for p in partitions), fields=sum(p['count'] for p in partitions),
                   versions=len(versions), partitions=len(partitions), seconds=round(time.monotonic()-started, 3),
                   bytes=sum(p.stat().st_size for p in output.rglob('*') if p.is_file()),
                   coverage=[dict(version=v,book=b,**counts) for (v,b),counts in sorted(pages.coverage.items())],issues=pages.issues)
    (output / 'build-report.json').write_bytes(jsonBytes(summary))
    state.searchManifest = manifestName
    state.searchClient = f'search/{client}/'
    return summary


def buildSearch(root, state):
    with PublishedPages(root, state.DESTINATION_FOLDER if state.REUSE_EXISTING_WORD_PAGES_FLAG else None) as pages:
        return _buildSearch(root, state, pages)


def validateSearch(root):
    """Validate the complete staged generation before changing any live pointer."""
    root=Path(root)
    manifest=json.loads((root/'search/manifest.json').read_text())
    if manifest.get('format')!=FORMAT_VERSION:
        raise ValueError('Incompatible search format; publication stopped.')
    files=set()
    for p in manifest['partitions']:
        files.update(p['blocks']);files.update(p['buckets'].values());files.add(p['catalogue'])
    page=(root/'Search.htm').read_text()
    pinned=re.search(r'data-manifest="search/(manifest-[a-f0-9]{24}\.bin)"',page)
    if not pinned or f'{manifest["client"]}/search.js' not in page:
        raise ValueError('Search page does not identify its immutable client and catalogue.')
    files.add(pinned[1])
    if json.loads(gzip.decompress((root/'search'/pinned[1]).read_bytes()))!=manifest:
        raise ValueError('Search page and manifest describe different generations.')
    for name in files:
        if not re.fullmatch(r'[a-z]+-[a-f0-9]{24}\.bin',name):
            raise ValueError(f'Invalid search artifact name: {name}')
        path=root/'search'/name
        if not path.is_file() or sha256(path.read_bytes()).hexdigest()[:24]!=path.stem.rsplit('-',1)[1]:
            raise ValueError(f'Missing or corrupted search artifact: {name}')
    clientNames=('search.js','searchCore.js','searchWorker.js','Search.css')
    if not re.fullmatch(r'client-[a-f0-9]{24}',manifest['client']):
        raise ValueError('Invalid search client directory.')
    clientHash=sha256(b''.join((root/'search'/manifest['client']/name).read_bytes() for name in clientNames)).hexdigest()[:24]
    if manifest['client']!=f'client-{clientHash}':
        raise ValueError('Search client files are incomplete or corrupted.')
    return manifest


def publishSearch(buildRoot, destination):
    """Install immutable files first, then atomically replace the current pointers."""
    import os
    buildRoot, destination = Path(buildRoot), Path(destination)
    manifest=validateSearch(buildRoot)
    target = destination / 'search'
    target.mkdir(parents=True, exist_ok=True)
    names={re.search(r'data-manifest="search/(manifest-[a-f0-9]{24}\.bin)"',(buildRoot/'Search.htm').read_text())[1]}
    for partition in manifest['partitions']:
        names.update(partition['blocks']);names.update(partition['buckets'].values());names.add(partition['catalogue'])
    names.update(f'{manifest["client"]}/{name}' for name in ('search.js','searchCore.js','searchWorker.js','Search.css'))
    for name in sorted(names):
        path=buildRoot/'search'/name
        destinationPath = target/name
        destinationPath.parent.mkdir(parents=True,exist_ok=True)
        # A corrupt or interrupted old copy is repaired using the validated file.
        # Unreferenced staging files are never copied into a restricted build.
        if not destinationPath.exists() or destinationPath.read_bytes()!=path.read_bytes():
            temporary = destinationPath.with_name(destinationPath.name + '.tmp')
            shutil.copyfile(path, temporary)
            os.replace(temporary, destinationPath)
    for name in ('search/manifest.json', 'search/build-report.json', 'Search.htm'):
        source = buildRoot / name
        temporary = destination / (name + '.tmp')
        shutil.copyfile(source, temporary)
        os.replace(temporary, destination / name)
