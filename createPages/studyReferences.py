#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Connect explicit topic selections and tagged people/places to study passages.

CHANGELOG:
    2026-10-30 Reverse source associations without inferring topics from English words.
"""
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape
import logging

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Reference.BibleVersificationMappings import MappingStatus,VersificationMappingError,get_default_mapping_engine
from referenceEntities import loadReferenceEntities,prepareEntityWordIndex,entityLink,ENTITY_DICTIONARY_ARTICLES
from referencePassages import parseReferenceSelection
from oetWords import mappedWordRows,wordTableName

ENTITY_FOLDER=Path(__file__).resolve().parents[2]/'Bible_speaker_identification/outsideSources/TheographicBibleData/derivedFiles'


def topicFilename(topic):
    words=[word.title() for word in topic.replace(', ',' ').replace('/','⁄').split()]
    return BibleOrgSysGlobals.makeSafeFilename(''.join(words)+'.htm')


def prepareTopicAssociations(state,topicTable=None):
    if hasattr(state,'topicAssociations'):return state.topicAssociations
    if topicTable is None:
        from createTopicPages import TOPIC_TABLE
        topicTable=TOPIC_TABLE
    graph=dict(topics={},passages=defaultdict(set),lemmas=defaultdict(set),selections=defaultdict(list))
    source=getattr(state,'BibleVersifications',{}).get('OET-RV','OET-RV')
    canonical=getattr(state,'navigationVersification','eng')
    for topic,items in topicTable.items():
        filename=topicFilename(topic);graph['topics'][filename]=topic
        for item in items:
            if item.startswith('H3 '):continue
            if '/' in item:
                graph['lemmas'][item].add(filename);continue
            BBB,selection=item.split('_',1)
            try:references=parseReferenceSelection(BBB,selection,source)
            except (ValueError,KeyError) as error:
                logging.warning('Topic %s citation %s: %s',filename,item,error);continue
            graph['selections'][filename].append(references)
            mapping=get_default_mapping_engine().convert_passage(source,canonical,references)
            if mapping.status!=MappingStatus.EXACT:
                logging.warning('Topic %s citation %s: cannot reverse %s mapping',filename,item,mapping.status.value);continue
            for ref in mapping.references:graph['passages'][ref].add(filename)
    for key,value in tuple(graph.items()):
        if isinstance(value,defaultdict):graph[key]=dict(value)
    state.topicAssociations=graph
    return graph


def prepareStudyAssociations(state,entityFolder=ENTITY_FOLDER):
    if hasattr(state,'studyAssociations'):return state.studyAssociations
    topics=prepareTopicAssociations(state)
    entities=loadReferenceEntities(entityFolder,state)
    prepareEntityWordIndex(entities,state)
    wordEntities=defaultdict(set)
    for key,occurrences in entities['taggedWords'].items():
        for language,row,_reference in occurrences:
            wordEntities[(f'OET-LV_{language}_word_table.tsv',row)].add(key)
    state.studyAssociations=dict(topics=topics,entities=entities,wordEntities=dict(wordEntities))
    return state.studyAssociations


def _topicLinks(level,filenames,topics):
    return ' · '.join(f'<a href="{"../"*level}tpc/{quote(filename)}#Top">{escape(topics["topics"][filename])}</a>'
                      for filename in sorted(filenames,key=lambda name:topics['topics'][name]))


def lemmaTopics(level,language,lemma,state):
    from lexicalLinks import lemmaFilename
    topics=prepareTopicAssociations(state)
    filename=lemmaFilename(language,lemma).removesuffix('.htm')
    return _topicLinks(level,topics['lemmas'].get(f'{language}Lem/{filename}',()),topics)


def _taggedEntities(references,sourceSystem,state,graph):
    if not graph['wordEntities']:return set()
    try:rows=mappedWordRows(sourceSystem,references,state)
    except (KeyError,VersificationMappingError):return set()
    table=wordTableName(references[0][0])
    return set().union(*(graph['wordEntities'].get((table,row),()) for row in rows))


def _entityResources(level,keys,state,graph):
    paragraphs=[]
    for prefix,label in (('P','People tagged in the matching LV passage'),('L','Places tagged in the matching LV passage')):
        links=[entityLink(key,level,graph['entities']) for key in sorted(keys) if key.startswith(prefix)]
        if links:paragraphs.append(f'<p class="note">{label}: '+ ' · '.join(links)+'</p>')
    articles=getattr(state,'TOBDData',{}).get('Articles',{})
    dictionaries=sorted({article for key in keys if (article:=ENTITY_DICTIONARY_ARTICLES.get(key)) and article in articles})
    if dictionaries:
        links=[f'<a href="{"../"*level}dct/{quote(article)}.htm#Top">{escape(article)}</a>' for article in dictionaries]
        paragraphs.append('<p class="note">Dictionary: '+' · '.join(links)+'</p>')
    return ''.join(paragraphs)


def passageReferenceMaterial(level,reference,sourceSystem,state):
    if int(reference[1])<1:return ''
    if 'OET-LV' not in getattr(state,'preloadedBibles',{}):return ''
    graph=prepareStudyAssociations(state)
    references=(tuple(reference),)
    keys=_taggedEntities(references,sourceSystem,state,graph)
    html=_entityResources(level,keys,state,graph)
    mapping=get_default_mapping_engine().convert_passage(sourceSystem,state.navigationVersification,references)
    if mapping.status==MappingStatus.EXACT:
        topics=set().union(*(graph['topics']['passages'].get(ref,()) for ref in mapping.references))
        if topics:html+='<p class="note">Used in these topics: '+_topicLinks(level,topics,graph['topics'])+'</p>'
    return '<details><summary>Reference material for this passage</summary>'+html+'</details>' if html else ''


def topicReferenceMaterial(level,topic,state):
    graph=prepareStudyAssociations(state)
    keys=set()
    for references in graph['topics']['selections'].get(topicFilename(topic),()):
        keys.update(_taggedEntities(references,state.BibleVersifications['OET-RV'],state,graph))
    html=_entityResources(level,keys,state,graph)
    return '<details><summary>People, places and dictionary entries for these passages</summary>'+html+'</details>' if html else ''
