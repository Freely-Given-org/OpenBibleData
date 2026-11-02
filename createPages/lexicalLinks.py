#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Source-based associations between OET lemmas, Strong's entries and UBS.

CHANGELOG:
    2026-10-30 Build lexical associations independently of page-generation order.
    2026-11-02 Identify UBS links explicitly as dictionary entries.
"""
from collections import defaultdict
from pathlib import Path
import re
import unicodedata
from functools import cache
from urllib.parse import quote
from xml.sax.saxutils import escape

from bible_transliterations import transliterate_Hebrew


def normaliseStrongs(value, language='Heb'):
    """Return (page code, sense code), retaining suffixes and Aramaic identity."""
    match = re.fullmatch(r'([HGA]?)(\d+)(?:\s*([a-z]))?\+?',value.strip())
    if not match: return None
    prefix,number,suffix = match.groups()
    prefix = prefix or ('G' if language=='Grk' else 'H')
    number = int(number)
    if not 0<number<=(5624 if prefix=='G' else 8674): return None
    page = ('G' if prefix=='G' else 'H')+str(number)
    return page,prefix+str(number)+(suffix or '')


def lemmaFilename(language,lemma):
    if language=='Grk': return f'{lemma}.htm'
    return f'{"pitggām" if lemma=="פִּתְגָּם" else transliterate_Hebrew(lemma)}.htm'


def _hebrewLemmaList(state):
    data = getattr(state,'OETRefData',{})
    if 'OTHebLemmaList' in data: return data['OTHebLemmaList']
    bible = getattr(state,'preloadedBibles',{}).get('OET-LV')
    folder = getattr(bible,'OTsourceFolder',None)
    if folder is None: return []
    path = Path(folder)/'OET-LV_OT_lemma_table.tsv'
    return [row.split('\t')[0] for row in path.read_text(encoding='utf-8-sig').splitlines()]


def wordLexicalKeys(language, fields, graph):
    """Keep Hebrew morpheme slots aligned; never take a Cartesian product."""
    if language=='Grk':
        strong = normaliseStrongs(fields[8][:-1],'Grk') if fields[8] and fields[8]!='None' else None
        return [(fields[2],strong)] if fields[2] else []
    lemmaSlots = fields[3].split(',')
    strongSlots = fields[4].split(',')
    result = []
    for index,lemmaNumber in enumerate(lemmaSlots):
        if not lemmaNumber.isdigit() or not 0<int(lemmaNumber)<len(graph['hebrewLemmas']): continue
        lemma = graph['hebrewLemmas'][int(lemmaNumber)]
        strong = normaliseStrongs(strongSlots[index]) if len(lemmaSlots)==len(strongSlots) else None
        if strong and fields[1].startswith('A'):
            strong = strong[0],'A'+strong[1][1:]
        result.append((lemma,strong))
    return result


def prepareLexicalAssociations(state):
    """Prepare once before dictionary, topic, word and lemma writers run.

    A shared Strong's identifier is an association, not proof of identical
    meaning. All UBS alternatives remain separate, including suffixes.
    """
    if hasattr(state,'lexicalAssociations'): return state.lexicalAssociations
    graph = dict(hebrewLemmas=_hebrewLemmaList(state),lemmaCodes=defaultdict(set),
                 strongLemmas=defaultdict(set),lemmaLabels={},availableLemmas=set(),availableStrongs=set(),
                 ubs={},ubsByCode=defaultdict(set),ubsByStrong=defaultdict(set),ubsByLemma=defaultdict(set),ubsIds={},
                 ubsMeaningsByCode=defaultdict(set))
    filtered = state.TEST_MODE_FLAG and not state.ALL_TEST_REFERENCE_PAGES_FLAG
    for language,tableName in (('Heb','OET-LV_OT_word_table.tsv'),('Grk','OET-LV_NT_word_table.tsv')):
        table = getattr(state,'OETRefData',{}).get('word_tables',{}).get(tableName,())
        for row in table[1:]:
            fields = row.split('\t')
            available = not filtered or fields[0][:3] in state.TEST_BOOK_LIST
            if available:
                rawCodes = fields[4].split(',') if language=='Heb' else [fields[8][:-1]]
                graph['availableStrongs'].update(code[0] for raw in rawCodes if (code:=normaliseStrongs(raw,language)))
            for lemma,strong in wordLexicalKeys(language,fields,graph):
                key = language,lemma
                graph['lemmaLabels'][key] = fields[3] if language=='Grk' else lemma
                if available and (language=='Heb' or fields[7]): graph['availableLemmas'].add(key)
                if strong:
                    pageCode,senseCode = strong
                    graph['lemmaCodes'][key].add(senseCode)
                    graph['strongLemmas'][pageCode].add(key)
                    if available: graph['availableStrongs'].add(pageCode)
    if not filtered:
        graph['availableStrongs'].update(f'H{n}' for n in range(1,8675))
        graph['availableStrongs'].update(f'G{n}' for n in range(1,5625))
        graph['availableLemmas'].update(('Heb',lemma) for lemma in graph['hebrewLemmas'][1:])
    for language,attribute in (('Heb','UBS_HEB_DATA'),('Grk','UBS_GNT_DATA')):
        for entry in getattr(state,attribute,()):
            key = language,entry['MainId']
            graph['ubs'][key] = entry
            graph['ubsByLemma'][(language,unicodedata.normalize('NFC',entry['Lemma']))].add(key)
            graph['ubsIds'][(language,entry['MainId'])] = (key,'Top')
            for base in entry.get('BaseForms',()):
                if identifier:=base.get('BaseFormID'): graph['ubsIds'][(language,identifier)] = (key,f'base{identifier}')
                for meaning in base.get('LEXMeanings') or ():
                    if identifier:=meaning.get('LEXID'): graph['ubsIds'][(language,identifier)] = (key,f'sense{identifier}')
                    if identifier and (code:=meaning.get('LEXEntryCode')):
                        graph['ubsMeaningsByCode'][(language,code)].add((key,f'sense{identifier}'))
            for raw in entry.get('StrongCodes',()):
                if code:=normaliseStrongs(raw,language):
                    graph['ubsByCode'][code[1]].add(key)
                    graph['ubsByStrong'][code[0]].add(key)
    # Plain dictionaries/sets can be inherited or serialised by page workers.
    for key,value in tuple(graph.items()):
        if isinstance(value,defaultdict): graph[key] = dict(value)
    state.lexicalAssociations = graph
    return graph


def _link(path, label, level, anchor='Top'):
    return f'<a href="{"../"*level}{quote(path)}#{anchor}">{escape(label)}</a>'


def ubsEntryLink(level, key, graph, label=None, anchor='Top'):
    entry = graph['ubs'][key]
    return _link(f"UBS/{key[0]}/{entry['Lemma']}.htm",label or entry['Lemma'],level,anchor)


def lexicalResourceLinks(level, language, state, *, lemma=None, strong=None, wordFields=None, ubsId=None):
    """Show verified alternatives without equating a shared number with meaning."""
    graph = prepareLexicalAssociations(state)
    lemmas, codes, entries = set(), set(), set()
    if lemma is not None:
        codes.update(graph['lemmaCodes'].get((language,lemma),()))
    if wordFields is not None:
        for wordLemma,code in wordLexicalKeys(language,wordFields,graph):
            if code: codes.add(code[1])
            label = graph['lemmaLabels'].get((language,wordLemma),wordLemma)
            entries.update(graph['ubsByLemma'].get((language,unicodedata.normalize('NFC',label)),()))
    if strong is not None:
        codes.add(strong)
        lemmas.update(graph['strongLemmas'].get(strong,()))
    if ubsId is not None:
        entry = graph['ubs'][(language,ubsId)]
        codes.update(code[1] for raw in entry.get('StrongCodes',()) if (code:=normaliseStrongs(raw,language)))
    if lemma is not None:
        label = graph['lemmaLabels'].get((language,lemma),lemma)
        entries.update(graph['ubsByLemma'].get((language,unicodedata.normalize('NFC',label)),()))
    strongLinks = {}
    for sense in sorted(codes):
        page,_ = normaliseStrongs(sense,language)
        if ubsId is not None: lemmas.update(graph['strongLemmas'].get(page,()))
        if page!=strong and wordFields is None:
            strongLinks[sense] = (_link(f'ref/{"Grk" if page[0]=="G" else "Heb"}Strng/{page}.htm',sense,level)
                                  if page in graph['availableStrongs'] else escape(sense))
        # Unsuffixed source numbers cannot select between dictionary homonyms.
        candidates = graph['ubsByCode'].get(sense,()) if sense[-1].isalpha() else ()
        entries.update(candidates or graph['ubsByStrong'].get(page,()))
    groups = []
    if strongLinks: groups.append("Strong’s: "+' · '.join(strongLinks.values()))
    lemmaLinks = [_link(f'ref/{lang}Lem/{lemmaFilename(lang,item)}',graph['lemmaLabels'].get((lang,item),item),level)
                  for lang,item in sorted(lemmas & graph['availableLemmas']) if (lang,item)!=(language,lemma)]
    if lemmaLinks: groups.append('Associated OET lemmas: '+' · '.join(lemmaLinks))
    if ubsId is not None: entries.discard((language,ubsId))
    entryLinks = []
    for key in sorted(entries):
        entry = graph['ubs'][key]
        identifier = ', '.join(entry.get('StrongCodes',()))
        label = entry['Lemma']+(f' ({identifier})' if identifier else '')
        entryLinks.append(ubsEntryLink(level,key,graph,label))
    if entryLinks: groups.append('UBS dictionary entries sharing a lemma or Strong’s identifier: '+' · '.join(entryLinks))
    if lemma is not None and hasattr(state,'BibleVersifications'):
        from studyReferences import lemmaTopics
        if links:=lemmaTopics(level,language,lemma,state):groups.append('Used in these topics: '+links)
    return '<div>'+''.join(f'<p class="note">{group}</p>' for group in groups)+'</div>' if groups else ''


def ubsRelatedLinks(level, language, values, state):
    """Resolve only exact, Unicode-normalised source lemmas; retain alternatives."""
    graph = prepareLexicalAssociations(state)
    result = []
    for value in values:
        word = value.get('Word','') if isinstance(value,dict) else value
        if not word: continue
        keys = graph['ubsByLemma'].get((language,unicodedata.normalize('NFC',word)),())
        result.append(' / '.join(ubsEntryLink(level,key,graph) for key in sorted(keys)) or escape(word))
    return ' · '.join(result)


def livenUBSLemmaReferences(text, level, state):
    """Expand documented dictionary/lemma tokens, retaining unverified selectors.

    Nonzero selector fields are not interpreted as sense IDs without a source
    specification. The entry link remains useful and the selector stays visible.
    """
    graph = prepareLexicalAssociations(state)
    pattern = re.compile(r'\{L:([^{}<>]+)<(SDB[HG]):([^{}<>]+)>\}')
    def replace(match):
        label,source,target = match.groups()
        target,separator,selector = target.partition(':')
        language = 'Heb' if source=='SDBH' else 'Grk'
        keys = graph['ubsByLemma'].get((language,unicodedata.normalize('NFC',target)),())
        linked = ' / '.join(ubsEntryLink(level,key,graph,label) for key in sorted(keys)) or escape(label)
        return linked+(f' [source selector {escape(selector)}]' if separator and selector.strip('0') else '')
    return pattern.sub(replace,text)


@cache
def _grammarPages(family):
    return {path.stem for path in Path(f'/srv/Bibles/unfoldingWordHelps/en_{family.lower()}/content').glob('*.rst')}


def interlinearReferenceCells(level,language,fields,state):
    """Prepare the same verified lemma, Strong's and grammar cells for both orders."""
    graph=prepareLexicalAssociations(state)
    lemmas=[]
    for lemma,_ in wordLexicalKeys(language,fields,graph):
        key=language,lemma
        label=graph['lemmaLabels'].get(key,lemma)
        lemmas.append(_link(f'ref/{language}Lem/{lemmaFilename(language,lemma)}',label,level)
                      if key in graph['availableLemmas'] else escape(label))
    strongs=[]
    for raw in (fields[4].split(',') if language=='Heb' else [fields[8][:-1]]):
        if code:=normaliseStrongs(raw,language):
            page,sense=code
            if language=='Heb' and fields[1].startswith('A'):sense='A'+sense[1:]
            local=(_link(f'ref/{language}Strng/{page}.htm',sense,level)
                   if page in graph['availableStrongs'] else escape(sense))
            external=f'<a title="View {page} on BibleHub" href="https://BibleHub.com/{"greek" if language=="Grk" else "hebrew"}/{page[1:]}.htm">↗</a>'
            strongs.append(f'{local} {external}')
    family='UGG' if language=='Grk' else 'UHG'
    def grammar(text,page):
        return (_link(f'ref/{family}/{page}.htm',text,level) if page in _grammarPages(family) else escape(text))
    if language=='Grk':
        role,morphology=fields[9:11]
        rolePage=dict(N='noun',A='adjective',V='verb',R='pronoun',D='adverb',P='preposition',C='conjunction').get(role)
        case=dict(N='nominative',G='genitive',D='dative',A='accusative',V='vocative').get(morphology[4] if len(morphology)==7 else '')
        mood=dict(I='indicative',S='subjunctive',M='imperative',O='optative',N='infinitive',P='participle').get(morphology[:1])
        morphPage=f'case_{case}' if case else f'mood_{mood}' if mood else None
        morphologyHtml=grammar(role,rolePage)+'-'+grammar(morphology,morphPage)
    else:
        parts=[]
        for morphology in fields[5].split(','):
            stem=dict(q='qal',N='niphal',p='piel',P='pual',h='hiphil',H='hophal',t='hithpael').get(morphology[1:2])
            page=(f'stem_{stem}' if morphology.startswith('V') and stem and not fields[1].startswith('A') else
                  dict(N='noun',V='verb',A='adjective',P='pronoun',R='preposition',C='conjunction',D='adverb').get(morphology[:1]))
            parts.append(grammar(morphology,page))
        morphologyHtml=escape(fields[16])+'-'+','.join(parts)
    return [' · '.join(dict.fromkeys(lemmas)) or '-',', '.join(dict.fromkeys(strongs)) or '-',morphologyHtml]
