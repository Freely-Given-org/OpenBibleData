#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Reference-preserving Bible navigation, shared by every Bible page family.

CHANGELOG:
    2026-11-01 Keep version, mode and reference choices together; resolve native sections.
    2026-11-01 Remove redundant visible selector-row labels.
    2026-11-01 Version the navigation script URL by its content to bypass stale CDN copies.
    2026-11-01 Restore independent views to the version row and identify the selected version below.
    2026-11-02 Navigate from the first verse of section-start bridges; fall back for invalid references.
    2026-11-03 Generate chapter/verse choices at build time; hide current choices with CSS.
"""
from hashlib import sha256
from pathlib import Path
import re
from xml.sax.saxutils import escape,unescape
import bos_books_codes_py

from BibleOrgSys.Reference.BibleVersificationMappings import MappingStatus
from navigation import mappedReferences,referenceHref
from versification import _mapReference,_storedReferences

PAGE_MODES={'book':'byDoc','bookIndex':'byDoc','chapter':'byC','chapterIndex':'byC',
    'section':'bySec','sectionIndex':'bySec','relatedPassage':'rel','relatedSectionIndex':'rel',
    'parallelVerse':'par','simpleVerse':'lst','interlinearVerse':'ilr'}
MODE_LABELS={'byDoc':'By Document','bySec':'By Section','byC':'By Chapter',
    'rel':'Related','par':'Parallel','lst':'Simple','ilr':'Interlinear'}
_ATTRIBUTE_ESCAPES={'"':'&quot;'}
# Read once per build process, not once per generated page. Changing the script
# must change its URL: the CDN otherwise serves the previous controls for hours.
_SCRIPT_VERSION=sha256(Path(__file__).with_suffix('.js').read_bytes()).hexdigest()[:12]
_COMMON_STYLE_VERSION=sha256(Path(__file__).with_name('common.css').read_bytes()).hexdigest()[:12]
INDEPENDENT_VIEWS=('Related','Parallel','Simple','Interlinear','Topics','Reference','Dictionary','Search')


def _attr(value):return escape(str(value),_ATTRIBUTE_ESCAPES)


def addReferenceNavigation(pageHtml):
    """Build ordinary chapter/verse links, including when JavaScript is disabled.

    Whole-document and multi-chapter section pages contain a verse row for each
    chapter. CSS selects the appropriate row from the URL's fragment, and omits
    its current chapter/verse choice without leaving a separator behind.
    """
    header=re.search(r'<div class="header" id="bibleNavigation"[^>]*>',pageHtml)
    if not header:return pageHtml
    attrs=dict(re.findall(r'data-([\w-]+)="([^"]*)"',header[0]))
    mode=attrs['mode']
    context=('TEST\u2003' if attrs['test']=='true' else '')+{
        'par':'ParallelVerse','lst':'VerseList','ilr':'InterlinearVerse','rel':'Related OET-RV',
    }.get(mode,attrs['version'])
    book=attrs.get('book','')
    def chapterContext(match):
        opening,contents,closing=match.groups()
        hasBook=bool(contents.split('<',1)[0].strip()) or 'title="Choose “book”"' in contents
        prefix=f'{context} ' if hasBook else f'{context} {book}\u2003'
        return f'{opening}{prefix}{contents}{closing}'
    pageHtml=re.sub(r'(<p class="chLst"[^>]*>)(.*?)(</p><!--chLst-->)',chapterContext,pageHtml)
    if mode in ('par','lst','ilr') or attrs.get('chapter')=='-1':return pageHtml

    # Use the same primary verse anchors as the text. Deduplicate overlapping
    # OET columns without inventing links into missing or bridged verses.
    chapters={}
    anchors={}
    verseTargets={}
    for anchor,chapter,verse in re.findall(r'\bid="((?:a)?C(\d+)V(\d+[a-z]*))"',pageHtml):
        chapters.setdefault(chapter,{}).setdefault(verse,anchor)
        anchors[anchor]=chapter
        verseTargets.setdefault((chapter,verse),[]).append(anchor)
    if not chapters:return pageHtml
    # Existing short #V anchors precede the full reference, sometimes with an
    # empty chapter anchor between them. Keep those older incoming links working.
    for alias,chapter,verse in re.findall(
            r'\bid="(V\d+[a-z]*)"[^>]*></span>\s*(?:<span\b[^>]*></span>\s*)*?'
            r'<span\b[^>]*\bid="(?:a)?C(\d+)V(\d+[a-z]*)"',pageHtml):
        if alias[1:]==verse and (chapter,verse) in verseTargets:
            verseTargets[chapter,verse].append(alias)
            anchors[alias]=chapter
    currentChapter=attrs.get('chapter')
    if currentChapter not in chapters:currentChapter=next(iter(chapters))
    currentVerse=attrs.get('verse') if attrs.get('chapter')==currentChapter else None

    def chapterChoice(chapter,link):
        current=' data-nav-current="true"' if chapter==currentChapter else ''
        return f'<span data-nav-chapter="{chapter}"{current}>\u2003{link}</span>'
    def chapterChoices(match):
        paragraph=match[0]
        return re.sub(r'\u2003?(<a\b[^>]*>(?:C|Sg|Ps)(\d+)</a>)',
            lambda m:chapterChoice(m[2],m[1]),paragraph)
    pageHtml=re.sub(r'<p class="chLst"[^>]*>.*?</p><!--chLst-->',chapterChoices,pageHtml)
    chapterRow=re.search(r'<p class="chLst"[^>]*>.*?</p><!--chLst-->',pageHtml)
    rows=[]
    if not chapterRow:
        choices=''.join(chapterChoice(chapter,
            f'<a href="#{next(iter(verses.values()))}">C{chapter}</a>')
            for chapter,verses in chapters.items())
        rows.append(f'<p class="chLst bibleReferenceChoices" aria-label="Chapters">{context} {book}{choices}</p>')
    styles=[]
    for chapter,verses in chapters.items():
        lastVerse=max(int(re.match(r'\d+',verse)[0]) for verse in verses)
        step=5 if lastVerse>100 else 4 if lastVerse>80 else 3 if lastVerse>60 else 2 if lastVerse>40 else 1
        choices=[]
        for verse,anchor in verses.items():
            number=int(re.match(r'\d+',verse)[0])
            if number!=0 and (number-1)%step:continue
            current=' data-nav-current="true"' if chapter==currentChapter and verse==currentVerse else ''
            choices.append(f'<span data-nav-verse="{anchor}"{current}>\u2003<a href="#{anchor}">V{verse}</a></span>')
            targets=', '.join(f'#{target}:target' for target in verseTargets[chapter,verse])
            styles.append(f'body:has({targets}) [data-nav-verse="{anchor}"] {{ display:none; }}')
        default=' data-nav-default="true"' if chapter==currentChapter else ''
        rows.append(f'<p class="vsLst bibleReferenceChoices" data-nav-verses="{chapter}"{default} aria-label="Verses">'
                    f'{context} {book} {chapter}{"".join(choices)}</p>')
        styles.append(f'body:has([data-nav-reference="{chapter}"]:target) [data-nav-chapter="{chapter}"] {{ display:none; }}')
        styles.append(f'body:has([data-nav-reference="{chapter}"]:target) p.bibleReferenceChoices[data-nav-verses="{chapter}"] {{ display:block; }}')
        anchors[f'C{chapter}']=chapter
        anchors[f'aC{chapter}']=chapter

    # The anchor itself identifies the chapter, including chapters whose first
    # available verse is not verse 1. This also works with browser Back/Forward.
    pageHtml=re.sub(r'\bid="([^"]+)"',lambda m:
        f'{m[0]} data-nav-reference="{anchors[m[1]]}"' if m[1] in anchors else m[0],pageHtml)
    if chapterRow:
        point=pageHtml.index('</p><!--chLst-->',pageHtml.index(chapterRow[0]))+len('</p><!--chLst-->')
    else:
        bookRow=re.search(r'<p class="bkLst"[^>]*>.*?</p><!--bkLst-->',pageHtml)
        point=bookRow.end() if bookRow else pageHtml.index('</div><!--header-->')+len('</div><!--header-->')
    pageHtml=pageHtml[:point]+'\n'+'\n'.join(rows)+pageHtml[point:]
    return pageHtml.replace('</head>','<style>\n'+'\n'.join(styles)+'\n</style>\n</head>',1)


def colourIndependentViews(top):
    """Distinguish version-independent destinations on every page family."""
    def colourRow(match):
        entries=[]
        for entry in match[1].split('\u2003'):
            label=unescape(re.sub(r'<[^>]*>','',entry))
            entries.append(f'<span class="independentView">{entry}</span>'
                if label in INDEPENDENT_VIEWS and 'class="independentView"' not in entry else entry)
        return '<p class="wrkLst">'+'\u2003'.join(entries)+'</p><!--wrkLst-->'
    top=re.sub(r'<p class="wrkLst">(.*?)</p><!--wrkLst-->',colourRow,top,flags=re.DOTALL)
    return re.sub(r'common\.css(?:\?[^"<>]*)?"',f'common.css?v={_COMMON_STYLE_VERSION}"',top)


def _available(version,book,state):
    key='OET-RV' if version=='OET' else version
    bible=state.preloadedBibles.get(key)
    selected=state.booksToLoad.get(version,state.booksToLoad.get(key,()))
    if bible is None or book not in bible:return False
    return ('ALL' in selected or book in selected
        or ('NT' in selected and bos_books_codes_py.is_new_testament_nr(book))
        or ('OT' in selected and bos_books_codes_py.is_old_testament_nr(book)))


def pageReference(filename):
    """The page's reference is the fallback until a reader selects a verse."""
    if not filename:return ()
    match=re.search(r'/([A-Z0-9]{3})(?:_C(\d+)|_S\d+|_Intro)?\.htm(?:#(.*))?$',filename)
    if not match:return ()
    book,chapter,anchor=match.groups()
    if anchor and (verse:=re.fullmatch(r'C(-?\d+)V(\d+[a-z]*)',anchor)):
        return book,verse[1],verse[2]
    if chapter:return book,chapter,'1'
    if '_Intro.htm' in filename:return book,'-1','0'
    return (book,)


