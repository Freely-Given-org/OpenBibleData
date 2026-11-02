#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Source-labelled word annotations for original-language search.

CHANGELOG:
    2026-11-01 Keep lemma, Strong's and morphology associations on the same word.
"""
import re


def strongKey(value):
    match = re.fullmatch(r'([HGA])0*(\d+)([a-z]*)',value)
    return f'{match[1]}{int(match[2])}{match[3]}' if match else value


def entryAnnotations(entries):
    result=[]
    for entry in entries:
        if entry.getMarker() not in ('v~','p~','d'):
            continue
        for extra in entry.getExtras() or ():
            if extra.getType() != 'ww':
                continue
            source=extra.getFullText()
            if '|' not in source:
                continue
            form,attributes=source.split('|',1)
            attrs=dict(re.findall(r'([\w-]+)="([^"]*)"',attributes))
            codes=[strongKey(code) for code in re.findall(r'[HGA]\d+[a-z]*',attrs.get('strong',''))]
            if attrs.get('lemma') or codes:
                result.append(dict(form=form,lemma=attrs.get('lemma',''),strong=codes,
                    morphology=attrs.get('x-morph',attrs.get('morph','')),source='USFM word attributes'))
    return result


def oetAnnotations(reference,state):
    from searchRecords import nativePoints
    data=getattr(state,'OETRefData',{})
    tables=data.get('word_tables',{})
    indexes=data.get('word_table_indexes',{})
    result=[]
    for filename,table in tables.items():
        if '_OT_' not in filename and '_NT_' not in filename:
            continue # Additional-book annotation formats have separate provenance.
        for book,chapter,verse,suffix in nativePoints(reference):
            key=f'{book}_{chapter}:{verse}{suffix or ""}'
            bounds=indexes.get(filename,{}).get(key)
            if not bounds:
                continue
            for number in range(bounds[0],bounds[1]+1):
                fields=table[number].split('\t')
                if '_NT_' in filename:
                    if not fields[7]:continue # Unused textual variant.
                    from lexicalLinks import normaliseStrongs
                    strong=normaliseStrongs(fields[8][:-1],'Grk') if fields[8] and fields[8]!='None' else None
                    result.append(dict(form=fields[1],lemma=fields[3],lemmaId=fields[2],
                        strong=[strong[1]] if strong else [],morphology=fields[10],
                        wordId=fields[0],source='OET-LV NT word table'))
                else:
                    from lexicalLinks import prepareLexicalAssociations,wordLexicalKeys
                    graph=prepareLexicalAssociations(state)
                    # The helper preserves Hebrew morpheme-slot associations.
                    for lemma,strong in wordLexicalKeys('Heb',fields,graph):
                        result.append(dict(form=fields[6],lemma=lemma,strong=[strongKey(strong[1])] if strong else [],
                            morphology=fields[5],wordId=fields[0],source='OET-LV OT word table'))
    return result
