#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Deterministic occurrence navigation from the native OET word tables.

CHANGELOG:
    2026-10-31 Index exact Strong's word occurrences and mapped context links.
    2026-10-31 Generate complete paginated lists and filterable form/gloss summaries.
    2026-10-31 Convert source gloss formatting before displaying or filtering occurrences.
    2026-11-02 Use shared OET-first controls with RV-only/LV-only alternatives.
    2026-11-02 Offer one section-first OET destination in its native numbering.
"""
from collections import defaultdict
from hashlib import sha256
import json
import re
from urllib.parse import quote,urlencode
from xml.sax.saxutils import escape
from openbibledata_rust import tidyHebrewLemmaGloss,formatNTSpansGlossWords

from settings import reorderBooksForOETVersions
from lexicalLinks import normaliseStrongs,prepareLexicalAssociations,wordLexicalKeys,lemmaFilename
from referencePassages import referenceSelectionLinks


def orderedReferences(references):
    books=reorderBooksForOETVersions(list({ref.split('_',1)[0] for ref in references}))
    order={book:number for number,book in enumerate(books)}
    def key(reference):
        book,chapter,verse=re.split('[_:]',reference)
        match=re.fullmatch(r'(\d+)([a-z]*)',verse)
        return order[book],int(chapter),int(match[1]),match[2]
    return sorted(set(references),key=key)


def prepareStrongOccurrences(state):
    if hasattr(state,'strongOccurrences'):return state.strongOccurrences
    index=defaultdict(lambda:defaultdict(list))
    for language,table in (('Heb','OET-LV_OT_word_table.tsv'),('Grk','OET-LV_NT_word_table.tsv')):
        for number,row in enumerate(getattr(state,'OETRefData',{}).get('word_tables',{}).get(table,())[1:],1):
            fields=row.split('\t')
            if not re.fullmatch(r'[A-Z0-9]{3}_\d+:\d+[a-z]*w\d+',fields[0]):continue
            if language=='Grk' and not fields[7]:continue # unused textual variant
            rawCodes=fields[4].split(',') if language=='Heb' else (fields[8][:-1],)
            codes={code[0] for raw in rawCodes if (code:=normaliseStrongs(raw,language))}
            reference=fields[0].split('w',1)[0]
            for code in codes:index[code][reference].append(number)
    state.strongOccurrences={code:dict(refs) for code,refs in index.items()}
    return state.strongOccurrences


def occurrenceContextLinks(level,reference,state):
    book,chapter,verse=re.split('[_:]',reference)
    source=state.BibleVersifications['OET-LV']
    match=re.fullmatch(r'(\d+)([a-z]*)',verse)
    references=((book,chapter,match[1],match[2] or None),)
    return referenceSelectionLinks(level,references,source,state,destinationLabel=True)


def _table(language,state):
    return state.OETRefData['word_tables'][f'OET-LV_{"OT" if language=="Heb" else "NT"}_word_table.tsv']


def _form(language,fields):
    return ' · '.join((fields[7],fields[5])) if language=='Heb' else ' · '.join((fields[1],fields[9],fields[10]))


def _gloss(language,fields):
    value=(fields[11] or fields[10] or fields[9] or fields[8]) if language=='Heb' else fields[5]
    # Reuse the word/lemma formatters, then take plain text for both labels and
    # filter keys. Escaping raw ESFM leaves e.g. \\untr in the generated page.
    value=tidyHebrewLemmaGloss(value) if language=='Heb' else formatNTSpansGlossWords(value)
    assert '\\' not in value, f'Unconverted {language} occurrence gloss at {fields[0]}: {value!r}'
    return ' '.join(re.sub(r'<[^>]+>','',value).replace('_',' ').replace('=',' ').split())


def prepareOccurrenceNavigation(state):
    """Prepare shared lists only for groups too large for the existing examples."""
    if hasattr(state,'occurrenceNavigation'):return state.occurrenceNavigation
    lexical=prepareLexicalAssociations(state)
    groups=defaultdict(list)
    for language in ('Heb','Grk'):
        table=getattr(state,'OETRefData',{}).get('word_tables',{}).get(f'OET-LV_{"OT" if language=="Heb" else "NT"}_word_table.tsv',())
        for number,row in enumerate(table[1:],1):
            fields=row.split('\t')
            if not re.fullmatch(r'[A-Z0-9]{3}_\d+:\d+[a-z]*w\d+',fields[0]):continue
            if language=='Grk' and not fields[7]:continue
            if state.TEST_MODE_FLAG and not state.ALL_TEST_REFERENCE_PAGES_FLAG and fields[0][:3] not in state.TEST_BOOK_LIST:continue
            groups[language,'form',_form(language,fields)].append(number)
            for lemma in {lemma for lemma,_code in wordLexicalKeys(language,fields,lexical)}:
                groups[language,'lemma',lemma].append(number)
            codes=fields[4].split(',') if language=='Heb' else (fields[8][:-1],)
            for code in {code[0] for raw in codes if (code:=normaliseStrongs(raw,language))}:
                groups[language,'strong',code].append(number)
    result={}
    for key,rows in groups.items():
        if len(rows)<=100:continue
        table=_table(key[0],state)
        references=orderedReferences({table[row].split('\t',1)[0].split('w')[0] for row in rows})
        order={ref:number for number,ref in enumerate(references)}
        rows.sort(key=lambda row:(order[table[row].split('\t',1)[0].split('w')[0]],row))
        stem=f'{key[0]}-{key[1]}-{sha256(json.dumps(key,ensure_ascii=False).encode()).hexdigest()[:20]}'
        result[key]=dict(stem=stem,rows=rows)
    assert len({group['stem'] for group in result.values()})==len(result)
    state.occurrenceNavigation=result
    return result


def occurrenceBrowseLink(level,language,kind,key,state,*,label=None,form=None,gloss=None):
    group=getattr(state,'occurrenceNavigation',{}).get((language,kind,key))
    if group is None:return ''
    query=urlencode({name:value for name,value in (('form',form),('gloss',gloss)) if value is not None})
    href=f'{"../"*level}ref/Occurrences/{group["stem"]}-1.htm'+('?' + query if query else '')+'#Top'
    label=label or f'Browse all {len(group["rows"]):,} occurrences'
    return f'<a href="{escape(href)}">{escape(label)}</a>'


def wordOccurrenceBrowseLink(level,language,fields,state):
    link=occurrenceBrowseLink(level,language,'form',_form(language,fields),state)
    return f'<p class="note">{link} by book or English gloss.</p>' if link else ''


def lemmaOccurrenceSummary(level,language,lemma,state):
    group=getattr(state,'occurrenceNavigation',{}).get((language,'lemma',lemma))
    if group is None:return ''
    forms=defaultdict(int);glosses=defaultdict(int)
    for row in group['rows']:
        fields=_table(language,state)[row].split('\t')
        forms[_form(language,fields)]+=1;glosses[_gloss(language,fields)]+=1
    formLinks=[occurrenceBrowseLink(level,language,'lemma',lemma,state,label=f'{form} ({count:,})',form=form) for form,count in sorted(forms.items(),key=lambda item:(-item[1],item[0]))]
    glossLinks=[occurrenceBrowseLink(level,language,'lemma',lemma,state,label=f'{gloss or "(no gloss)"} ({count:,})',gloss=gloss) for gloss,count in sorted(glosses.items(),key=lambda item:(-item[1],item[0]))]
    return '<p class="note">'+occurrenceBrowseLink(level,language,'lemma',lemma,state)+' by book, form or gloss.</p><details><summary>Matching occurrences by form and gloss</summary><p>Forms: '+'; '.join(formLinks)+'</p><p>English glosses: '+'; '.join(glossLinks)+'</p></details>'


def createOccurrencePages(level,folder,state):
    """Write at most 100 word rows per page, plus optional filters across the list."""
    from openbibledata_rust import getHebrewWordpageFilename,getGreekWordpageFilename
    from html import makeTop,makeBottom,checkHtml
    folder.mkdir(parents=True,exist_ok=True)
    groups=prepareOccurrenceNavigation(state)
    contextCache={};recordCache={};pageCount=0
    for (language,kind,key),group in groups.items():
        filename=getHebrewWordpageFilename if language=='Heb' else getGreekWordpageFilename
        table=_table(language,state)
        records=[]
        for row in group['rows']:
            cacheKey=language,row
            if cacheKey not in recordCache:
                fields=table[row].split('\t');ref=fields[0].split('w')[0]
                form,gloss=_form(language,fields),_gloss(language,fields)
                if ref not in contextCache:contextCache[ref]=occurrenceContextLinks(level,ref,state)
                word=fields[7] if language=='Heb' else fields[1]
                wordHref=f'{"../"*level}ref/{language}Wrd/{filename(row,state)}#Top'
                jump=f'<div class="referencePassage"><p class="referenceJump">Jump to {contextCache[ref]}</p></div>' if contextCache[ref] else ''
                html=(f'<li><b><a href="{wordHref}" title="{escape(fields[0])}">{escape(word)}</a></b>'
                      f' · {escape(form)} · {escape(gloss or "(no gloss)")}{jump}</li>')
                recordCache[cacheKey]=dict(book=ref[:3],ref=ref,form=form,gloss=gloss,html=html)
            records.append(recordCache[cacheKey])
        stem=group['stem'];total=len(records);pages=(total+99)//100
        (folder/f'{stem}.json').write_text(json.dumps(records,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
        title=f'{"Hebrew" if language=="Heb" else "Greek"} {kind}: {key}'
        back=f'../{language}Lem/{quote(lemmaFilename(language,key))}#Top' if kind=='lemma' else f'../{language}Strng/{key}.htm#Top' if kind=='strong' else f'../{language}Wrd/{filename(group["rows"][0],state)}#Top'
        books=dict.fromkeys(record['book'] for record in records)
        options=''.join(f'<option value="{book}">{book}</option>' for book in books)
        for page in range(pages):
            start=page*100
            previous=f'<a href="{stem}-{page}.htm#Top">Previous</a>' if page else ''
            following=f'<a href="{stem}-{page+2}.htm#Top">Next</a>' if page+1<pages else ''
            top=makeTop(level,None,'word',None,state).replace('__TITLE__',escape(title)).replace('__KEYWORDS__','Bible, occurrences')
            html=f'''{top}<h1 id="Top">{escape(title)} — recorded occurrences</h1>
<p><a href="{back}">Back to the reference entry</a></p>
<p>Native LV word occurrences in OET book order. OET links open the matching section with RV and LV side by side where available, otherwise the chapter or available edition. Each page lists at most 100 words.</p>
<div id="occurrenceBrowser" data-source="{stem}.json" data-offset="{start}">
<fieldset id="occurrenceFilters" hidden><legend>Find matching occurrences</legend>
<label>Book <select id="occurrenceBook"><option value="">All books</option>{options}</select></label>
<label>Word form <select id="occurrenceForm"><option value="">All forms</option></select></label>
<label>English gloss <select id="occurrenceGloss"><option value="">All glosses</option></select></label>
<label>Search <input id="occurrenceSearch" type="search"></label></fieldset>
<p id="occurrenceCount" aria-live="polite">{start+1:,}–{min(start+100,total):,} of {total:,} occurrences</p>
<p id="occurrencePages">{previous} · Page {page+1} of {pages} · {following}</p>
<ol id="occurrenceRows" start="{start+1}">{''.join(record['html'] for record in records[start:start+100])}</ol>
</div><script src="{'../'*level}referenceOccurrences.js" defer></script>{makeBottom(level,None,'word')}'''
            assert checkHtml(f'Occurrences {language} {kind} {key}',html)
            (folder/f'{stem}-{page+1}.htm').write_text(html,encoding='utf-8');pageCount+=1
    return pageCount