def _navigationStart(reference):
    """Use the start of a stored verse bridge, or keep only the known book."""
    reference=tuple(map(str,reference))
    if len(reference)<3:return reference
    if not re.fullmatch(r'-?\d+',reference[1]):return reference[:1]
    match=re.fullmatch(r'(\d+)([a-z]*)(?:[-–](\d+)([a-z]*))?',reference[2])
    if not match:return reference[:1]
    if match[3] and (int(match[3]),match[4])<(int(match[1]),match[2]):return reference[:1]
    return (*reference[:2],match[1]+match[2],*reference[3:])


def navigationRoutes(level,reference,sourceVersion,targetVersion,state):
    """Return only available modes; preserve a book when an exact verse is absent.

    Combined OET pages use RV anchors. A None source is a shared study view,
    whose reference belongs to the configured navigation versification.
    """
    from BibleOrgSys.BibleOrgSysGlobals import makeSafeString
    from referencePassages import _nativeContextReference
    reference=_navigationStart(reference)
    prefix='../'*level
    base=f'{prefix}{makeSafeString(targetVersion)}'
    key='OET-RV' if targetVersion=='OET' else targetVersion
    bible=state.preloadedBibles.get(key)
    sections=getattr(state,'sectionsListsForSections',{}).get(key,{})
    routes={'home':f'{base}/', 'byDoc':f'{base}/byDoc/', 'byC':f'{base}/byC/'}
    if sections:routes['bySec']=f'{base}/bySec/'
    if not reference:return routes
    book=reference[0]
    if _available(targetVersion,book,state):
        routes.update(byDoc=f'{base}/byDoc/{book}.htm#Top',byC=f'{base}/byC/{book}.htm#Top')
        if sections.get(book):routes['bySec']=f'{base}/bySec/{book}.htm#Top'
    if len(reference)<3:return routes
    sourceKey='OET-RV' if sourceVersion=='OET' else sourceVersion
    if int(reference[1])<1:
        if not _available(targetVersion,book,state):return routes
        try:hasIntro=bible.getNumVerses(book,'-1')
        except (AttributeError,KeyError):hasIntro=False
        if hasIntro:routes['byC']=f'{base}/byC/{book}_Intro.htm#Top'
        for section in sections.get(book,()):
            if str(section[1])=='-1' and not section[6].startswith('Alternate '):
                routes['bySec']=f'{base}/bySec/{section[-1]}#Top'
                break
        return routes
    if sourceKey:
        mapped=mappedReferences(reference,sourceKey,key,state)
    else:
        match=re.fullmatch(r'(\d+)([a-z]*)',str(reference[2]))
        result=_mapReference(state.navigationVersification,state.BibleVersifications[key],
            (book,str(reference[1]),match[1],match[2] or None))
        mapped=_storedReferences(key,result.references,state) if result.status==MappingStatus.EXACT else ()
    if not mapped:return routes
    ref=mapped[0]
    if not _available(targetVersion,ref[0],state):return routes
    native=_nativeContextReference(bible,tuple(ref)) if hasattr(bible,'getPassageData') else ref
    if not native:return routes
    book,chapter,verse=map(str,native[:3])
    if len(native)>3:verse+=native[3] or ''
    anchor='Top' if verse=='0' else f'C{chapter}V{verse}'
    routes.update(byC=f'{base}/byC/{book}_C{chapter}.htm#{anchor}',
                  byDoc=f'{base}/byDoc/{book}.htm#{anchor}')
    if sections.get(book):
        from openbibledata_rust import findSectionNumber
        index=findSectionNumber(key,book,chapter,verse,state)
        if index is not None:
            section=sections[book][index]
            # Some sections contain headings only at their starting reference.
            sectionAnchor='Top' if (str(section[1]),str(section[2]))==(chapter,verse) else anchor
            routes['bySec']=f'{base}/bySec/{section[-1]}#{sectionAnchor}'
    return routes


