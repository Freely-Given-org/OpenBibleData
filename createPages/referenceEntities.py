#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Verified person and place associations, shared by reference page builders.

CHANGELOG:
    2026-10-30 Resolve relationship IDs and lookup slugs and add reciprocal links.
    2026-10-31 Link kingdom articles to explicitly identified kings, prophets and places.
    2026-11-02 Index traditional and OET-RV names from the names table without merging identities.
    2026-11-02 Group each entry's indented passage previews ahead of its jump links.
"""
from collections import Counter, defaultdict
from csv import DictReader
import json
import logging
from pathlib import Path
import re
from urllib.parse import quote
from xml.sax.saxutils import escape

from navigation import bookNavigationOrder
from referencePassages import parseReferenceSelection, renderReferencePassage, renderReferencePassageGroup, referenceCitationLink


OET_RV_NAMES_TABLE_PATH = Path(__file__).resolve().parents[2]/'OpenEnglishTranslation--OET/translatedTexts/ReadersVersion/OET-RV_names_table.tsv'


def _nameKey(name):
    """Ignore typographic spelling differences when looking up a whole name."""
    return re.sub(r"[\s\-‐‑’ʼ']",'',name).casefold()


def loadOETRVNameAliases(state):
    """Read once per build, retaining every RV spelling for repeated table names."""
    if hasattr(state,'oetRVNameAliases'): return state.oetRVNameAliases
    aliases = defaultdict(list)
    with OET_RV_NAMES_TABLE_PATH.open(encoding='utf-8-sig',newline='') as source:
        rows = DictReader(source,delimiter='\t')
        if not {'TraditionalName','RVName'}.issubset(rows.fieldnames or ()):
            raise ValueError(f'{OET_RV_NAMES_TABLE_PATH}: expected TraditionalName and RVName columns')
        for row in rows:
            traditional,rv = ((row.get(column) or '').strip() for column in ('TraditionalName','RVName'))
            if not traditional or not rv:
                raise ValueError(f'{OET_RV_NAMES_TABLE_PATH}:{rows.line_num}: missing TraditionalName or RVName')
            spellings = aliases[_nameKey(traditional)]
            if rv not in spellings: spellings.append(rv)
    state.oetRVNameAliases = {key:tuple(names) for key,names in aliases.items()}
    return state.oetRVNameAliases


def oetRVNameVariants(name, aliases):
    """Match a name, preserving geographic prefixes and possessive endings."""
    if variants:=aliases.get(_nameKey(name)): return variants
    # The place source calls e.g. Lebanon "Mount Lebanon". Keep that context
    # instead of turning a mountain into a separate person or place identity.
    match = re.fullmatch(r'((?:mount|mountain|brook|river|valley|hill|sea|gate)(?: of(?: the)?)? )(.+)',name,re.IGNORECASE)
    if match:
        return tuple(match[1]+variant for variant in oetRVNameVariants(match[2],aliases))
    if name.endswith(("'s",'’s')):
        return tuple(variant+name[-2:] for variant in oetRVNameVariants(name[:-2],aliases))
    return ()


def entityNames(entry, aliases):
    """Use names explicitly attached to this record, not names inside qualifiers."""
    title = entry['displayTitle']
    base = title.partition(' (')[0]
    sourceNames = [base]
    sourceNames.extend(entry.get(field) or '' for field in ('name','surname','kjvName','esvName'))
    sourceNames.extend((entry.get('alsoCalled') or '').split(','))
    names = [title]
    for sourceName in dict.fromkeys(name.strip() for name in sourceNames if name.strip()):
        if sourceName != base: names.append(sourceName)
        names.extend(oetRVNameVariants(sourceName,aliases))
    return tuple(dict.fromkeys(names))


def entityIndexLinks(keys, entities, state):
    """Alphabetise aliases, with existing destinations and namesake distinctions."""
    aliases = loadOETRVNameAliases(state)
    entries = []
    for key in keys:
        entry = entities['records'][key]
        title = entry['displayTitle']
        suffix = ''
        if entities['nameCounts'][title]>1:
            references = entry.get('verses',())
            suffix = f' ({references[0].replace("_"," ") if references else key[1:]})'
        href = f'{quote(key[1:],safe="")}.htm#Top'
        for name in entityNames(entry,aliases):
            label = escape(name)
            if name != title: label += f' <small>({escape(title)})</small>'
            label += escape(suffix)
            entries.append((name.casefold(),key,f'<a href="{href}">{label}</a>'))
    return [link for _name,_key,link in sorted(entries)]


# Explicit cross-resource identities. Do not match ambiguous names automatically.
ENTITY_DICTIONARY_ARTICLES = {
    'PMoses':'Moses','PAbraham':'Abraham','PJesus':'Jesus','PDavid':'David',
    'LJerusalem':'Jerusalem','LEgypt':'Egypt',
}
KINGDOM_BACKGROUND_ENTITIES = ('PJacob','LEgypt','PSaul','PDavid','PSolomon','LJerusalem','LSamaria')
KINGDOM_ENTITIES = {
    'PromisedLand':('PMoses','PJacob','LEgypt'),
    'FullKingdom':('PSamuel','PGad2','PNathan','PAhijah','PJoseph'),
    'NorthernKingdom':('PElijah','PElisha','PJonah','PAmos','PHosea','LSamaria'),
    'SouthernKingdom':('PElijah','PIsaiah','PMicah3','PZephaniah2','PObadiah12','PNahum','PJeremiah','PJoel14','PHabakkuk'),
    'BothKingdoms':('PIsaiah','LJerusalem','LSamaria'),
}
for _kingdom in ('FullKingdom','NorthernKingdom','SouthernKingdom','BothKingdoms'):
    KINGDOM_ENTITIES[_kingdom] = tuple(dict.fromkeys(KINGDOM_BACKGROUND_ENTITIES+KINGDOM_ENTITIES[_kingdom]))

# Reviewed identities in this specific prose, not a general name matcher. Gad2 is
# David's prophet, for example; Gad is Jacob's son. The same applies to the
# numbered Micah, Zephaniah, Obadiah and Joel records.
KINGDOM_MENTIONS = {
    'Mosheh (Moses)':'PMoses','Yakov/Yisrael (Jacob/Israel)':'PJacob',
    'Yakov (Jacob)':'PJacob','Yakov':'PJacob','Egypt':'LEgypt',
    'Shaul (Saul)':'PSaul','Shaul':'PSaul','David':'PDavid',
    'Shelomoh (Solomon)':'PSolomon','Shelomoh':'PSolomon',
    "Yosef's (Joseph's)":'PJoseph','Gad':'PGad2','Natan (Nathan)':'PNathan','Ahiyah (Ahijah)':'PAhijah',
    'Eliyyyah (Elijah)':'PElijah','Elisha':'PElisha','Yonah (Jonah)':'PJonah','Amos':'PAmos','Hoshea (Hosea)':'PHosea',
    'Isaiah':'PIsaiah','Mikah (Micah)':'PMicah3','Zefanyah (Zephaniah)':'PZephaniah2',
    'Ovadyah (Obadiah)':'PObadiah12','Nahum':'PNahum','Yeremyah (Jeremiah)':'PJeremiah',
    'Yoel (Joel)':'PJoel14','Habakkuk':'PHabakkuk',
    'Yerushalem':'LJerusalem','Yerushalim':'LJerusalem','Samaria':'LSamaria',
}


def kingdomArticleLinks(html, level, entities):
    """Link reviewed mentions in text nodes, retaining existing scripture links."""
    pattern = re.compile(r'(?<!\w)(?:'+'|'.join(re.escape(name) for name in sorted(KINGDOM_MENTIONS,key=len,reverse=True))+r')(?!\w)')
    def replace(match):
        key = KINGDOM_MENTIONS[match[0]]
        if key not in entities['records']: return match[0]
        link = entityLink(key,level,entities)
        return link[:link.index('>')+1]+escape(match[0])+'</a>'
    parts = re.split(r'(<[^>]+>)',html)
    inLink = False
    for index,part in enumerate(parts):
        if part.startswith('<'):
            if re.match(r'<a\b',part): inLink = True
            elif part == '</a>': inLink = False
        elif not inLink: parts[index] = pattern.sub(replace,part)
    return ''.join(parts)


def loadReferenceEntities(folder, state):
    """Read each source once; names are display text, never inferred identities."""
    folder = Path(folder)
    cached = getattr(state,'referenceEntities',None)
    if cached and cached['folder'] == folder: return cached
    records = {}
    for prefix,filename in (('P','normalised_People.json'),('L','normalised_Places.json')):
        with (folder/filename).open(encoding='utf-8') as source:
            records.update((key,entry) for key,entry in json.load(source).items() if key.startswith(prefix))
    lookups = defaultdict(set)
    for key,entry in records.items():
        for field in ('TBDPersonLookup','TBDPlaceLookup'):
            if value:=entry.get(field): lookups[value].add(key)
    relationships = defaultdict(lambda:defaultdict(set))
    def resolve(source,value):
        if value in records: return value
        matches = lookups.get(value,())
        if len(matches)==1: return next(iter(matches))
        if value: logging.warning('Entity %s: unresolved or ambiguous relationship identifier %r',source,value)
        return None
    def relate(source,value,label,inverse):
        target = resolve(source,value)
        if target and target != source:
            relationships[source][label].add(target)
            relationships[target][inverse].add(source)
    for key,entry in records.items():
        if key.startswith('P'):
            for field,label in (('mother','Mother'),('father','Father')):
                if value:=entry.get(field): relate(key,value,label,'Children')
            for field,label,inverse in (('partners','Partners','Partners'),('children','Children','Parents'),
                    ('siblings','Siblings','Siblings'),('halfSiblingsSameMother','Half-siblings','Half-siblings'),
                    ('halfSiblingsSameFather','Half-siblings','Half-siblings')):
                for value in entry.get(field,()): relate(key,value,label,inverse)
            for field,label,inverse in (('birthPlace','Born in','People born here'),('deathPlace','Died in','People who died here')):
                if value:=entry.get(field): relate(key,value,label,inverse)
        else:
            for field,label,inverse in (('peopleBorn','People born here','Born in'),('peopleDied','People who died here','Died in')):
                for value in entry.get(field,()): relate(key,value,label,inverse)
            for value in (entry.get('hasBeenHere') or '').split(','):
                if value.strip(): relate(key,value.strip(),'People recorded here','Places recorded for this person')
    for groups in relationships.values():
        # A directly identified father/mother already conveys the parent link.
        if 'Parents' in groups: groups['Parents'] -= groups.get('Father',set()) | groups.get('Mother',set())
    result = dict(folder=folder,records=records,
                  relationships={key:{label:tuple(sorted(targets)) for label,targets in groups.items() if targets}
                                 for key,groups in relationships.items()},
                  nameCounts=Counter(entry['displayTitle'] for entry in records.values()))
    state.referenceEntities = result
    return result


def entityLink(key, level, entities):
    entry = entities['records'][key]
    name = entry['displayTitle']
    if entities['nameCounts'][name]>1:
        refs = entry.get('verses',())
        if refs: name += f' ({refs[0].replace("_"," ")})'
    folder = 'Per' if key.startswith('P') else 'Loc'
    return f'<a href="{"../"*level}ref/{folder}/{quote(key[1:],safe="")}.htm#Top">{escape(name)}</a>'


def entityRelationships(key, level, entities):
    groups = entities['relationships'].get(key,{})
    if not groups: return ''
    paragraphs = [f'<p class="note"><b>{label}:</b> '+', '.join(entityLink(target,level,entities) for target in targets)+'</p>'
                  for label,targets in groups.items()]
    return '<h2>People and places</h2>'+''.join(paragraphs)


def prepareEntityWordIndex(entities,state):
    """Reverse existing tags once, retaining the original row identity and numbering."""
    if 'taggedWords' in entities: return
    tagged,passages = defaultdict(list),defaultdict(set)
    unknown = set()
    for language in ('OT','NT'):
        table = getattr(state,'OETRefData',{}).get('word_tables',{}).get(f'OET-LV_{language}_word_table.tsv',())
        for number,row in enumerate(table[1:],1):
            fields = row.split('\t')
            if language=='NT' and not fields[7]: continue
            reference = fields[0].split('w')[0]
            for tag in set(fields[-1].split(';')):
                if not tag.startswith(('P','L')): continue
                if tag not in entities['records']:
                    unknown.add(tag)
                    continue
                tagged[tag].append((language,number,reference))
                passages[reference].add(tag)
    if unknown: logging.warning('Word-table entity tags lack records: %s',', '.join(sorted(unknown)))
    entities['taggedWords'] = dict(tagged)
    entities['passageEntities'] = {reference:tuple(sorted(keys)) for reference,keys in passages.items()}


def _orderedSelections(citations, sourceSystem, sourcePage):
    selections = []
    for citation in dict.fromkeys(citations):
        try:
            BBB,selection = citation.split('_',1)
            BBB = {'EZK':'EZE'}.get(BBB,BBB) # Theographic retains this USFM spelling.
            references = parseReferenceSelection(BBB,selection,sourceSystem)
        except (ValueError,KeyError) as error:
            logging.warning('Entity %s: cannot link citation %r: %s',sourcePage,citation,error)
            selections.append((citation,()))
            continue
        selections.append((citation,references))
    order = {BBB:n for n,BBB in enumerate(bookNavigationOrder({refs[0][0] for _,refs in selections if refs},'OET'))}
    return sorted(selections,key=lambda item:((order[item[1][0][0]],int(item[1][0][1]),int(item[1][0][2]))
                                               if item[1] else (len(order),0,0)))


def entityPassages(key, level, entities, state, selected=()):
    """A few previews, with complete recorded lists available by book."""
    parts = []
    if selected:
        parts.append('<h2>Selected passages</h2>')
        parts.append(selectedPassageControls(selected,level,state,'selected'))
    recorded = _orderedSelections(entities['records'][key].get('verses',()),'eng',key)
    if recorded:
        parts.append(f'<h2>Recorded scripture occurrences ({len(recorded):,})</h2>'
                     '<p class="note">References recorded in the source data; this is not an exhaustive list of mentions.</p>')
        parts.append(renderReferencePassageGroup(level,((citation.replace('_',' '),refs) for citation,refs in recorded[:3]),
                     'eng',state,instancePrefix='recorded'))
        groups = defaultdict(list)
        for n,(citation,refs) in enumerate(recorded):
            groups[refs[0][0] if refs else 'Unresolved'].append(renderReferencePassage(level,refs,'eng',state,
                instanceId=f'occurrence{n}',label=citation.replace('_',' '),preview=False)
                if refs else f'<p class="note">{escape(citation)} (reference unavailable)</p>')
        for BBB,items in groups.items():
            parts.append(f'<details><summary>{BBB}: all {len(items):,} recorded references</summary>{"".join(items)}</details>')
    return ''.join(parts)


def selectedPassageControls(citations,level,state,instancePrefix):
    return renderReferencePassageGroup(level,
        ((citation.replace('_',' '),refs) for citation,refs in _orderedSelections(citations,'eng',instancePrefix)),
        'eng',state,instancePrefix=instancePrefix)


def entityTaggedWords(key, level, entities, state):
    from openbibledata_rust import getGreekWordpageFilename, getHebrewWordpageFilename
    prepareEntityWordIndex(entities,state)
    byBook = defaultdict(lambda:defaultdict(list))
    for language,number,reference in entities['taggedWords'].get(key,()):
        BBB,CV = reference.split('_')
        if state.TEST_MODE_FLAG and not state.ALL_TEST_REFERENCE_PAGES_FLAG and BBB not in state.TEST_BOOK_LIST: continue
        greek = language=='NT'
        filename = (getGreekWordpageFilename if greek else getHebrewWordpageFilename)(number,state)
        fields = state.OETRefData['word_tables'][f'OET-LV_{language}_word_table.tsv'][number].split('\t')
        word = fields[1] if greek else fields[6]
        byBook[BBB][CV].append(f'<a href="{"../"*level}ref/{"GrkWrd" if greek else "HebWrd"}/{filename}#Top">{escape(word)}</a>')
    if not byBook: return ''
    parts = ['<h2>Words tagged with this person or place</h2><p class="note">These links follow the source-word tags and may include pronouns. Tagging is not exhaustive.</p>']
    for BBB in bookNavigationOrder(byBook,'OET'):
        entries = []
        for CV,links in sorted(byBook[BBB].items(),key=lambda item:(int(item[0].split(':')[0]),int(re.match(r'\d+',item[0].split(':')[1])[0]),item[0])):
            C,V = CV.split(':')
            books = state.booksToLoad.get('OET',())
            passage = (referenceCitationLink(level,(BBB,C,V),state.BibleVersifications['OET-LV'],'OET',f'{BBB} {CV}',state)
                       if 'ALL' in books or BBB in books else f'{BBB} {CV}')
            entries.append(f'<p class="note">{passage}: {" · ".join(links)}</p>')
        parts.append(f'<details><summary>{BBB}: {len(entries):,} tagged passages</summary>{"".join(entries)}</details>')
    return ''.join(parts)


def entityRelatedResources(key,level,state):
    links = []
    article = ENTITY_DICTIONARY_ARTICLES.get(key)
    if article in getattr(state,'TOBDData',{}).get('Articles',{}):
        links.append(f'<a href="{"../"*level}dct/{quote(article,safe="")}.htm#Top">Tyndale dictionary</a>')
    for kingdom,keys in KINGDOM_ENTITIES.items():
        if key in keys:
            label = re.sub(r'([a-z])([A-Z])',r'\1 \2',kingdom)
            links.append(f'<a href="{"../"*level}ref/Kingdoms/{kingdom}.htm#Top">{label}</a>')
    return '<h2>Related reference material</h2><p class="note">'+' · '.join(links)+'</p>' if links else ''
