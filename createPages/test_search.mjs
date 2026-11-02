// SPDX-License-Identifier: CC0-1.0
// CHANGELOG: 2026-11-01 Exercise Python-produced indexes using the browser engine.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {gunzipSync} from 'node:zlib';
import {SearchEngine,tokens,parseReference,within} from './searchCore.js';
const root=process.env.OBD_SEARCH_FIXTURE;
const manifest=JSON.parse(await fs.readFile(`${root}/manifest.json`));
const requests=[];
const load=async name=>{requests.push(name);return JSON.parse(gunzipSync(await fs.readFile(`${root}/${name}`)));};
const engine=new SearchEngine(manifest,load);
const search=(query,options={})=>engine.search({query,versions:['A'],mode:'text',match:'all',...options});
test('word and phrase acceptance',async()=>{
  assert.equal((await search('world')).count,2);
  assert.equal((await search('wor')).count,0);
  assert.equal((await search('constructor')).count,0);
  assert.equal((await search('world loved')).count,1);
  assert.equal((await search('world loved',{match:'phrase'})).count,0);
  assert.equal((await search('loved the world',{match:'phrase'})).count,1);
  assert.equal((await search('to be',{match:'phrase'})).results[0].highlights.length,4);
  assert.equal((await search('world',{exclude:'God'})).count,1);
});
test('versions and fields never combine into a false match',async()=>{
  assert.equal((await search('God mercy',{versions:['A','B']})).count,0);
  assert.equal((await search('mercy')).count,0);
  assert.equal((await search('mercy',{mode:'study'})).count,1);
  assert.equal((await search('God mercy',{match:'any',versions:['A','B']})).count,2);
});
test('Unicode matching and offsets agree with the builder',async()=>{
  assert.deepEqual(tokens('😀 λόγος'),[['λογοσ','λόγοσ',3,8]]);
  assert.equal(tokens('בְּ\u2060רֵאשִׁ֖ית')[0][0],'בראשית');
  assert.equal((await search('λογος',{versions:['G']})).count,1);
  assert.equal((await search('λογος',{versions:['G'],accents:true})).count,0);
  assert.equal((await search('λόγος',{versions:['G'],accents:true})).count,1);
  assert.equal((await search('logos',{versions:['G']})).count,1);
  assert.equal((await search('בראשית',{versions:['H']})).count,1);
});
test('reference aliases and verse bridges',async()=>{
  assert.equal((await search('Jn 3:16-17',{mode:'reference'})).count,2);
  assert.equal((await search('John 3.19',{mode:'reference'})).results[0].ref[2],'18-19');
  assert.equal((await search('John 3',{mode:'reference'})).count,3);
  assert.equal((await search('world',{range:'John 3:17'})).count,1);
  assert.throws(()=>parseReference('John 3:19-16',manifest.partitions),/end/);
  assert(within(['JHN','3','16a'],parseReference('Jn 3:16',manifest.partitions)));
  assert(!within(['JHN','3','16b'],parseReference('Jn 3:16a',manifest.partitions)));
  assert(within(['JHN','3','16b'],parseReference('Jn 3:16a-17',manifest.partitions)));
  const one=[{book:'JDE',aliases:['Jude'],singleChapter:true}];
  assert(within(['JDE','1','5'],parseReference('Jude 5',one)));
  const withThirdJohn=[...manifest.partitions,{book:'JN3',aliases:['JN3','3 John','3Jn'],singleChapter:true}];
  for(const query of ['Jn 3:16','Jn3.16','John 3:16','Jn. 3:16'])assert.equal(parseReference(query,withThirdJohn).book,'JHN',query);
  assert.equal(parseReference('3John 5',withThirdJohn).book,'JN3');
  const selection=parseReference('Jn 3:16; 18-19; Psalms 1:1',manifest.partitions);
  assert(within(['JHN','3','18'],selection));assert(!within(['JHN','3','17'],selection));assert(within(['PSA','1','1'],selection));
  assert.equal((await search('John 3:16; Psalm 1:1',{mode:'reference',versions:['A','H']})).count,2);
});
test('original word filters stay on the same annotated word',async()=>{
  assert.equal((await search('λογος',{versions:['G'],mode:'original'})).count,1);
  assert.equal((await search('G03056',{versions:['G'],mode:'original',lookup:'strong'})).count,1);
  assert.equal((await search('λογος',{versions:['G'],mode:'original',morphology:'N-NSM'})).count,1);
  assert.equal((await search('λογος',{versions:['G'],mode:'original',morphology:'V-IAI-3S'})).count,0);
  await assert.rejects(()=>search('λόγος',{mode:'original'}),/no original-word annotations/);
});
test('result blocks are fetched only for displayed results',async()=>{
  const isolated=new SearchEngine(manifest,load);
  requests.length=0;
  assert.equal((await isolated.search({query:'world',versions:['A'],page:5})).results.length,0);
  assert(!requests.some(name=>name.startsWith('records-')));
});
test('failed downloads do not appear as empty results',async()=>{
  const broken=new SearchEngine(manifest,()=>{throw new Error('offline');});
  await assert.rejects(()=>broken.search({query:'world'}),/offline/);
  const controller=new AbortController();controller.abort();
  await assert.rejects(()=>engine.search({query:'world'},controller.signal),{name:'AbortError'});
});
test('pagination reuses the completed query and context stays in one source',async()=>{
  const isolated=new SearchEngine(manifest,load);
  await isolated.search({query:'world',versions:['A'],page:0});requests.length=0;
  await isolated.search({query:'world',versions:['A'],page:1});assert.equal(requests.length,0);
  const rows=await isolated.context({version:'A',book:'JHN',reference:0});
  assert.deepEqual(rows.map(r=>r.ref[2]),['16','17']);assert(rows.every(r=>r.version==='A'));
});
test('only complete exact mappings group sources together',async()=>{
  const result=await search('God mercy',{versions:['A','B'],match:'any',groupMatches:true});
  assert.equal(result.count,1);assert.equal(result.sourceMatches,2);
  assert.deepEqual(result.results[0].matches.map(r=>r.version),['A','B']);
  assert.equal((await search('mercy',{versions:['A','B'],groupMatches:true})).count,1);
});
