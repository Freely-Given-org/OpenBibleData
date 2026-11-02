#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Readable UBS senses, source identifiers and bounded OET comparisons.

CHANGELOG:
    2026-10-30 Render UBS definitions, semantic domains and original-numbered citations.
    2026-10-31 Omit redundant note reference codes and link references absent from the prose.
    2026-11-02 Group sense previews before indented, section-first reading links.
"""
from collections import defaultdict
import logging
import re
from xml.sax.saxutils import escape

import bos_books_codes_py
from BibleOrgSys.Reference.BibleVersificationMappings import MappingStatus,get_default_mapping_engine
from lexicalLinks import prepareLexicalAssociations,lexicalResourceLinks,ubsEntryLink,ubsRelatedLinks,livenUBSLemmaReferences
from dictionaryPassages import dictionarySelectionLinks
from referencePassages import renderReferencePassageGroup,parseReferenceSelection


def parseUBSReference(value):
    """Decode only the published book/chapter/verse fields, not word positions.

    Both source dictionaries use original numbering (e.g. Mal 3:24 and
    2 Cor 13:13). Preserve extra position/annotation fields without using them
    to infer OET word alignment.
    """
    match = re.match(r'^(\d{3})(\d{3})(\d{3})\d{5}',value)
    if not match: raise ValueError(f'Unsupported UBS reference {value!r}')
    book,chapter,verse = (int(part) for part in match.groups())
    BBB = bos_books_codes_py.get_bos_book_code_from_reference_number(book)
    if not BBB: raise ValueError(f'Unknown UBS book number {book}')
    reference = (BBB,str(chapter),str(verse),None)
    if verse==0:
        # Source chapter pointers include references to book headings. Offer
        # chapter context, never substitute verse 1 as a lexical example.
        parseReferenceSelection(BBB,str(chapter),'org')
        return reference
    result = get_default_mapping_engine().convert('org','org',(reference,))
    if result.status!=MappingStatus.EXACT: raise ValueError(f'Invalid original-numbered reference {BBB} {chapter}:{verse}')
    return reference


def _chapterContexts(references):
    return tuple(dict.fromkeys(ref for reference in references
                for ref in (parseReferenceSelection(reference[0],reference[1],'org')
                            if reference[2]=='0' else (reference,))))


def ubsText(value,level,language,state,source):
    """Escape ordinary text; expand only recognised source tokens into links."""
    text = str(value)
    graph = prepareLexicalAssociations(state)
    if target:=graph['ubsIds'].get((language,source)):
        source=f'{language}/{graph["ubs"][target[0]]["Lemma"]}.htm#{target[1]}'
    tokenPattern = re.compile(r'\{(?:L:[^{}]*<SDB[HG]:[^{}]*>|[SD]:[^{}]*)\}')
    parts=[];start=0
    for match in tokenPattern.finditer(text):
        parts.append(escape(text[start:match.start()]))
        token=match[0];kind=token[1];payload=token[3:-1]
        if kind=='L':
            parts.append(livenUBSLemmaReferences(token,level,state))
        elif kind=='D':
            entries=graph['ubsMeaningsByCode'].get((language,payload),())
            parts.append(' / '.join(ubsEntryLink(level,key,graph,f'{payload}: {graph["ubs"][key]["Lemma"]}',anchor)
                                   for key,anchor in sorted(entries)) or escape(f'Semantic domain {payload}'))
        else:
            refs=[];unresolved=[]
            for raw in payload.split():
                try:refs.append(parseUBSReference(raw))
                except (ValueError,KeyError) as error:
                    logging.warning('UBS %s scripture token %r: %s',source,raw,error)
                    unresolved.append(escape(raw))
            refs=tuple(dict.fromkeys(refs))
            linked=dictionarySelectionLinks(level,_chapterContexts(refs),'org',state) if refs else ''
            readable='; '.join(f'{ref[0]} {ref[1]}'+(f':{ref[2]}' if ref[2]!='0' else ' (chapter context)') for ref in refs)
            parts.append('; '.join(part for part in (linked or readable,*unresolved) if part))
        start=match.end()
    parts.append(escape(text[start:]))
    return ''.join(parts).replace('\n','<br>')


def _noteValue(note,level,language,state,source):
    """Show note prose with any passage context not already cited within it."""
    content=note.get('Content') or ''
    def referenceKey(raw):
        # Different word-position/annotation fields can identify the same verse.
        try:return parseUBSReference(raw)
        except (ValueError,KeyError):return raw # ubsText reports and preserves invalid references.
    seen={referenceKey(raw) for payload in re.findall(r'\{S:([^{}]*)\}',content) for raw in payload.split()}
    additional=[]
    for raw in note.get('References') or ():
        key=referenceKey(raw)
        if key not in seen:
            # Metadata can append a note caller such as {N:006}; it is not
            # part of the scripture token passed to the text renderer.
            additional.append(raw[:14] if isinstance(key,tuple) else raw);seen.add(key)
    text=ubsText(content,level,language,state,source)
    if additional:
        links=ubsText('{S:'+' '.join(additional)+'}',level,language,state,source)
        text='<b>Passage'+('s' if len(additional)>1 else '')+':</b> '+links+('<br>'+text if text else '')
    return text


def _value(value,level,language,state,source):
    if isinstance(value,list):return '; '.join(part for item in value if (part:=_value(item,level,language,state,source)))
    if isinstance(value,dict):
        # Localised source text is not a nested Python dictionary for readers.
        if value.get('LanguageCode') not in (None,'en'):return ''
        if 'Content' in value and ('References' in value or 'Caller' in value):
            return _noteValue(value,level,language,state,source)
        if value.get('Domain'):
            return escape(value['Domain'])+(f' ({escape(value["DomainCode"])})' if value.get('DomainCode') else '')
        return '; '.join(_value(item,level,language,state,source) for key,item in value.items()
                        if item and key not in ('LanguageCode','LastEdited','LastEditedBy','BaseFormIndex'))
    return ubsText(value,level,language,state,source)


def _paragraph(label,value,level,language,state,source):
    if not value:return ''
    content=_value(value,level,language,state,source)
    return f'<p><b>{label}:</b> {content}</p>' if content else ''


def ubsSensePassages(level,meaning,language,state,source):
    graph=prepareLexicalAssociations(state)
    sourceLabel=source
    if target:=graph['ubsIds'].get((language,source)):
        sourceLabel=f'{language}/{graph["ubs"][target[0]]["Lemma"]}.htm#{target[1]}'
    references=[];unresolved=[]
    for raw in meaning.get('LEXReferences') or ():
        try:references.append(parseUBSReference(raw))
        except (ValueError,KeyError) as error:
            logging.warning('UBS %s LEXReferences %r: %s',sourceLabel,raw,error)
            unresolved.append(raw)
    references=tuple(dict.fromkeys(references))
    selections=[(f'{ref[0]} {ref[1]}'+(' (chapter context)' if ref[2]=='0' else f':{ref[2]}'),
                 _chapterContexts((ref,))) for ref in references[:2]]
    html=renderReferencePassageGroup(level,selections,'org',state,instancePrefix=f'ubs{source}_')
    if len(references)>2:
        books=defaultdict(list)
        for reference in references:books[reference[0]].append(reference)
        html+=f'<details><summary>All {len(references):,} recorded passages for this sense</summary>'
        for BBB,refs in books.items():
            links=dictionarySelectionLinks(level,_chapterContexts(refs),'org',state)
            if not links:links=escape('; '.join(f'{r[1]}:{r[2]}' for r in refs))
            html+=f'<p><b>{BBB}</b>: {links}</p>'
        html+='</details>'
    if unresolved:
        html+='<details><summary>Unmapped source references</summary><p>'+escape('; '.join(unresolved))+'</p></details>'
    return html


def renderUBSEntry(level,language,entry,state):
    main=entry['MainId']
    html=f'<h2>{escape(entry["Lemma"])}</h2>'+lexicalResourceLinks(level,language,state,ubsId=main)
    for key,label in (('AlternateLemmas','Other spellings'),('Notes','Notes'),('Authors','Authors'),
                      ('Contributors','Contributors'),('ContributorNote','Contributor note'),('MainLinks','Further resources')):
        html+=_paragraph(label,entry.get(key),level,language,state,main)
    for baseNumber,base in enumerate(entry.get('BaseForms') or (),1):
        baseId=base.get('BaseFormID',f'{main}_{baseNumber}')
        html+=f'<div id="base{baseId}"><h3>Form {baseNumber}</h3>'
        for key,label in (('PartsOfSpeech','Part of speech'),('Inflections','Inflections'),('Constructs','Constructions'),
                          ('Etymologies','Etymology'),('RelatedNames','Related names'),('MeaningsOfName','Name meanings'),
                          ('CrossReferences','Cross-references'),('BaseFormLinks','Further resources')):
            html+=_paragraph(label,base.get(key),level,language,state,baseId)
        if related:=base.get('RelatedLemmas'):
            html+=f'<p><b>Related lemmas:</b> {ubsRelatedLinks(level,language,related,state)}</p>'
        for number,meaning in enumerate(base.get('LEXMeanings') or (),1):
            senseId=meaning.get('LEXID',f'{baseId}_{number}')
            senses=[sense for sense in meaning.get('LEXSenses') or () if sense.get('LanguageCode') in (None,'en')]
            glosses=list(dict.fromkeys(gloss for sense in senses for gloss in sense.get('Glosses') or ()))
            html+=f'<div id="sense{senseId}"><h4>Sense {number}'+(': '+escape(', '.join(glosses)) if glosses else '')+'</h4>'
            for key,label in (('LEXEntryCode','Semantic entry'),('LEXDomains','Semantic domains'),('LEXSubDomains','Subdomains'),('LEXCoreDomains','Core domains')):
                html+=_paragraph(label,meaning.get(key),level,language,state,senseId)
            for sense in senses:
                shown=set()
                for key,label in (('DefinitionShort','Definition'),('DefinitionLong','Further definition'),('Comments','Notes')):
                    if (text:=sense.get(key)) and text not in shown:
                        html+=_paragraph(label,text,level,language,state,senseId);shown.add(text)
            for key,label in (('LEXForms','Forms'),('LEXValencies','Valencies'),('LEXCollocations','Collocations'),
                              ('LEXIllustrations','Illustrations'),('LEXCrossReferences','Cross-references'),
                              ('LEXLinks','Further resources'),('LEXImages','Images'),('LEXVideos','Videos'),
                              ('LEXCoordinates','Coordinates'),('CONMeanings','Contextual meanings')):
                html+=_paragraph(label,meaning.get(key),level,language,state,senseId)
            for key,label in (('LEXSynonyms','Synonyms'),('LEXAntonyms','Antonyms')):
                if values:=meaning.get(key):html+=f'<p><b>{label}:</b> {ubsRelatedLinks(level,language,values,state)}</p>'
            html+=ubsSensePassages(level,meaning,language,state,senseId)+'</div>'
        html+='</div>'
    return html
