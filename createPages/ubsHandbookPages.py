#!/usr/bin/env -S uv run
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""
Create pages for the UBS flora, fauna, and realia handbooks
    in UBS/Fauna/, UBS/Flora/, and UBS/Realia/ (one page per article, plus index.htm for each handbook).

The handbooks' images come from the UBS image collection zip files (which aren't in our adapted repo),
    and are resized (once) into a cache folder, then copied into UBS/img/.
    Images that aren't available locally (e.g., the OPEN-AI collection) are left out.

CHANGELOG:
    2026-11-19 First version
    2026-11-19 Place an article's images together at the top right, and keep them clear of the footer.
"""
import logging
from pathlib import Path
import re
import shutil
from urllib.parse import quote
from xml.sax.saxutils import escape, quoteattr
import zipfile

from html import makeTop, makeBottom, checkHtml
from ubsHandbooks import HANDBOOKS, HandbookEntry, HandbookImage
from ubsHOTTP import parseUBSWordReference
from ubsStudyLinks import _navigationRefs, _verseLink
from openbibledata_rust import getOETTidyBBB


IMAGE_ZIP_FILES = ('web/web.zip', 'UBS/ubs.zip', 'Pritz/pritz.zip') # In state.UBS_IMAGES_FOLDER
MAX_IMAGE_SIZE = (900, 900) # pixels
JPEG_QUALITY = 82
MAX_INLINE_REFERENCES = 8 # Per lemma before the rest go into a <details> list


def _referenceLinks(level:int, codes:list[str], state) -> list[str]:
    """
    Convert UBS scripture codes (or ranges of codes) to links to the parallel verse pages.
    """
    links = []
    for code in codes:
        start, _dash, end = code.partition('-')
        startRef, endRef = parseUBSWordReference(start), (parseUBSWordReference(end) if end else None)
        if startRef is None:
            logging.warning(f"UBS handbook: can't parse scripture code {code!r}"); links.append(escape(code)); continue
        if startRef[2] == '0': # A chapter reference
            label = f'{getOETTidyBBB(startRef[0])} {startRef[1]}'
            navigationRefs = _navigationRefs([(startRef[0], startRef[1], '1')], state)
        else:
            navigationRefs = _navigationRefs([startRef[:3]], state)
            label = f'{getOETTidyBBB(navigationRefs[0][0])} {navigationRefs[0][1]}:{navigationRefs[0][2]}' if navigationRefs \
                        else f'{getOETTidyBBB(startRef[0])} {startRef[1]}:{startRef[2]}'
            if endRef and endRef[:3] != startRef[:3]:
                endNavigationRefs = _navigationRefs([endRef[:3]], state) or [endRef[:3]]
                label += f'–{endNavigationRefs[0][2]}' if endNavigationRefs[0][:2] == (navigationRefs[0][:2] if navigationRefs else startRef[:2]) \
                            else f'–{endNavigationRefs[0][1]}:{endNavigationRefs[0][2]}'
        links.append( _verseLink(level, navigationRefs[0], label, state) if navigationRefs else escape(label) )
    return list(dict.fromkeys(links))
# end of _referenceLinks


class HandbookRenderer:
    """
    Renders handbook articles, and keeps track of which images are needed.
    """
    def __init__(self, level:int, handbook:str, state, availableImages:set[str]) -> None:
        self.level, self.handbook, self.state, self.availableImages = level, handbook, state, availableImages
        self.usedImages:dict[str,HandbookImage] = {}
        self.articleFigures:list[str] = [] # Figures for the article being rendered (placed together at the top)

    def figure(self, image:HandbookImage|None) -> str:
        if image is None or image.filename not in self.availableImages: return ''
        self.usedImages[image.filename] = image
        filename = imageOutputFilename(image.filename)
        caption = escape(image.caption) if image.caption else ''
        credit = f' <small class="hbCredit">({escape(image.copyright)})</small>' if image.copyright else ''
        captionHtml = f'<p class="hbCaption">{caption}{credit}</p>' if caption or credit else ''
        return f'''<div class="hbImage"><img src="../img/{quote(filename)}" alt={quoteattr(image.caption or image.imageID)} loading="lazy">{captionHtml}</div><!--hbImage-->'''

    def paragraph(self, innerXML:str, images:dict[str,HandbookImage]) -> str:
        """
        Convert the inner XML of a handbook <Paragraph> to HTML.

        Any <Image> placements are collected in self.articleFigures (rather than left inline).
        """
        def imagePlacement(match:re.Match) -> str:
            self.articleFigures.append( self.figure(images.get(match.group(1))) )
            return ''
        html = re.sub(r'<Image Id="([^"]*)"\s*/>', imagePlacement, innerXML)
        html = re.sub(r'<s>([^<]*)</s>', lambda match: ', '.join(_referenceLinks(self.level, match.group(1).split(), self.state)), html)
        html = re.sub(r'<l target="([^"]*)">(.*?)</l>', lambda match: self.articleLink(match.group(1), match.group(2)), html)
        html = re.sub(r'<a>(.*?)</a>', r'<cite>\1</cite>', html) # Bibliography abbreviations
        html = re.sub(r'<(?!/?(?:i|b|u|sup|cite|a|span|small)\b)[^>]*>', '', html) # Remove any other source markup
        return f'<p class="hbPara">{html.strip()}</p>' if html.strip() else ''

    def articleLink(self, target:str, labelHtml:str) -> str:
        prefix, _colon, key = target.partition(':')
        handbook = next((handbook for handbook in HANDBOOKS if handbook.lower() == prefix.lower()), None)
        if handbook is None or key not in getattr(self.state, 'UBS_HANDBOOKS', {}).get(handbook, {}):
            return labelHtml
        return f'<a href="../{handbook}/{quote(articleFilename(key))}#Top">{labelHtml}</a>'

    def lemmaSet(self, lemmaSet) -> str:
        language = lemmaSet.language
        lemmaIndex, folder = (getattr(self.state, 'UBS_GNT_LEMMA_INDEX', {}), 'Grk') if language == 'Greek' \
                                else (getattr(self.state, 'UBS_HEB_LEMMA_INDEX', {}), 'Heb')
        lemmaHtml = f'<span class="{"greek" if language == "Greek" else "hebrew"}">{escape(lemmaSet.lemma)}</span>'
        if lemmaSet.lemma in lemmaIndex:
            lemmaHtml = f'<a title="Go to UBS dictionary entry" href="../../UBS/{folder}/{quote(lemmaSet.lemma)}.htm#Top">{lemmaHtml}</a>'
        transliteration = f' <i>{escape(lemmaSet.transliteration)}</i>' if lemmaSet.transliteration else ''
        links = _referenceLinks(self.level, lemmaSet.references, self.state)
        referencesHtml = ', '.join(links[:MAX_INLINE_REFERENCES])
        if len(links) > MAX_INLINE_REFERENCES:
            referencesHtml += f'''<details><summary>{len(links)-MAX_INLINE_REFERENCES} more references</summary>{', '.join(links[MAX_INLINE_REFERENCES:])}</details>'''
        return f'<li>{escape(language)} {lemmaHtml}{transliteration}: {referencesHtml}</li>'

    def article(self, entry:HandbookEntry) -> str:
        """
        Return the article HTML, with all its images floated together at the top right
            (and wrapped so that the floats can't run into the page footer).
        """
        self.articleFigures = []
        html = ''
        if entry.index:
            items = ''.join(f'<li>{self.articleLink(f"{self.handbook}:{key}", escape(description))}</li>' for key, description in entry.index)
            html += f'<div class="hbIndex"><ul>{items}</ul></div><!--hbIndex-->'
        for section in entry.sections:
            sectionHtml = ''
            if section.lemmaSets:
                sectionHtml += f'''<div class="hbLemmas"><ul>{''.join(self.lemmaSet(lemmaSet) for lemmaSet in section.lemmaSets)}</ul></div><!--hbLemmas-->'''
            sectionHtml += ''.join(self.paragraph(paragraph, section.images) for paragraph in section.paragraphs)
            placedImageIDs = {imageID for paragraph in section.paragraphs for imageID in re.findall(r'<Image Id="([^"]*)"', paragraph)}
            self.articleFigures.extend(self.figure(image) for imageID, image in section.images.items() if imageID not in placedImageIDs)
            if sectionHtml:
                heading = section.heading.rstrip(':') or section.content.capitalize()
                subheading = f'<h4>{escape(section.subheading)}</h4>' if section.subheading else ''
                html += f'<h3>{escape(heading)}</h3>{subheading}{sectionHtml}'
        figures = ''.join(figure for figure in self.articleFigures if figure)
        if figures:
            html = f'<div class="hbImages">{figures}</div><!--hbImages-->{html}'
        return f'<div class="hbArticle">{html}</div><!--hbArticle-->' if html else ''
# end of HandbookRenderer class


def articleFilename(key:str) -> str:
    return 'index.htm' if key == '0' else f'{key}.htm'


def imageOutputFilename(filename:str) -> str:
    return re.sub(r'\.(png|jpeg|jpg|gif|tif|tiff|webp)$', '.jpg', filename, flags=re.IGNORECASE)


def availableImageFilenames(state) -> dict[str,tuple[Path,str]]:
    """
    Return a dict of image filenames available in the UBS image zip files (filename -> (zip path, member name)).
    """
    available = {}
    imagesFolder = Path(getattr(state, 'UBS_IMAGES_FOLDER', '') or '.')
    for zipName in IMAGE_ZIP_FILES:
        zipPath = imagesFolder/zipName
        if not zipPath.is_file(): continue
        for memberName in zipfile.ZipFile(zipPath).namelist():
            if not memberName.endswith('/'): available.setdefault(memberName.rsplit('/',1)[-1], (zipPath, memberName))
    return available
# end of availableImageFilenames


def copyHandbookImages(images:dict[str,HandbookImage], available:dict[str,tuple[Path,str]], outputFolderPath:Path, state) -> int:
    """
    Resize the used images (once) into the image cache, then copy them into outputFolderPath.
    """
    from PIL import Image # Only needed here
    cacheFolder = Path(state.UBS_IMAGE_CACHE_FOLDER)
    cacheFolder.mkdir(parents=True, exist_ok=True)
    outputFolderPath.mkdir(parents=True, exist_ok=True)
    numCopied = 0
    for filename in sorted(images):
        cachedPath = cacheFolder/imageOutputFilename(filename)
        if not cachedPath.is_file():
            zipPath, memberName = available[filename]
            try:
                with zipfile.ZipFile(zipPath).open(memberName) as imageFile, Image.open(imageFile) as image:
                    image = image.convert('RGB')
                    image.thumbnail(MAX_IMAGE_SIZE)
                    temporaryPath = cachedPath.with_suffix('.tmp')
                    image.save(temporaryPath, 'JPEG', quality=JPEG_QUALITY, optimize=True)
                    temporaryPath.replace(cachedPath)
            except Exception as error:
                logging.error(f"UBS handbook image {filename} from {zipPath}: {error}"); continue
        shutil.copy2(cachedPath, outputFolderPath/cachedPath.name)
        numCopied += 1
    return numCopied
# end of copyHandbookImages


def handbookNavigationParagraph(level:int, handbook:str, entries:list[HandbookEntry], index:int) -> str:
    previousLink = f'<a title="Previous article" href="{quote(articleFilename(entries[index-1].key))}#Top">←</a> ' if index > 0 else ''
    nextLink = f' <a title="Next article" href="{quote(articleFilename(entries[index+1].key))}#Top">→</a>' if index+1 < len(entries) else ''
    otherHandbooks = ' '.join(f'<a href="../{other}/index.htm#Top">{escape(HANDBOOKS[other][1])}</a>' for other in HANDBOOKS if other != handbook)
    return f'''<p class="dNav">{previousLink}<a title="Go to {escape(HANDBOOKS[handbook][1])} contents" href="index.htm#Top">Contents</a>{nextLink} {otherHandbooks} <a title="Go to copyright and licence" href="{'../'*level}UBS/details.htm#Top">©</a></p>'''


def ubsHandbooksIndexHtml(level:int, state) -> str:
    """
    Return the heading and links for the UBS handbooks (for the main Reference index page), or ''.
    """
    handbooks = [handbook for handbook in HANDBOOKS if getattr(state, 'UBS_HANDBOOKS', {}).get(handbook)]
    if not handbooks: return ''
    links = ', '.join(f'<a href="{'../'*level}UBS/{handbook}/index.htm#Top">{escape(HANDBOOKS[handbook][1])}</a>' for handbook in handbooks)
    return f'''<h2>UBS Handbooks <small><a title="Show details" href="{'../'*level}UBS/details.htm#Top">©</a></small></h2>
<p class="note">Translator-oriented articles, with Hebrew and Greek terms, passages, and pictures: {links}.</p>
'''
# end of ubsHandbooksIndexHtml


def createUBSHandbookPages(level:int, outputFolderPath:Path, state) -> int:
    """
    Create the handbook pages in outputFolderPath (the UBS/ folder, which is at level-1).

    Returns the number of pages written.
    """
    handbooks = getattr(state, 'UBS_HANDBOOKS', None)
    if not handbooks: return 0
    available = availableImageFilenames(state)
    usedImages:dict[str,HandbookImage] = {}
    numPages = 0
    for handbook, entriesDict in handbooks.items():
        folderPath = outputFolderPath/handbook
        folderPath.mkdir(parents=True, exist_ok=True)
        entries = list(entriesDict.values())
        renderer = HandbookRenderer(level, handbook, state, set(available))
        handbookName = HANDBOOKS[handbook][1]
        for index, entry in enumerate(entries):
            title = handbookName if entry.key == '0' else f'{entry.title} ({handbookName} {entry.key})'
            articleHtml = renderer.article(entry)
            description = f'UBS handbook article on {entry.title.lower()} in the Bible, with Hebrew and Greek terms, passages, and translation advice.' \
                            if entry.key != '0' else f'Contents of the UBS handbook {handbookName}: articles with Hebrew and Greek terms, passages, and translation advice.'
            pageType = 'dictionaryIntro' if entry.key == '0' else 'dictionaryEntry'
            top = makeTop(level, None, pageType, None, state, metadata=(title, description))
            heading = f"{'TEST ' if state.TEST_MODE_FLAG else ''}{escape(title)}"
            if not articleHtml: articleHtml = '<div class="hbArticle"><p class="hbPara">(This article has no content yet.)</p></div><!--hbArticle-->'
            html = f'''{top}{handbookNavigationParagraph(level, handbook, entries, index).replace('<p class="dNav">', '<p id="Top" class="dNav">', 1)}
<h1>{heading}</h1>
{articleHtml}
{makeBottom(level, None, pageType)}'''
            assert checkHtml(f'UBS handbook {handbook} {entry.key}', html)
            filepath = folderPath/articleFilename(entry.key)
            assert not filepath.exists(), filepath
            filepath.write_text(html, encoding='utf-8')
            numPages += 1
        usedImages.update(renderer.usedImages)
    numImages = copyHandbookImages(usedImages, available, outputFolderPath/'img', state) if usedImages else 0
    logging.info(f"createUBSHandbookPages: wrote {numPages:,} handbook pages with {numImages:,} images")
    return numPages
# end of createUBSHandbookPages
