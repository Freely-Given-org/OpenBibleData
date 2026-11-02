#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Shared discovery controls for reference indexes.

CHANGELOG:
    2026-10-31 Add available cross-family destinations, glosses and bounded filtering.
    2026-11-01 Group word occurrences with readable references, glosses and transliterations.
"""
import re
import json
import unicodedata
from urllib.parse import quote,unquote
from xml.sax.saxutils import escape,unescape


def wordIndexRecord(language, filename, word, fields):
    """Retain the exact generated target and plain, searchable occurrence context."""
    from referenceOccurrences import _gloss
    record=dict(word=word,language='Hebrew' if language=='Heb' else 'Greek',
                href=f'{filename}#Top',ref=fields[0],gloss=_gloss(language,fields))
    if language=='Grk' and not fields[7]:record['status']='Unused NT variant'
    return record


def dcWordIndexRecords(state, relativeFolder=''):
    """Use the same book selection and row anchors as the DC detail writer."""
    bible=getattr(state,'preloadedBibles',{}).get('OET-LV')
    selected=state.booksToLoad.get('OET-LV',())
    records=[]
    for number,row in enumerate(state.OETRefData.get('word_tables',{}).get('OET-LV_DC_word_table.tsv',())[1:],1):
        fields=row.split('\t')
        match=re.fullmatch(r'([A-Z0-9]{3})_(\d+):(\d+[a-z]?)w(\d+)',fields[0])
        assert match, fields[0]
        book=state.OET_SOURCE_BOOK_ALIASES.get(match[1],match[1])
        if bible is None or book not in bible or ('ALL' not in selected and book not in selected):continue
        records.append(dict(word=fields[1],language='Latin' if book=='LAO' else 'Greek',
            href=f'{relativeFolder}{book}_C{match[2]}.htm#W{number}',
            ref=f'{book}_{match[2]}:{match[3]}w{match[4]}',
            gloss=glossSummary([fields[5] or fields[4]]),status='DC draft'))
    return records


def groupWordIndex(records, transliterator):
    """Group spellings (ignoring capitalisation), without merging lexical senses."""
    from settings import reorderBooksForOETVersions
    books=reorderBooksForOETVersions(list({row['ref'][:3] for row in records}))
    bookOrder={book:index for index,book in enumerate(books)}
    def occurrenceOrder(row):
        match=re.fullmatch(r'([A-Z0-9]{3})_(\d+):(\d+)([a-z]*)w(\d+)',row['ref'])
        assert match, row
        return bookOrder[match[1]],int(match[2]),int(match[3]),match[4],int(match[5])
    groups={}
    for row in records:
        word=row['word']
        key=row['language'],unicodedata.normalize('NFC',word).casefold()
        if key not in groups:
            groups[key]=dict(word=word,language=row['language'],
                transliteration=word if row['language']=='Latin' else transliterator(word),occurrences=[])
        groups[key]['occurrences'].append({key:value for key,value in row.items() if key not in ('word','language')})
    for group in groups.values():
        group['occurrences'].sort(key=occurrenceOrder)
    return sorted(groups.values(),key=lambda group:group['word'].casefold())


def wordIndex(level, groups, outputFolder, *, transliterated=False):
    """Search one spelling at a time; keep every occurrence in the static fallback."""
    stem='transIndex' if transliterated else 'index'
    if not transliterated:
        (outputFolder/'words.json').write_text(json.dumps(groups,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    ordered=sorted(groups,key=lambda group:group['transliteration'].casefold()) if transliterated else groups
    def label(group):
        first,second=(group['transliteration'],group['word']) if transliterated else (group['word'],group['transliteration'])
        if first==second:return escape(first or '(blank)')
        return f'{escape(first or "(blank)")} ({escape(second)})'
    complete=[]
    for group in ordered:
        rows=[]
        for row in group['occurrences']:
            reference=row['ref'].replace('_',' ').replace('w',', word ')
            description=f'{reference} — {row["gloss"] or "(no gloss)"}'+(f' ({row["status"]})' if row.get('status') else '')
            title=escape(f'{group["word"]} ({group["transliteration"]}) — {description}',{'"':'&quot;'})
            rows.append(f'<li><a href="{escape(row["href"],{chr(34):"&quot;"})}" title="{title}">{escape(description)}</a></li>')
        complete.append(f'<details><summary>{label(group)} — {group["language"]} — {len(rows):,} {"occurrence" if len(rows)==1 else "occurrences"}</summary><ol>{"".join(rows)}</ol></details>')
    title='Complete word index'
    (outputFolder/f'{stem}-all.htm').write_text(
        f'<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{title}</title><link rel="stylesheet" href="{"../"*level}BibleSite.css">'
        f'<link rel="stylesheet" href="{"../"*level}common.css"></head><body><h1 id="Top">{title}</h1>'
        f'<p><a href="{stem}.htm#Top">Return to searchable index</a></p>{"".join(complete)}</body></html>',encoding='utf-8')
    example=('tov','ţōⱱ') if groups and all(group['language']=='Hebrew' for group in groups) else ('Barakiou','Baraⱪiou')
    return (f'<div class="wordIndex" data-source="words.json" data-transliterated="{str(transliterated).lower()}">'
        '<p>Occurrences are grouped by spelling, ignoring capitalisation. Expand a spelling to browse its verse locations and English glosses. '
        'Glosses describe individual uses; a shared spelling need not mean a shared sense.</p>'
        '<div class="referenceIndexControls" hidden>'
        '<label>Find a word <input type="search" placeholder="English gloss, transliteration or verse reference"></label> '
        '<button type="button" data-action="clear">Clear</button> '
        '<label>Book <select data-filter="book"><option value="">All books</option></select></label>'
        f'<p>Use ordinary letters: for example, <b>{example[0]}</b> matches the spelling <b>{example[1]}</b>. '
        'Accents and apostrophes are optional. Original Hebrew or Greek text also works. '
        'You can combine a word with a book code and verse reference.</p></div>'
        '<p class="referenceIndexCount" role="status" aria-live="polite">Loading searchable words…</p>'
        '<div class="wordIndexPages"></div><div class="wordIndexEntries"></div><div class="wordIndexPages"></div>'
        f'<p><a href="{stem}-all.htm#Top">Complete HTML list (large page; also works without JavaScript)</a></p></div>'
        f'<script src="{"../"*level}referenceIndex.js" defer></script>')


def referenceIndexLinks(level, state, *, includeCore=False):
    links = []
    prefix = '../'*level
    if includeCore:
        links.append(('ref/index.htm','All reference resources'))
        for language,name,grammar in (('Heb','Hebrew','UHG'),('Grk','Greek','UGG')):
            for family,label in (('Wrd','words'),('Lem','lemmas'),('Strng','Strong’s numbers')):
                links.append((f'ref/{language}{family}/index.htm',f'{name} {label}'))
            links.append((f'ref/{grammar}/index.htm',f'{name} grammar'))
    for language,attribute,name in (('Heb','UBS_HEB_DATA','Hebrew'),('Grk','UBS_GNT_DATA','Greek')):
        if getattr(state,attribute,None) is not None:
            links.append((f'UBS/{language}/index.htm',f'UBS {name} dictionary'))
    if getattr(state,'TOBDData',{}).get('Articles'):
        links.append(('dct/index.htm','Bible dictionary'))
    table = getattr(state,'OETRefData',{}).get('word_tables',{}).get('OET-LV_DC_word_table.tsv')
    bible = getattr(state,'preloadedBibles',{}).get('OET-LV')
    selected = getattr(state,'booksToLoad',{}).get('OET-LV',())
    if table and bible and any(book in bible and ('ALL' in selected or book in selected)
                              for book in getattr(state,'OET_LV_DC_BOOK_LIST',())):
        links.append(('ref/DCWrd/index.htm','Additional-book Greek and Latin words'))
    if not links: return ''
    return '<p class="note">'+' · '.join(f'<a href="{prefix}{path}#Top">{label}</a>' for path,label in links)+'</p>'


def filterableIndex(level, contents, itemTag='a', *, outputFolder=None, stem='index'):
    """Keep complete static HTML available; search displays 200 entries at a time."""
    assert itemTag in ('a','li')
    dataAttribute = fallback = ''
    if outputFolder is not None and itemTag=='a' and contents.count('<a ')>10_000:
        # Avoid constructing hundreds of thousands of live browser elements.
        # The full static list remains an explicit, JavaScript-free fallback.
        items = re.findall(r'<a\b[^>]*>.*?</a>',contents,re.DOTALL)
        records = []
        for item in items:
            href = re.search(r'href="([^"]+)"',item)[1]
            text = unescape(re.sub(r'<[^>]+>','',item))+' '+unquote(unescape(href))
            records.append(dict(text=text,html=item))
        dataName,allName = f'{stem}.json',f'{stem}-all.htm'
        (outputFolder/dataName).write_text(json.dumps(records,ensure_ascii=False),encoding='utf-8')
        complete = (f'<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>Complete reference index</title><link rel="stylesheet" href="{"../"*level}BibleSite.css">'
            f'<link rel="stylesheet" href="{"../"*level}common.css"></head><body><h1 id="Top">Complete reference index</h1>'
            f'<p><a href="{stem}.htm#Top">Return to searchable index</a></p>{contents}</body></html>')
        (outputFolder/allName).write_text(complete,encoding='utf-8')
        dataAttribute = f' data-source="{dataName}"'
        fallback = f'<p><a href="{allName}#Top">Complete HTML list ({len(items):,} entries)</a></p>'
        contents = '<p>'+' · '.join(items[:200])+'</p>'
    return (f'<div class="referenceIndex" data-item-tag="{itemTag}"{dataAttribute}>'
            '<div class="referenceIndexControls" hidden>'
            '<label>Find an entry <input type="search" placeholder="Name, form, gloss or reference"></label> '
            '<button type="button" data-action="clear">Clear</button>'
            '<p class="referenceIndexCount" role="status" aria-live="polite"></p>'
            '<button type="button" data-action="previous">Previous</button> '
            '<button type="button" data-action="next">Next</button></div>'
            f'<div class="referenceIndexEntries">{contents}</div>{fallback}</div>'
            f'<script src="{"../"*level}referenceIndex.js" defer></script>')


def glossSummary(glosses, limit=3):
    """Brief source glosses are search aids, not exhaustive definitions."""
    if isinstance(glosses,str): glosses = glosses.split(';')
    texts = []
    for gloss in glosses:
        text = re.sub(r'<[^>]+>','',str(gloss)).replace('_',' ').replace('=',' ')
        text = ' '.join(text.split())
        if text and text not in texts: texts.append(text)
        if len(texts)>=limit: break
    return ' / '.join(texts)


def lemmaIndexLink(filename, label, glosses):
    summary = glossSummary(glosses)
    return (f'<a href="{quote(filename)}#Top">{escape(label)}'
            +(f' <small>— {escape(summary)}</small>' if summary else '')+'</a>')


def transliterateIndexLinks(html, transliterator):
    """Transliterate displayed source words without rewriting URLs or English glosses."""
    return re.sub(r'(<a\b[^>]*>)([^<]*)(.*?</a>)',
                  lambda match:match[1]+transliterator(match[2])+match[3],html,flags=re.DOTALL)


def ubsIndexEntry(entry):
    glosses = [gloss for base in entry.get('BaseForms') or () for meaning in base.get('LEXMeanings') or ()
               for sense in meaning.get('LEXSenses') or () if sense.get('LanguageCode')=='en'
               for gloss in sense.get('Glosses') or ()]
    return '<li>'+lemmaIndexLink(f'{entry["Lemma"]}.htm',entry['Lemma'],glosses)+'</li>'


def strongIndexEntry(code, lexicon):
    """Index every populated entry, including numbers between old sample points."""
    word = lexicon.getStrongsEntryField(code,'word')
    if not word: return None
    transliteration = word[3] if code.startswith('H') else word[1]
    return f'<li><a href="{code}.htm#Top">{code}: <b>{escape(word[0])}</b> ({escape(transliteration or "")})</a></li>'


def statisticsBookLink(level, BBB, label, state):
    """Link to an available OET chapter index; LV-only books retain LV context."""
    for version in ('OET','OET-LV','OET-RV'):
        books = state.booksToLoad.get(version,())
        bible = state.preloadedBibles.get('OET-RV' if version=='OET' else version)
        if ('ALL' in books or BBB in books) and bible is not None and BBB in bible:
            return f'<a href="{"../"*level}{version}/byC/{BBB}.htm#Top">{escape(label)}</a>'
    return escape(label)
