#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Resolve grammar source labels and contents entries to local HTML pages.

CHANGELOG:
    2026-10-30 Preserve Sphinx references and render validated contents links.
    2026-11-02 Keep preview summaries concise beside the shared OET jump controls.
"""
import logging
from pathlib import Path
import re
import unicodedata
from urllib.parse import unquote, urlsplit
from xml.sax.saxutils import escape

from docutils import nodes
import bos_books_codes_py

from referencePassages import parseReferenceSelection, renderReferencePassage


def grammarReferenceRole(folder, relatedFolders=None):
    """Index explicit source labels, including section labels unrelated to filenames."""
    def indexFolder(sourceFolder, prefix=''):
        indexed = {}
        for path in sorted(Path(sourceFolder).glob('*.rst')):
            filename = f'{prefix}{path.stem}.htm'
            indexed.setdefault(path.stem, (f'{filename}#Top', path.stem.replace('_',' ')))
            source = path.read_text(encoding='utf-8')
            for match in re.finditer(r'^\.\. _([^:\n]+):\s*$',source,re.MULTILINE):
                label = match[1].strip()
                target = (f'{filename}#{nodes.make_id(label)}', label.replace('_',' '))
                if label in indexed and indexed[label][0].split('#')[0] != filename:
                    raise ValueError(f'Duplicate grammar label {label!r} in {path} and {indexed[label][0]}')
                indexed[label] = target
        return indexed

    targets = indexFolder(folder)
    for prefix,relatedFolder in (relatedFolders or {}).items():
        for label,target in indexFolder(relatedFolder,prefix).items():
            targets.setdefault(label,target)

    def referenceRole(name, rawtext, text, lineno, inliner, options=None, content=None):
        match = re.fullmatch(r'(.*?)\s*<([^<>]+)>',text)
        label = (match[2] if match else text).strip()
        display = match[1].strip() if match else targets.get(label,('',label.replace('_',' ')))[1]
        if target := targets.get(label):
            return [nodes.reference(rawtext,display,refuri=target[0])], []
        source = inliner.document.current_source
        if source == '<string>': source = getattr(referenceRole,'sourcePath',source)
        logging.warning('Grammar %s:%s: unresolved reference %r (%s)',source,lineno,label,display)
        return [nodes.inline(rawtext,display)], []
    return referenceRole


def expandGrammarContents(source, folder):
    """Replace Sphinx toctrees with ordinary rST lists before docutils conversion.

    Read the source entries directly; rendered error messages and blank lines
    must never become filenames. Preserve explicitly named and nested entries.
    """
    lines = source.splitlines()
    result = []
    inContents = False
    for lineNumber,line in enumerate(lines,1):
        if line.strip().startswith('.. toctree::'):
            inContents = True
            result.append('')
            continue
        if not inContents:
            result.append(line)
            continue
        if not line.strip() or line.lstrip().startswith(':'):
            continue
        if not line.startswith((' ', '\t')):
            inContents = False
            result.extend(('',line))
            continue
        text = line.strip()
        match = re.fullmatch(r'(.*?)\s*<([^<>]+)>',text)
        target = (match[2] if match else text).strip()
        label = match[1].strip() if match else target.replace('_',' ')
        if not re.fullmatch(r'[A-Za-z0-9_-]+',target) or not (Path(folder)/f'{target}.rst').is_file():
            logging.warning('Grammar %s/index.rst:%s: missing contents target %r',folder,lineNumber,target)
            item = label
        else:
            item = f'`{label} <{target}.htm#Top>`_'
        indent = '  ' if len(line)-len(line.lstrip()) > 3 else ''
        result.extend(('',f'{indent}* {item}'))
    return '\n'.join(result)+'\n'


def _citationPattern():
    aliases = {}
    books = [BBB for BBB in bos_books_codes_py.get_all_bos_book_codes()
             if bos_books_codes_py.is_chapter_verse_book(BBB)]
    for BBB in books:
        for name in (BBB,bos_books_codes_py.bos_book_code_to_usfm_abbrev(BBB),
                     bos_books_codes_py.get_english_name_nr(BBB)):
            if name: aliases[name.lower()] = BBB
    # USFM abbreviations are source identifiers, not names of combined BOS books.
    for BBB in books:
        abbreviation = bos_books_codes_py.bos_book_code_to_usfm_abbrev(BBB)
        if abbreviation:
            aliases[abbreviation.lower()] = bos_books_codes_py.usfm_abbrev_to_bos_book_code(abbreviation)
    aliases.update({'1 chr':'CH1','2 chr':'CH2','matt':'MAT','matt.':'MAT','maττ':'MAT',
                    'mk':'MRK','jn':'JHN','1 jn':'JN1','1 cor.':'CO1','2 cor.':'CO2',
                    'ith':'TH1','ico':'CO1','rev.':'REV'}) # Explicit source spellings.
    aliases['mathew'] = 'MAT' # A spelling used in the supplied participle article.
    names = '|'.join(re.escape(name) for name in sorted(aliases,key=len,reverse=True))
    return aliases,re.compile(r'\b('+names+r')\s+(\d+:\d+[a-z]?(?:\s*(?:[-–—]+|[,;])\s*(?:\d+:)?\d+[a-z]?)*)(?!\w)',re.I)


GRAMMAR_BOOK_ALIASES, GRAMMAR_CITATION = _citationPattern()


def _quotedWordLinks(tableHtml, references, level, state):
    """Link a bold example word only if it matches one native occurrence uniquely."""
    from oetWords import mappedWordRows, wordTableName
    from openbibledata_rust import getGreekWordpageFilename, getHebrewWordpageFilename
    from BibleOrgSys.Reference.BibleVersificationMappings import VersificationMappingError

    data = getattr(state,'OETRefData',{})
    if not data.get('word_table_indexes') or not references: return ''
    BBB = references[0][0]
    greek = bos_books_codes_py.is_new_testament_nr(BBB)
    try: rows = mappedWordRows('eng',references,state)
    except (KeyError,VersificationMappingError): return ''
    if state.TEST_MODE_FLAG and not state.ALL_TEST_REFERENCE_PAGES_FLAG and BBB not in state.TEST_BOOK_LIST: return ''
    def normalise(text):
        return ''.join(c for c in unicodedata.normalize('NFD',text)
                       if ('\u0370'<=c<='\u03ff' if greek else '\u05d0'<=c<='\u05ea')).casefold()
    candidates = {}
    for number in rows:
        fields = data['word_tables'][wordTableName(BBB)][number].split('\t')
        if greek and not fields[7]: continue # Unused Greek variant.
        word = fields[1] if greek else fields[6]
        candidates.setdefault(normalise(word),[]).append((number,word))
    links = []
    for bold in re.findall(r'<strong>(.*?)</strong>',tableHtml,re.DOTALL):
        plain = re.sub('<[^>]+>','',bold).strip()
        if re.search(r'\s',plain): continue # A highlighted phrase is not one word.
        matches = candidates.get(normalise(plain),())
        if len(matches) != 1: continue
        number,word = matches[0]
        filename = (getGreekWordpageFilename if greek else getHebrewWordpageFilename)(number,state)
        folder = 'GrkWrd' if greek else 'HebWrd'
        links.append(f'<a href="{"../"*level}ref/{folder}/{filename}#Top">{escape(word)}</a>')
    return f'<p class="note">Word details: {" · ".join(dict.fromkeys(links))}</p>' if links else ''


def addGrammarPassages(html, level, pageName, state):
    """Preserve original examples and add clearly labelled OET comparisons below them.

    The leading citation uses English numbering in these sources; Hebrew
    alternatives, when present, are explicitly parenthesised in the caption.
    """
    count = 0
    def add(match):
        nonlocal count
        caption = match[2]
        citation = GRAMMAR_CITATION.search(caption)
        if not citation: return match[0]
        BBB = GRAMMAR_BOOK_ALIASES[citation[1].lower()]
        if pageName.startswith('UHG/') and citation[1].upper() == 'JUD': BBB = 'JDG'
        selection = re.sub(r'[-–—]+','-',citation[2])
        try: references = parseReferenceSelection(BBB,selection,'eng')
        except (ValueError,KeyError) as error:
            logging.warning('Grammar %s: cannot link example %r: %s',pageName,citation[0],error)
            return match[0]
        count += 1
        comparison = renderReferencePassage(level,references,'eng',state,
            instanceId=f'grammar{count}',label=citation[0])
        words = _quotedWordLinks(match[0],references,level,state)
        return match[0]+comparison+words
    return re.sub(r'(<table\b[^>]*>\s*<caption>)(.*?)(</caption>.*?</table>)',add,html,flags=re.DOTALL)


def grammarMorphologyExamples(pageName, level, state):
    """Offer a few mechanically tagged forms, without assigning interpretive functions."""
    from openbibledata_rust import getGreekWordpageFilename, getHebrewWordpageFilename
    data = getattr(state,'OETRefData',{})
    if 'grammarExamples' not in data:
        examples = data['grammarExamples'] = {}
        stems = dict(q='qal',N='niphal',p='piel',P='pual',h='hiphil',H='hophal',t='hithpael')
        cases = dict(N='nominative',G='genitive',D='dative',A='accusative',V='vocative')
        for language in ('OT','NT'):
            table = data.get('word_tables',{}).get(f'OET-LV_{language}_word_table.tsv',())
            for number,row in enumerate(table[1:],1):
                fields = row.split('\t')
                BBB = fields[0][:3]
                if state.TEST_MODE_FLAG and not state.ALL_TEST_REFERENCE_PAGES_FLAG and BBB not in state.TEST_BOOK_LIST: continue
                if language == 'NT':
                    if not fields[7] or len(fields[10])!=7 or fields[10][4] not in cases: continue
                    key = f'UGG/case_{cases[fields[10][4]]}.rst'
                    word = fields[1]
                else:
                    if fields[1].startswith('A'): continue
                    morphology = next((part for part in fields[5].split(',') if part.startswith('V')), '')
                    if len(morphology)<2 or morphology[1] not in stems: continue
                    key = f'UHG/stem_{stems[morphology[1]]}.rst'
                    word = fields[6]
                items = examples.setdefault(key,[])
                if len(items)<3: items.append((language,number,word,fields[0]))
    links = []
    for language,number,word,reference in data['grammarExamples'].get(pageName,()):
        greek = language == 'NT'
        filename = (getGreekWordpageFilename if greek else getHebrewWordpageFilename)(number,state)
        folder = 'GrkWrd' if greek else 'HebWrd'
        links.append(f'<a href="{"../"*level}ref/{folder}/{filename}#Top">{escape(word)} ({escape(reference)})</a>')
    return '<h2>Examples tagged with this form</h2><p class="note">'+ ' · '.join(links)+'</p>' if links else ''


def localiseGrammarLinks(folder, referenceRoot):
    """Rewrite only external grammar destinations with a verified local file and anchor."""
    root = Path(referenceRoot)
    for path in Path(folder).glob('*.htm'):
        html = path.read_text(encoding='utf-8')
        def replace(match):
            url = urlsplit(match[1])
            family = {'ugg.readthedocs.io':'UGG','uhg.readthedocs.io':'UHG'}.get(url.hostname)
            if not family: return match[0]
            stem = Path(url.path).stem
            target = root/family/f'{stem}.htm'
            if not target.is_file(): return match[0]
            anchor = unquote(url.fragment) or 'Top'
            # Sphinx's anonymous numeric IDs are not stable in docutils output.
            if re.fullmatch(r'id\d+',anchor): return match[0]
            if f'id="{anchor}"' not in target.read_text(encoding='utf-8'): return match[0]
            prefix = '' if path.parent.name == family else f'../{family}/'
            return f'href="{prefix}{stem}.htm#{anchor}"'
        html = re.sub(r'href="(https?://[^\"]+)"',replace,html)
        path.write_text(html,encoding='utf-8')