def preferredReadingHref(level,version,book,chapter,verse,state):
    """Beside-the-text version abbreviations open a section where one exists."""
    from BibleOrgSys.BibleOrgSysGlobals import makeSafeString
    if version in state.versionsWithoutTheirOwnPages:
        return f'{"../"*level}{makeSafeString(version)}/details.htm#Top'
    routes=navigationRoutes(level,(book,str(chapter),str(verse)),version,version,state)
    section=routes.get('bySec','')
    return section if '_S' in section else routes['byC']


def studyHref(level,mode,reference,source,state):
    prefix='../'*level
    reference=_navigationStart(reference)
    if len(reference)<3 or int(reference[1])<1:return f'{prefix}{mode}/'
    if source:
        source='OET-RV' if source=='OET' else source
        profile=state.BibleVersifications.get('OET-RV' if source=='OET' else source)
        if not profile:return f'{prefix}{mode}/'
        book,chapter,verse=reference[:3]
        for original,layouts in getattr(state,'BibleSourceBookLayouts',{}).get(source,{}).items():
            for first,last,stored,offset in layouts:
                if book==stored and first<=int(chapter)-offset<=last:
                    book,chapter=original,str(int(chapter)-offset)
        match=re.fullmatch(r'(\d+)([a-z]*)',reference[2])
        result=_mapReference(profile,state.navigationVersification,
            (book,chapter,match[1],match[2] or None))
        if result.status!=MappingStatus.EXACT:return f'{prefix}{mode}/'
        reference=result.references[0]
    if mode=='ilr' and not _available('OET',reference[0],state):return f'{prefix}{mode}/'
    # Heading pages differ between study modes. Their existing page controls
    # decide availability; avoid inventing a verse-zero destination here.
    if str(reference[2])=='0':return f'{prefix}{mode}/'
    return referenceHref(level,reference,'OET',mode)


