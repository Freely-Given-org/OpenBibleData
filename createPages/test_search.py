#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Native search acceptance checks using actual BOS entries and browser code.

CHANGELOG:
    2026-11-01 Cover source boundaries, Unicode, references and static index queries.
    2026-11-02 Cover source editions without a declared language.
"""
import json
import gzip
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from searchText import tokens, normalize, plainHtml, usfmText
from searchRecords import PublishedPages, exportBook, recordLinks
from searchIndex import buildPartition, buildSearch, publishSearch, validateSearch, jsonBytes, FORMAT_VERSION


def makeFixture(root):
    records = [
        dict(key='A:1',version='A',ref=['JHN','3','16'],language='en',fields={'body':'God loved the world.', 'note':'A note about mercy.'}),
        dict(key='A:2',version='A',ref=['JHN','3','17'],language='en',fields={'body':'The world was made through him.'}),
        dict(key='A:3',version='A',ref=['JHN','3','18-19'],language='en',fields={'body':'To be or not to be.'}),
        dict(key='B:1',version='B',ref=['JHN','3','16'],language='en',fields={'body':'He showed mercy.'}),
        dict(key='G:1',version='G',ref=['JHN','1','1'],language='grk',fields={'body':'Ἐν ἀρχῇ ἦν ὁ λόγος.', 'transliteration':'En archē ēn ho logos.'},
             annotations=[dict(form='λόγος',lemma='λόγος',strong=['G3056'],morphology='N-NSM',source='Fixture'),
                          dict(form='ἦν',lemma='εἰμί',strong=['G1510'],morphology='V-IAI-3S',source='Fixture')]),
        dict(key='H:1',version='H',ref=['PSA','1','1'],language='heb',fields={'body':'בְּרֵאשִׁית בָּרָא'}),
    ]
    partitions = []
    for version in ('A','B','G','H'):
        rows = [dict(r,links={'context':f'{version}/byC/{r["ref"][0]}_C{r["ref"][1]}.htm#C{r["ref"][1]}V{r["ref"][2].split("-")[0]}'})
                for r in records if r['version']==version]
        for row in rows:
            if row['ref']==['JHN','3','16']:
                row.update(mapping='exact',mapped=[['JHN','3','16',None]])
        book = rows[0]['ref'][0]
        partition=buildPartition(rows,root,version=version,book=book,aliases=['John','Jn','JHN'] if book=='JHN' else ['Psalms','Psalm','PSA'],order=1)
        partition['traditionalOrder']=1
        partitions.append(partition)
    manifest=dict(format=FORMAT_VERSION,buckets=32,versions=[dict(id=v,name=v) for v in ('A','B','G','H')],partitions=partitions,test=True)
    (root/'manifest.json').write_bytes(jsonBytes(manifest))
    return manifest


class SearchTextTests(unittest.TestCase):
    def test_words_keep_combining_marks_and_browser_offsets(self):
        self.assertEqual(tokens('😀 λόγος'), [('λογοσ','λόγοσ',3,8)])
        self.assertEqual(normalize('בְּרֵאשִׁית'),'בראשית')
        self.assertEqual(tokens('to be or not to be')[0][0],'to')
        self.assertEqual(tokens('בְּ\u2060רֵאשִׁ֖ית')[0][0],'בראשית')

    def test_html_parser_keeps_entities_and_ignores_script(self):
        self.assertEqual(plainHtml('<p>A &amp; B<script>secret</script></p><p>Next</p>'),'A & B Next')

    def test_selected_verses_keep_notes_separate(self):
        fields=usfmText(r'God \add made\add* earth.\f + \fr 1:1 \ft A note.\f*')
        self.assertEqual(fields,dict(body='God made earth.',note='A note.'))

    def test_stdlib_parser_does_not_replace_site_html_module(self):
        import html
        self.assertTrue(hasattr(html,'checkHtml'))


class SourceRecordTests(unittest.TestCase):
    def test_real_bos_entries_keep_bridges_and_notes(self):
        from BibleOrgSys.Formats.ESFMBible import ESFMBible
        with TemporaryDirectory() as directory:
            root=Path(directory); source=root/'source';source.mkdir()
            (source/'MRK.esfm').write_text('\\id MRK\n\\c 1\n\\p\n\\v 1 God¦123 made earth.\\f + \\fr 1:1 \\ft A note.\\f*\n\\s1 Heading\n\\v 2-3 One bridge.\n')
            bible=ESFMBible(source,givenAbbreviation='TST',versification='eng');bible.loadBooks()
            page=root/'TST/byC/MRK_C1.htm';page.parent.mkdir(parents=True)
            page.write_text('<p id="Top"></p><p id="C1V1">God made earth.</p><p id="C1V2">One bridge.</p>')
            state=SimpleNamespace(BibleLanguages={'TST':None},BibleVersifications={'TST':'eng'},navigationVersification='eng')
            with PublishedPages(root) as pages:
                records=list(exportBook('TST','MRK',bible,state,pages))
            self.assertEqual([r['ref'][2] for r in records],['1','2-3'])
            self.assertEqual(records[0]['language'],'und')
            self.assertEqual(records[0]['fields']['body'],'God made earth.')
            self.assertEqual(records[0]['fields']['note'],'A note.')
            self.assertEqual(records[1]['fields']['heading'],'Heading')
            self.assertEqual(records[1]['fields']['body'],'One bridge.')

    def test_unpublished_destinations_are_not_exposed(self):
        with TemporaryDirectory() as directory:
            pages=PublishedPages(directory)
            self.assertFalse(pages.available('A/byC/JHN_C1.htm#C1V1'))
            for bad in ('https://example.com/','../outside.htm','%2e%2e/outside.htm'):
                with self.assertRaises(ValueError):pages.available(bad)
            pages.close()

    def test_book_aliases_include_bos_and_oet(self):
        from searchReferences import bookAliases
        self.assertIn('Jn',bookAliases('JHN'))

    def test_derived_fields_belong_to_their_source_and_worker(self):
        from searchSupplement import captureSupplement,supplementFiles,supplementRecords
        with TemporaryDirectory() as directory:
            root=Path(directory)
            state=SimpleNamespace(CREATE_SEARCH_INDEX_FLAG=True,TEMP_BUILD_FOLDER=root,BibleLanguages={'A':'en'})
            path=root/'par/JHN/C3V16.htm';path.parent.mkdir(parents=True);path.write_text('<p id="A">text</p><p id="UTN">note</p>')
            captureSupplement(state,'A',('JHN','3','16'),'<p class="A_mod">Modernised <i>text</i>.</p><p>unrelated</p>','par/JHN/C3V16.htm#A')
            captureSupplement(state,'UTN',('JHN','3','16'),'<p>A note.</p>','par/JHN/C3V16.htm#UTN',field='note')
            with PublishedPages(root) as pages:
                files=supplementFiles(root)
                self.assertEqual(supplementRecords(files['A','JHN'],pages)['A:JHN:3:16']['fields'],{'modernised':'Modernised text.'})
                self.assertEqual(supplementRecords(files['UTN','JHN'],pages)['UTN:JHN:3:16']['fields'],{'note':'A note.'})

    def test_original_word_attributes_keep_strong_suffixes(self):
        from searchLexical import entryAnnotations
        extra=SimpleNamespace(getType=lambda:'ww',getFullText=lambda:'word|lemma="lemma" strong="H0123a" x-morph="He,Ncmsa"')
        words=entryAnnotations([SimpleNamespace(getMarker=lambda:'v~',getExtras=lambda:[extra])])
        self.assertEqual(words[0]['strong'],['H123a'])
        self.assertEqual(words[0]['morphology'],'He,Ncmsa')

    def test_malformed_source_references_are_reported_without_guessing(self):
        with TemporaryDirectory() as directory, PublishedPages(directory) as pages:
            state=SimpleNamespace()
            with self.assertLogs(level='WARNING'):
                records=list(exportBook('ULT','CH1',{('CH1','7',r'\add'):'8 Example.'},state,pages))
            self.assertEqual(records,[])
            self.assertEqual(pages.coverage['ULT','CH1']['malformedReferences'],1)
            self.assertEqual(pages.issues[0]['reference'],['CH1','7',r'\add'])

    def test_parallel_only_selected_verse_and_renumbered_passage(self):
        from settings import State
        with TemporaryDirectory() as directory:
            root=Path(directory)
            selected=root/'par/JHN/C3V16.htm';selected.parent.mkdir(parents=True);selected.write_text('<p id="A">Selected text.</p>')
            mapped=root/'par/MAL/C4V1.htm';mapped.parent.mkdir(parents=True);mapped.write_text('<p id="OET-LV">Coming.</p>')
            native=root/'OET-LV/byC/MAL_C3.htm';native.parent.mkdir(parents=True);native.write_text('<p id="C3V19">Coming.</p>')
            state=State();state.BibleVersifications=dict(state.BibleVersifications,A='eng')
            with PublishedPages(root) as pages:
                records=list(exportBook('A','JHN',{('JHN','3','16'):'Selected text.'},state,pages))
                self.assertEqual(records[0]['links']['context'],'par/JHN/C3V16.htm#A')
                links,mapped,status=recordLinks('OET-LV',('MAL','3','19'),state,pages)
                self.assertEqual(links['context'],'OET-LV/byC/MAL_C3.htm#C3V19')
                self.assertEqual(links['parallel'],'par/MAL/C4V1.htm#OET-LV')
                self.assertEqual(status,'exact')
                self.assertEqual(tuple(mapped[0][:3]),('MAL','4','1'))


class SearchIndexTests(unittest.TestCase):
    def test_repeat_build_is_identical_and_browser_acceptance_passes(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            makeFixture(root)
            first={p.name:p.read_bytes() for p in root.iterdir()}
            makeFixture(root)
            self.assertEqual(first,{p.name:p.read_bytes() for p in root.iterdir()})
            env=dict(os.environ,OBD_SEARCH_FIXTURE=str(root))
            result=subprocess.run(['node','--test','test_search.mjs'],env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_cache_reuse_changed_source_and_corrupt_artifact(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            records=[dict(key='A:JHN:1:1',version='A',ref=['JHN','1','1'],language='en',fields={'body':'One word.'},links={'context':'A.htm#v1'})]
            first=buildPartition(records,root/'a',version='A',book='JHN')
            second=buildPartition(records,root/'b',version='A',book='JHN',cached=first,cacheRoot=root/'a')
            self.assertEqual(first,second)
            (root/'a'/first['catalogue']).write_bytes(b'corrupted')
            repaired=buildPartition(records,root/'c',version='A',book='JHN',cached=first,cacheRoot=root/'a')
            self.assertEqual(json.loads(gzip.decompress((root/'c'/repaired['catalogue']).read_bytes()))['references'][0]['ref'],['JHN','1','1'])
            records[0]['fields']['body']='A changed word.'
            changed=buildPartition(records,root/'d',version='A',book='JHN',cached=first,cacheRoot=root/'b')
            self.assertNotEqual(first['inputHash'],changed['inputHash'])
            self.assertNotEqual(first['blocks'],changed['blocks'])

    def test_publication_preserves_old_generation_on_failure(self):
        from searchPage import searchBody
        with TemporaryDirectory() as directory:
            root=Path(directory);destination=root/'published';destination.mkdir()
            def build(name,text):
                staging=root/name;staging.mkdir()
                page=staging/'A/byC/JHN_C3.htm';page.parent.mkdir(parents=True);page.write_text('<p id="C3V16">'+text+'</p>')
                state=SimpleNamespace(BibleVersions=['A'],BibleNames={'A':'Version A'},BibleLanguages={'A':'en'},BibleVersifications={'A':'eng'},navigationVersification='eng',BibleSourceBookLayouts={},
                    booksToLoad={'A':['ALL']},preloadedBibles={'A':{('JHN','3','16'):text}},OET_BOOK_ORDER=['JHN'],TEST_MODE_FLAG=True,REUSE_EXISTING_WORD_PAGES_FLAG=False,DESTINATION_FOLDER=destination)
                buildSearch(staging,state)
                (staging/'Search.htm').write_text(f'<script type="module" src="{state.searchClient}search.js"></script>'+searchBody(state.searchManifest))
                return staging
            old=build('old','Old passage.')
            (old/'search/unselected-source.bin').write_bytes(b'Excluded content')
            publishSearch(old,destination)
            self.assertFalse((destination/'search/unselected-source.bin').exists())
            oldPage=(destination/'Search.htm').read_bytes();oldManifest=validateSearch(destination)
            new=build('new','New passage.')
            import os
            replace=os.replace
            def fail(source,target):
                if str(target).endswith('Search.htm'):raise OSError('Interrupted before the page switch')
                return replace(source,target)
            with patch('os.replace',side_effect=fail):
                with self.assertRaisesRegex(OSError,'Interrupted'):publishSearch(new,destination)
            self.assertEqual((destination/'Search.htm').read_bytes(),oldPage)
            # The old page pins its manifest; changing the discovery pointer cannot break it.
            for partition in oldManifest['partitions']:
                self.assertTrue((destination/'search'/partition['catalogue']).is_file())
            publishSearch(new,destination);validateSearch(destination)
            publishSearch(old,destination);self.assertEqual((destination/'Search.htm').read_bytes(),oldPage)
            (destination/'search'/oldManifest['partitions'][0]['catalogue']).write_bytes(b'broken')
            publishSearch(old,destination);validateSearch(destination)
            corrupt=build('corrupt','Incomplete passage.')
            manifest=json.loads((corrupt/'search/manifest.json').read_text())
            (corrupt/'search'/manifest['partitions'][0]['catalogue']).unlink()
            with self.assertRaisesRegex(ValueError,'Missing or corrupted'):publishSearch(corrupt,destination)
            self.assertEqual((destination/'Search.htm').read_bytes(),oldPage)


if __name__=='__main__':unittest.main()
