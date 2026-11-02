// SPDX-License-Identifier: CC0-1.0
// CHANGELOG: 2026-11-01 Add shareable, accessible Bible searches with source labels.
// 2026-11-02 Scroll completed searches to their results without interrupting edits.
// 2026-11-02 Clear previous result counts while a new search is loading.
// 2026-11-02 Label introductions consistently in context and copied references.
import {SearchEngine,parseReference,fetchJSON} from './searchCore.js';
const root=document.getElementById('bibleSearch');
const form=document.getElementById('searchForm');
const status=document.getElementById('searchStatus');
const results=document.getElementById('searchResults');
const control=name=>form.elements.namedItem(name);
const simple=['mode','query','book','group','match','exclude','range','field','language','order','lookup','morphology','numbering'];
let manifest,worker,fallback,id=0,page=0,lastResult,activeOptions,restoring=false;
const contexts=new Map();let contextCounter=0;
const element=(tag,text)=>{const node=document.createElement(tag);node.textContent=text;return node;};
function options(){
  const data=Object.fromEntries(simple.map(name=>[name,control(name).value]));
  data.versions=[...control('versions').selectedOptions].map(o=>o.value);
  data.accents=control('accents').checked;data.groupMatches=control('groupMatches').checked;data.page=page;return data;
}
function restore(){
  const query=new URLSearchParams(location.search);
  restoring=true;form.reset();restoring=false;
  for(const name of simple) if(query.has(name)) control(name).value=query.get(name);
  control('accents').checked=query.get('accents')==='1';
  control('groupMatches').checked=query.get('groupMatches')==='1';
  const versions=query.getAll('versions');
  const initial=versions.length ? versions : [query.get('version') || 'OET-RV'];
  for(const option of control('versions').options) option.selected=initial.includes(option.value) || initial.includes('OET') && ['OET-RV','OET-LV'].includes(option.value);
  if(!control('versions').selectedOptions.length && control('versions').options.length) control('versions').options[0].selected=true;
  page=Math.max(0,Number(query.get('page'))||0);
  document.getElementById('originalControls').hidden=control('mode').value!=='original';
  suggestions();
}
function save(){
  const data=options(), query=new URLSearchParams();
  for(const name of simple) if(data[name]) query.set(name,data[name]);
  for(const version of data.versions) query.append('versions',version);
  if(data.accents) query.set('accents','1');
  if(data.groupMatches) query.set('groupMatches','1');
  if(page) query.set('page',String(page));
  const url=`${location.pathname}?${query}`;
  if(url!==location.pathname+location.search) history.pushState({},'',url);
}
function link(label,href){
  const url=new URL(href,location.href);
  const base=new URL('.',location.href);
  if(url.origin!==base.origin || !url.pathname.startsWith(base.pathname)) throw new Error('Invalid result destination.');
  const node=element('a',label);node.href=url.href;return node;
}
function scrollToResults(){
  const request=id;
  requestAnimationFrame(()=>{
    // A finished older search must not interrupt somebody editing a new one.
    if(request!==id || !activeOptions || JSON.stringify(options())!==JSON.stringify(activeOptions))return;
    const area=document.getElementById('searchResultsArea') || status;
    area.tabIndex=-1;area.focus({preventScroll:true});
    area.scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
  });
}
function display(result){
  lastResult=result;results.replaceChildren();contexts.clear();
  status.textContent=`${result.count.toLocaleString()} ${activeOptions.groupMatches?'passage groups':activeOptions.mode==='reference'?'passage':'text field'} matches.`;
  if(activeOptions.groupMatches)status.textContent+=` ${result.sourceMatches.toLocaleString()} source matches.`;
  if(activeOptions.mode==='original')status.textContent+=` Annotation coverage: ${result.annotatedVersions.join(', ') || 'none'}.`;
  if(!result.count && activeOptions.mode==='reference')status.textContent+=' This passage is not indexed in the selected scope. Check this version’s numbering or choose another version.';
  const omissions=(manifest.omissions || []).filter(r=>activeOptions.versions.includes(r.version) && (!activeOptions.book || activeOptions.book===r.book));
  if(omissions.length)status.textContent+=` ${omissions.reduce((n,r)=>n+r.count,0)} source passages have unusable references and are unavailable in this search.`;
  const counts=document.getElementById('searchCounts');counts.replaceChildren();
  for(const [book,count] of Object.entries(result.byBook)){
    const button=element('button',`${manifest.partitions.find(p=>p.book===book)?.name || book}: ${count}`);button.type='button';
    button.onclick=()=>{control('book').value=book;page=0;submit();};counts.append(button,' ');
  }
  for(const group of result.results){
    const item=document.createElement('li');
    if(group.matches)item.append(element('p',`Exact mapped passage · ${group.matches.length} source matches`));
    for(const row of group.matches || [group]){
    const label=`${row.bookName || row.ref[0]} ${row.ref[1]==='-1'?'Introduction':`${row.ref[1]}:${row.ref[2]}`} · ${row.version}`;
    const heading=element('h2','');heading.append(link(label,row.links.context));item.append(heading);
    if(row.text){
      item.append(element('p',({body:'Bible text',note:'Note',heading:'Heading',transliteration:'Transliteration',modernised:'Modernised spelling',translation:'Supplementary translation',introduction:'Introduction'})[row.field] || row.field));
      const text=document.createElement('p');text.dir='auto';let cursor=0;
      for(const [start,end] of row.highlights){
        if(start<cursor)continue;
        text.append(document.createTextNode(row.text.slice(cursor,start)),element('mark',row.text.slice(start,end)));cursor=end;
      }
      text.append(document.createTextNode(row.text.slice(cursor)));item.append(text);
    }
    for(const word of row.matchedAnnotations || []){
      const detail=element('p',`${word.form} · ${word.lemma} · ${word.strong.join(', ')} · ${word.morphology} (${word.source})`);
      detail.dir='auto';item.append(detail);
    }
    const links=element('p','');
    for(const [kind,label] of [['context','Read in context'],['parallel','Parallel versions'],['interlinear','Interlinear']]){
      if(row.links[kind]){if(links.childNodes.length)links.append(' · ');links.append(link(label,row.links[kind]));}
    }
    item.append(links);
    if(row.contextId){
      const details=document.createElement('details');details.append(element('summary','Show nearby verses'));
      details.addEventListener('toggle',async()=>{
        if(!details.open || details.dataset.loaded)return;
        details.dataset.loaded='1';const content=element('div','Loading context…');details.append(content);
        const contextId=++contextCounter;contexts.set(contextId,content);
        if(worker)worker.postMessage({type:'context',contextId,reference:row.contextId});
        else try{showContext(content,await fallback.context(row.contextId));}catch(error){content.textContent=error.message;}
      });item.append(details);
    }
    }results.append(item);
  }
  document.getElementById('searchPrevious').disabled=page===0;
  document.getElementById('searchNext').disabled=page+1>=result.pages;
  document.getElementById('searchPageNumber').textContent=result.pages ? `Page ${page+1} of ${result.pages}` : '';
  scrollToResults();
}
function showContext(node,rows){
  node.replaceChildren();
  if(!rows.length){node.textContent='No adjacent Bible text is available here.';return;}
  for(const row of rows){const p=element('p',`${row.ref[1]==='-1'?'Introduction':`${row.ref[1]}:${row.ref[2]}`} ${row.text}`);p.dir='auto';node.append(p);}
}
async function submit(push=true){
  if(!manifest)return;
  const data=options();if(!data.query.trim()){clearResults();return;}
  if(!data.versions.length){status.textContent='Choose at least one version.';return;}
  if(push)save();
  results.replaceChildren();contexts.clear();lastResult=null;
  document.getElementById('searchCounts').replaceChildren();
  document.getElementById('searchPageNumber').textContent='';
  activeOptions=data;
  document.getElementById('searchPrevious').disabled=document.getElementById('searchNext').disabled=true;
  document.getElementById('searchScope').textContent=`${data.mode==='reference'?`Passage lookup: ${data.query}`:data.match==='phrase'?'Exact phrase':data.match==='any'?'Any word':'All words in one verse or field'} · ${data.versions.join(', ')} · ${(data.mode!=='reference' && data.range) || data.book || data.group || 'All available books'}${data.field && data.mode!=='reference'?` · ${data.field}`:''}`;
  status.textContent='Searching…';const request=++id;
  if(worker)worker.postMessage({id:request,options:data});
  else if(data.mode==='reference'){
    try{const result=await fallback.search(data);if(id===request)display(result);}catch(error){if(id===request){status.textContent=error.message;scrollToResults();}}
  }else {status.textContent='Text search needs browser worker support. Passage lookup is still available.';scrollToResults();}
}
function clearResults(){
  id++;worker?.postMessage({type:'cancel'});results.replaceChildren();contexts.clear();lastResult=null;
  document.getElementById('searchScope').textContent='';document.getElementById('searchCounts').replaceChildren();
  document.getElementById('searchPageNumber').textContent='';
  document.getElementById('searchPrevious').disabled=document.getElementById('searchNext').disabled=true;
  status.textContent='Choose versions and enter words or a reference.';
}
function suggestions(){
  const holder=document.getElementById('referenceSuggestion');holder.replaceChildren();
  if(!manifest || control('mode').value==='reference')return;
  try{
    parseReference(control('query').value,manifest.books || manifest.partitions);
    const button=element('button',`Look up passage “${control('query').value}”`);button.type='button';
    button.onclick=()=>{control('mode').value='reference';page=0;submit();};holder.append(button);
  }catch(_){/* Ordinary text remains an ordinary text query. */}
}
form.addEventListener('submit',event=>{event.preventDefault();page=0;submit();});
form.addEventListener('reset',()=>{if(restoring)return;page=0;clearResults();setTimeout(()=>{
  if(!control('versions').selectedOptions.length && control('versions').options.length)control('versions').options[0].selected=true;
  document.getElementById('originalControls').hidden=control('mode').value!=='original';suggestions();
  history.pushState({},'',location.pathname);
},0);});
control('query').addEventListener('input',suggestions);
control('mode').addEventListener('change',()=>{document.getElementById('originalControls').hidden=control('mode').value!=='original';suggestions();});
document.getElementById('bothOET').onclick=()=>{for(const o of control('versions').options)o.selected=['OET-RV','OET-LV'].includes(o.value);};
document.getElementById('allVersions').onclick=()=>{for(const o of control('versions').options)o.selected=true;};
document.getElementById('searchPrevious').onclick=()=>{page--;submit();};
document.getElementById('searchNext').onclick=()=>{page++;submit();};
document.getElementById('copyReferences').onclick=async()=>{
  if(!lastResult)return;
  const text=[...new Set(lastResult.results.flatMap(r=>r.matches || [r]).map(r=>`${r.version} ${r.bookName || r.ref[0]} ${r.ref[1]==='-1'?'Introduction':`${r.ref[1]}:${r.ref[2]}`}`))].join('\n');
  try{await navigator.clipboard.writeText(text);status.textContent='Displayed references copied.';}
  catch(_){status.textContent=text;}
};
window.addEventListener('popstate',()=>{restore();submit(false);});
try{
  manifest=await fetchJSON(root.dataset.manifest);
  fallback=new SearchEngine(manifest,async name=>{
    if(!/^[a-z]+-[a-f0-9]{24}\.bin$/.test(name))throw new Error('Invalid search asset.');
    return fetchJSON(new URL(`search/${name}`,location.href));
  });
  for(const version of manifest.versions){const option=element('option',`${version.id} — ${version.name}`);option.value=version.id;option.defaultSelected=version.id==='OET-RV';control('versions').append(option);}
  const books=new Map();for(const p of manifest.partitions)if(!books.has(p.book))books.set(p.book,p);
  for(const p of [...books.values()].sort((a,b)=>a.order-b.order)){const option=element('option',p.name);option.value=p.book;control('book').append(option);}
  const fromBook=books.get(new URLSearchParams(location.search).get('fromBook'));
  if(fromBook){
    const button=element('button',`Limit to ${fromBook.name}`);button.type='button';
    button.onclick=()=>{control('book').value=fromBook.book;page=0;submit();};document.getElementById('searchOrigin').append(button);
  }
  for(const alias of [...new Set(manifest.partitions.flatMap(p=>p.aliases))].sort()){
    const option=document.createElement('option');option.value=alias;document.getElementById('searchBookSuggestions').append(option);
  }
  for(const language of [...new Set(manifest.partitions.map(p=>p.language))].sort()){const option=element('option',language);option.value=language;control('language').append(option);}
  try{
    worker=new Worker(new URL('./searchWorker.js',import.meta.url),{type:'module'});
    worker.onmessage=({data})=>{
      if(data.contextId){const node=contexts.get(data.contextId);if(node){if(data.error)node.textContent=data.error;else showContext(node,data.context);}return;}
      if(data.id!==id)return;if(data.error){status.textContent=data.error;scrollToResults();return;}
      if(data.progress)status.textContent=`Searching ${data.progress.done} of ${data.progress.total} book/version indexes…`;if(data.result)display(data.result);
    };
    worker.onerror=()=>{worker.terminate();worker=null;status.textContent='The search worker could not start. Passage lookup remains available.';};
    worker.postMessage({type:'init',manifest,base:new URL('search/',location.href).href});
  }catch(_){worker=null;}
  restore();status.textContent=manifest.test?'This build contains a limited selection of books and versions.':'Choose versions and enter words or a reference.';
  if(control('query').value)submit(false);
}catch(error){status.textContent=error.message;}