def bibleNavigation(top,level,version,pageType,filename,state,reference=()):
    """Offer independent views beside versions; keep reading modes version-specific."""
    if pageType not in PAGE_MODES:return top
    mode=PAGE_MODES[pageType]
    reference=_navigationStart(reference or pageReference(filename))
    source=None if mode in ('par','lst','ilr') else version
    selected=version or 'OET'
    currentRoutes=navigationRoutes(level,reference,source,selected,state)
    work=re.search(r'<p class="wrkLst">(.*?)</p><!--wrkLst-->',top,re.DOTALL)
    if not work:return top
    entries=[]
    for entry in work[1].split('\u2003'):
        label=unescape(re.sub(r'<[^>]*>','',entry))
        if label in INDEPENDENT_VIEWS[:4]:
            key=next(key for key,value in MODE_LABELS.items() if value==label)
            if key==mode:
                entry=f'<b aria-current="true">{label}</b>'
            else:
                href=studyHref(level,key,reference,source,state) if key!='rel' else f'{"../"*level}rel/'
                entry=re.sub(r'<a\b[^>]*>(.*?)</a>',
                    lambda m:f'<a data-bible-mode="{key}" href="{_attr(href)}">{m[1]}</a>',entry)
        elif label in state.BibleVersifications and label in state.BibleVersions:
            routes=navigationRoutes(level,reference,source,label,state)
            # Shared study pages deliberately restart version selection from
            # the purple bar; their beside-the-text links retain the passage.
            href=routes['home'] if mode in ('par','lst','ilr','rel') else routes.get(mode,routes['byC'])
            attributes=' '.join(f'data-nav-{name.lower()}="{_attr(path)}"' for name,path in routes.items())
            if label==version and mode not in ('rel','par','lst','ilr'):
                entry=f'<b aria-current="true">{escape(label)}</b>'
            else:
                entry=re.sub(r'<a\b[^>]*>(.*?)</a>',
                    lambda m:f'<a title="{_attr(state.BibleNames.get(label,label))}" data-bible-version="{_attr(label)}" {attributes} href="{_attr(href)}">{m[1]}</a>',entry)
        entries.append(entry)
    workHtml='<p class="wrkLst">'+'\u2003'.join(entries)+'</p><!--wrkLst-->'
    top=top[:work.start()]+workHtml+top[work.end():]
    modes=['TEST',escape(selected)] if state.TEST_MODE_FLAG else [escape(selected)]
    for key,label in MODE_LABELS.items():
        if key not in ('byDoc','bySec','byC'):continue
        if key==mode:
            modes.append(f'<b aria-current="true">{label}</b>');continue
        href=currentRoutes.get(key)
        if href:modes.append(f'<a data-bible-mode="{key}" href="{_attr(href)}">{label}</a>')
    modes.append(f'<a href="{_attr(currentRoutes["home"])}details.htm#Top">Version details</a>')
    modeHtml='' if mode in ('rel','par','lst','ilr') else '<p class="viewLst">'+'\u2003'.join(modes)+'</p><!--viewLst-->'
    top=re.sub(r'<p class="viewLst">.*?</p><!--viewLst-->',lambda _m:modeHtml,top,flags=re.DOTALL) if 'class="viewLst"' in top else top.replace('</div><!--header-->',modeHtml+'</div><!--header-->')
    attrs=f'id="bibleNavigation" data-root="{"../"*level}" data-version="{_attr(selected)}" data-mode="{mode}" data-test="{str(bool(state.TEST_MODE_FLAG)).lower()}"'
    if reference:attrs+=f' data-book="{reference[0]}"'
    if len(reference)>=3:attrs+=f' data-chapter="{reference[1]}" data-verse="{reference[2]}"'
    top=top.replace('<div class="header">',f'<div class="header" {attrs}>',1)
    return top.replace('</head>',f'<script src="{"../"*level}bibleNavigation.js?v={_SCRIPT_VERSION}" defer></script></head>',1)
