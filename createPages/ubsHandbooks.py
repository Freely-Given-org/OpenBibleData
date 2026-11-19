#!/usr/bin/env -S uv run
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""
Load the UBS 'flora, fauna and realia' handbooks (from our OET-adapted copies)
    so that they can be rendered as pages beside the other dictionaries.

    Fauna: Animals in the Bible (adapted from All Creatures Great and Small, Edward R. Hope)
    Flora: Plants and Trees in the Bible
    Realia: Objects in the Bible

Each handbook is an XML file of <ThemLex_Entry Key="2.1"> articles, with sections of
    paragraphs (containing inline <i>, <b>, <u>, <sup>, <s>UBS scripture codes</s>,
    <l target="FLORA:3">links</l>, <a>bibliography abbreviations</a>, and <Image Id="…"/> placements),
    Hebrew/Greek lemma sets with scripture references, and image metadata.

CHANGELOG:
    2026-11-19 First version
"""
from dataclasses import dataclass, field
from pathlib import Path
import logging
import re
from xml.etree import ElementTree


HANDBOOKS = { # Our abbreviation: (filename, display name, MARBLE/UBS link prefix)
    'Fauna': ('FAUNA_1.1_en.xml', 'Animals in the Bible'),
    'Flora': ('FLORA_1.1_en.xml', 'Plants and Trees in the Bible'),
    'Realia': ('REALIA_1.1_en.xml', 'Objects in the Bible'),
    }


@dataclass
class HandbookLemmaSet:
    language:str # 'Hebrew', 'Aramaic', or 'Greek'
    lemma:str
    transliteration:str
    references:list[str] # UBS reference codes, e.g., '00103003700018' or 'H00100402101000'


@dataclass
class HandbookImage:
    imageID:str
    collection:str # e.g., 'WEB', 'PRITZ', 'UBS', 'OPEN-AI', 'FAUNA'
    filename:str
    copyright:str
    caption:str


@dataclass
class HandbookSection:
    content:str # e.g., 'references', 'discussion', 'translation'
    heading:str
    subheading:str
    lemmaSets:list[HandbookLemmaSet]
    paragraphs:list[str] # Inner XML of each <Paragraph> (with the source's inline markup)
    images:dict[str,HandbookImage]


@dataclass
class HandbookEntry:
    handbook:str # 'Fauna', 'Flora', or 'Realia'
    key:str # e.g., '2.1'
    title:str
    index:list[tuple[str,str]] # (target key, description) for sub-articles
    sections:list[HandbookSection] = field(default_factory=list)

    @property
    def images(self) -> dict[str,HandbookImage]:
        return {imageID:image for section in self.sections for imageID,image in section.images.items()}

    def referenceCodes(self) -> list[str]:
        """
        All the UBS scripture reference codes in this article (from lemma sets and <s> elements).
        """
        codes = [code for section in self.sections for lemmaSet in section.lemmaSets for code in lemmaSet.references]
        for section in self.sections:
            for paragraph in section.paragraphs:
                for payload in re.findall(r'<s>([^<]*)</s>', paragraph):
                    codes.extend( payload.split() )
        return codes
# end of HandbookEntry class


def innerXML(element:ElementTree.Element) -> str:
    """
    Return the inner XML of an element (keeping its inline markup), with entities escaped.
    """
    text = ElementTree.tostring(element, encoding='unicode', short_empty_elements=True)
    return re.sub(r'^<[^>]*>|</[^>]*>\s*$', '', text.strip(), count=2) if not text.endswith('/>') else ''
# end of innerXML


def textOf(element:ElementTree.Element|None) -> str:
    return (''.join(element.itertext()).strip()) if element is not None else ''


def loadHandbook(handbook:str, folderpath) -> dict[str,HandbookEntry]:
    """
    Load one handbook XML file.

    Returns a dict (in source order) with entry keys (e.g., '2.1') as keys.
    """
    filename = HANDBOOKS[handbook][0]
    filepath = Path(folderpath, filename)
    tree = ElementTree.parse(filepath)
    entries:dict[str,HandbookEntry] = {}
    for entryElement in tree.getroot().iterfind('ThemLex_Entry'):
        key = entryElement.get('Key', '').strip()
        if not key:
            logging.warning(f"loadHandbook: {handbook} entry without a key in {filepath}"); continue
        if key in entries:
            logging.warning(f"loadHandbook: duplicate {handbook} entry key {key!r} in {filepath}"); continue
        index = []
        for indexItem in entryElement.iterfind('Index/IndexItem'):
            if indexItem.get('Target'): # <IndexItem Number="2.1" Description="Weapon" Target="REALIA:2.1" />
                index.append( (indexItem.get('Target').split(':',1)[-1], f"{indexItem.get('Number','')} {indexItem.get('Description','')}".strip()) )
            elif (linkElement:=indexItem.find('l')) is not None: # <IndexItem><l target="FAUNA:1">1 Animals, General</l></IndexItem>
                index.append( (linkElement.get('target','').split(':',1)[-1], textOf(linkElement)) )
        entry = HandbookEntry(handbook, key, textOf(entryElement.find('Title')), index)
        for sectionElement in entryElement.iterfind('Sections/Section'):
            lemmaSets = [HandbookLemmaSet(languageSet.get('Language',''), textOf(languageSet.find('Lemma')),
                                            textOf(languageSet.find('Transliteration')),
                                            [textOf(reference) for reference in languageSet.iterfind('References/Reference') if textOf(reference)])
                            for languageSet in sectionElement.iterfind('LanguageSets/LanguageSet')]
            paragraphs = [innerXML(paragraph) for paragraph in sectionElement.iterfind('Paragraphs/Paragraph')]
            images = {}
            for imageElement in sectionElement.iter('BibleImage'):
                imageID = imageElement.get('Id','')
                images[imageID] = HandbookImage(imageID, textOf(imageElement.find('Collection')), textOf(imageElement.find('FileName')),
                                                textOf(imageElement.find('Copyright')), textOf(imageElement.find('Caption')))
            entry.sections.append( HandbookSection(sectionElement.get('Content',''), textOf(sectionElement.find('Heading')),
                                                    textOf(sectionElement.find('SubHeading')), lemmaSets, paragraphs, images) )
        entries[key] = entry
    return entries
# end of loadHandbook


def loadHandbooks(folderpath) -> dict[str,dict[str,HandbookEntry]]:
    """
    Load all three handbooks from the flora-fauna-realia/XML folder.
    """
    return {handbook:loadHandbook(handbook, folderpath) for handbook in HANDBOOKS}
# end of loadHandbooks


def handbookKeyFromLink(link:str) -> tuple[str,str]|None:
    """
    Convert a link target like 'FAUNA:3', 'Realia:1.5.2.1' (MARBLE ThematicLinks), or 'FLORA:2.1'
        to (handbook, key), or None if it's not a handbook link.
    """
    prefix, _colon, key = link.partition(':')
    for handbook in HANDBOOKS:
        if prefix.lower() == handbook.lower() and key:
            return handbook, key
    return None
# end of handbookKeyFromLink
