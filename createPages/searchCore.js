// SPDX-License-Identifier: CC0-1.0
// CHANGELOG: 2026-11-01 Search independently indexed native passages in a worker.
export const FORMAT = 3;
export async function fetchJSON(url, signal) {
  const response=await fetch(url,{signal});
  if(!response.ok) throw new Error('Search data could not be loaded. Please retry.');
  if(new URL(url,globalThis.location?.href || 'http://localhost/').pathname.endsWith('.bin')) {
    if(!globalThis.DecompressionStream) throw new Error('This browser cannot read the compressed search data. Please use a newer browser.');
    return new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).json();
  }
  return response.json();
}
export function normalize(text, accents = false) {
  let value = text.normalize('NFD').toLowerCase().replaceAll('ς', 'σ').replaceAll('\u2060','');
  if (!accents) value = value.replace(/\p{M}/gu, '');
  return value.normalize('NFC');
}
export function tokens(text) {
  return [...text.matchAll(/[\p{L}\p{N}][\p{L}\p{N}\p{M}\u2060]*/gu)].map(m =>
    [normalize(m[0]), normalize(m[0], true), m.index, m.index + m[0].length]);
}
export function bucket(term, count = 32) {
  let value = 2166136261;
  for (const byte of new TextEncoder().encode(term)) value = Math.imul(value ^ byte, 16777619) >>> 0;
  return value % count;
}
const aliasKey = value => normalize(value).replace(/(?<=\p{L})\./gu,'').replace(/[_–—]/g,' ')
  .replace(/\s+/g,' ').trim().replace(/^([1-4])\s*(?=\p{L})/u,'$1 ');
const aliasCatalogues=new WeakMap();
const point = (chapter, verse) => {
  const m = /^(\d+)([a-z]*)$/.exec(String(verse));
  if (!m) throw new Error(`Invalid verse: ${verse}`);
  return [Number(chapter), Number(m[1]), m[2]];
};
const compare = (a,b) => a[0]-b[0] || a[1]-b[1] || a[2].localeCompare(b[2]);

function parseSingleReference(query, partitions) {
  const input = query.trim().replace(/[–—]/g, '-');
  if(input.length>256)throw new Error('Please shorten each passage selection to 256 characters.');
  let catalogue=aliasCatalogues.get(partitions);
  if(!catalogue){
    catalogue=new Map();
    for(const partition of partitions)for(const alias of partition.aliases){
      const key=aliasKey(alias);if(!catalogue.has(key))catalogue.set(key,[]);catalogue.get(key).push(partition);
    }
    aliasCatalogues.set(partitions,catalogue);
  }
  let choices=[];
  for(let end=input.length;end>0;end--){
    const aliases=catalogue.get(aliasKey(input.slice(0,end)));
    if(!aliases)continue;
    const rest=input.slice(end).trim();if(rest && !/^\d/.test(rest))continue;
    choices=aliases.map(partition=>({partition,rest}));break;
  }
  if (!choices.length) throw new Error('Enter a book and reference, for example John 3:16 or 1 Cor 13.');
  const books = [...new Set(choices.map(c => c.partition.book))];
  if (books.length > 1) throw new Error(`This book name is ambiguous: ${books.join(', ')}.`);
  const {rest} = choices[0];
  const single = choices.every(c => c.partition.singleChapter);
  let chapter = null;
  const ranges = [];
  if (!rest) return {book: books[0], ranges};
  for (const item of rest.split(/[,;]/)) {
    const ends = item.trim().split('-');
    if (ends.length > 2 || ends.some(s => !s.trim())) throw new Error('Invalid reference range.');
    const chapterOnly = !/[.:]/.test(item) && chapter === null && !single;
    const read = (value, last) => {
      const m = /^(?:(\d+)[.:])?(\d+)([a-z]*)$/.exec(value.trim());
      if (!m) throw new Error(`Invalid reference: ${item}`);
      if (chapterOnly) return [Number(m[2]), last ? Infinity : 0, last ? '\uffff' : ''];
      if (m[1]) chapter = Number(m[1]);
      if (chapter === null) chapter = 1;
      return [chapter,Number(m[2]),m[3] || (last ? '\uffff' : '')];
    };
    const first = read(ends[0],false), last = read(ends.at(-1),true);
    if (compare(first,last)>0) throw new Error('The end of a reference range must follow its start.');
    ranges.push([first,last]);
  }
  return {book: books[0], ranges};
}
export function parseReference(query,partitions) {
  const segments=query.split(';');
  if(segments.length===1)return parseSingleReference(query,partitions);
  if(segments.length>32)throw new Error('Please use no more than 32 passage selections.');
  const selections=[];
  for(let segment of segments){
    segment=segment.trim();
    const previous=selections.at(-1);
    if(previous && /^\d+[a-z]*(?:[.:,\s-]\d|$)/.test(segment) && !/^\d+\s+\p{L}/u.test(segment)){
      const last=previous.ranges.at(-1);
      if(last && Number.isFinite(last[1][1]) && !segment.includes(':') && !segment.includes('.'))segment=`${last[1][0]}:${segment}`;
      segment=`${previous.book} ${segment}`;
    }
    selections.push(parseSingleReference(segment,partitions));
  }
  return {selections};
}
export function within(ref, selection) {
  if (!selection) return true;
  if(selection.selections)return selection.selections.some(part=>within(ref,part));
  if (ref[0] !== selection.book) return false;
  if (!selection.ranges.length) return true;
  return ref[2].split(',').some(span => {
    const ends = span.split('-');
    const first = point(ref[1],ends[0]), last = point(ref[1],ends.at(-1));
    return selection.ranges.some(([a,b]) => compare(last,a)>=0 && compare(first,b)<=0);
  });
}

export function matchTokens(source, query, options) {
  const key = options.accents ? 1 : 0;
  const terms = query.map(t=>t[key]);
  const words = source.map(t=>t[key]);
  const hits = new Set();
  if (options.match === 'phrase') {
    for (let i=0;i<=words.length-terms.length;i++) {
      if (terms.every((term,j)=>words[i+j]===term)) for(let j=0;j<terms.length;j++) hits.add(i+j);
    }
  } else {
    for (let i=0;i<words.length;i++) if (terms.includes(words[i])) hits.add(i);
    if (options.match !== 'any' && !terms.every(term=>words.includes(term))) return [];
  }
  return [...hits].sort((a,b)=>a-b).map(i=>[source[i][2],source[i][3]]);
}

export class SearchEngine {
  constructor(manifest, load, cacheBytes=(manifest.limits?.cacheMiB || 64)*1024*1024) {
    if (manifest.format !== FORMAT) throw new Error('Search has been updated. Reload this page.');
    this.manifest=manifest; this.load=load; this.cache=new Map(); this.cacheBytes=cacheBytes;
    this.usedBytes=0;this.pending=new Map();this.lastSearch=null;
  }
  async data(name, signal) {
    if (signal?.aborted) throw new DOMException('Cancelled','AbortError');
    if (this.cache.has(name)) {
      const cached=this.cache.get(name); this.cache.delete(name); this.cache.set(name,cached); return cached.value;
    }
    const pending=this.pending.get(name);
    if(pending && pending.signal===signal) return pending.promise;
    const request={signal};
    request.promise=(async()=>{
      const value=await this.load(name,signal);
      if(signal?.aborted) throw new DOMException('Cancelled','AbortError');
      // Conservative accounting includes strings and parsed object overhead.
      const bytes=JSON.stringify(value).length*6;
      if(bytes<=this.cacheBytes) {
        this.usedBytes-=this.cache.get(name)?.bytes || 0;
        this.cache.delete(name);this.cache.set(name,{value,bytes});this.usedBytes+=bytes;
        while(this.usedBytes>this.cacheBytes) {
          const first=this.cache.keys().next().value;
          this.usedBytes-=this.cache.get(first).bytes;this.cache.delete(first);
        }
      }
      return value;
    })();
    this.pending.set(name,request);
    try{return await request.promise;}finally{if(this.pending.get(name)===request)this.pending.delete(name);}
  }
  scope(options) {
    return this.manifest.partitions.filter(p => (!options.versions?.length || options.versions.includes(p.version))
      && (!options.book || options.book===p.book) && (!options.group || options.group===p.group)
      && (!options.language || options.language===p.language))
      .sort((a,b)=>(options.order==='traditional' ? a.traditionalOrder-b.traditionalOrder : a.order-b.order)
        || this.manifest.versions.findIndex(v=>v.id===a.version)-this.manifest.versions.findIndex(v=>v.id===b.version));
  }
  async search(options, signal, progress=()=>{}) {
    let query=tokens(options.query || '');
    const excluded=options.mode==='original' ? [] : tokens(options.exclude || '');
    if(options.mode==='original') {
      let value=(options.query||'').trim();
      const kind=options.lookup || 'lemma';
      if(!['lemma','strong','form'].includes(kind)) throw new Error('Choose lemma, word form, or Strong’s number.');
      if(kind==='strong') value=value.toUpperCase().replace(/^([HGA])0+(\d)/,'$1$2');
      query=value ? [[`@${kind}:${normalize(value)}`,normalize(value,true)]] : [];
    }
    const available=this.scope(options);
    const catalogue=this.manifest.books || this.manifest.partitions;
    const selection=options.mode!=='reference' && options.range ? parseReference(options.range,catalogue) : null;
    const ref=options.mode==='reference' ? parseReference(options.query,catalogue) : selection;
    const partitions=available.filter(p=>!ref || options.numbering==='shared' || (ref.selections || [ref]).some(r=>p.book===r.book));
    if(ref && !partitions.length)throw new Error(`This book is not available in the selected versions and filters${this.manifest.test?' in this limited build':''}. Choose another version or clear the filters.`);
    const inRange=row=>options.numbering==='shared' && ref
      ? row.mapping==='exact' && row.mapped.some(r=>within([r[0],r[1],r[2]+(r[3]||'')],ref)) : within(row.ref,ref);
    if(options.mode==='original' && !partitions.some(p=>p.fields.includes('original'))) throw new Error('These versions have no original-word annotations in this build. Choose an annotated source such as UHB or OET-LV.');
    if(options.mode!=='reference' && !query.length) throw new Error('Enter a word or phrase to search for.');
    if(query.length>30 || excluded.length>30) throw new Error('Please use no more than 30 search words or exclusions.');
    const key=JSON.stringify({...options,page:0});
    let hits;
    if(this.lastSearch?.key===key) hits=this.lastSearch.hits;
    else {
    const batches=new Array(partitions.length);
    let next=0,done=0;
    const scan=async n=>{
      if(signal?.aborted) throw new DOMException('Cancelled','AbortError');
      const p=partitions[n];
      const found=[];
      if(options.mode==='reference') {
        for(const row of (await this.data(p.catalogue,signal)).references) if(inRange(row)) {
          found.push({partition:p,reference:row});
        }
      } else {
        const lookups=new Map();
        for(const term of new Set([...query,...excluded].map(t=>t[0]))) {
          const file=p.buckets[String(bucket(term,this.manifest.buckets))];
          const shard=file ? await this.data(file,signal) : {};
          lookups.set(term,Object.hasOwn(shard,term) ? shard[term] : []);
        }
        const permitted=field=>options.mode==='original' ? field==='original' : options.field ? field===options.field : options.mode==='study'
          ? ['note','heading','introduction'].includes(field) : ['body','transliteration','modernised','translation'].includes(field);
        const positions=query.map(t=>{
          const map=new Map();
          for(const row of lookups.get(t[0])) if(permitted(row[1]) && (!options.accents || row[3]===t[1])
              && (options.mode!=='original' || !options.morphology || row[4]===options.morphology)) {
            map.set(row[0],[...(map.get(row[0])||[]),...row[2]]);
          }
          return map;
        });
        const sets=positions.map(p=>new Set(p.keys()));
        let ids=options.match==='any' ? new Set(sets.flatMap(s=>[...s]))
          : new Set([...sets[0]].filter(id=>sets.every(s=>s.has(id))));
        const omit=new Set(excluded.flatMap(t=>lookups.get(t[0]).filter(r=>!options.accents || r[3]===t[1]).map(r=>r[0])));
        const {documents,references}=ids.size ? await this.data(p.catalogue,signal) : {documents:[],references:[]};
        for(const id of [...ids].sort((a,b)=>a-b)) {
          if(omit.has(id)) continue;
          if(options.match==='phrase' && !positions[0].get(id).some(start=>positions.every((map,i)=>map.get(id).includes(start+i)))) continue;
          if(!inRange(references[documents[id][0]])) continue;
          found.push({partition:p,reference:references[documents[id][0]],id,matched:options.mode==='original' ? positions[0].get(id) : null});
        }
      }
      batches[n]=found;progress({done:++done,total:partitions.length});
      await new Promise(resolve=>setTimeout(resolve,0));
    };
    await Promise.all(Array.from({length:Math.min(Math.max(1,this.manifest.limits?.concurrency || 6),partitions.length)},async()=>{
      while(next<partitions.length)await scan(next++);
    }));
    hits=batches.flat();
    const versionOrder=new Map(this.manifest.versions.map((v,i)=>[v.id,i]));
    const rank=hit=>[Number(hit.reference.ref[1]),parseInt(hit.reference.ref[2]),hit.reference.ref[2]];
    hits.sort((a,b)=>(options.order==='traditional' ? a.partition.traditionalOrder-b.partition.traditionalOrder : a.partition.order-b.partition.order)
      || a.partition.book.localeCompare(b.partition.book) || compare(rank(a),rank(b))
      || versionOrder.get(a.partition.version)-versionOrder.get(b.partition.version) || (a.id||0)-(b.id||0));
    this.lastSearch=hits.length<=100000 ? {key,hits} : null;
    }
    if(signal?.aborted) throw new DOMException('Cancelled','AbortError');
    const byBook={};
    for(const hit of hits)byBook[hit.partition.book]=(byBook[hit.partition.book]||0)+1;
    const groups=[],mapped=new Map();
    for(const hit of hits) {
      const groupKey=options.groupMatches && hit.reference.mapping==='exact' && hit.reference.mapped.length ? JSON.stringify(hit.reference.mapped) : null;
      if(groupKey && mapped.has(groupKey))mapped.get(groupKey).push(hit);
      else {const group=[hit];groups.push(group);if(groupKey)mapped.set(groupKey,group);}
    }
    const page=Math.max(0,Math.floor(Number(options.page)||0)), size=20;
    const render=async hit=>{
      const p=hit.partition;
      if(hit.id===undefined) return {...hit.reference,version:p.version,bookName:p.name,field:'reference',text:'',highlights:[]};
      const row=(await this.data(p.blocks[Math.floor(hit.id/p.blockSize)],signal))[hit.id%p.blockSize];
      return {...hit.reference,...row,version:p.version,bookName:p.name,annotations:undefined,
        contextId:{version:p.version,book:p.book,reference:row.reference},
        matchedAnnotations:hit.matched ? hit.matched.map(i=>row.annotations[i]) : undefined,
        highlights:options.mode==='original' ? [] : matchTokens(tokens(row.text),query,options)};
    };
    const results=await Promise.all(groups.slice(page*size,(page+1)*size).map(async group=>{
      const rows=await Promise.all(group.map(render));return {...rows[0],matches:rows.length>1 ? rows : undefined};
    }));
    return {count:groups.length,sourceMatches:hits.length,byBook,page,pages:Math.ceil(groups.length/size),results,
      annotatedVersions:partitions.filter(p=>p.fields.includes('original')).map(p=>p.version).filter((v,i,a)=>a.indexOf(v)===i)};
  }
  async context({version,book,reference},signal) {
    const p=this.manifest.partitions.find(p=>p.version===version && p.book===book);
    if(!p)throw new Error('This passage is unavailable in the current catalogue.');
    const {references:refs,documents:docs}=await this.data(p.catalogue,signal);
    const selected=refs[reference];
    if(!selected)throw new Error('This passage is unavailable in the current catalogue.');
    const nearby=[reference-1,reference,reference+1].filter(i=>refs[i] && refs[i].ref[1]===selected.ref[1]);
    return Promise.all(nearby.map(async i=>{
      const id=docs.findIndex(d=>d[0]===i && d[1]==='body');
      if(id<0)return null;
      const row=(await this.data(p.blocks[Math.floor(id/p.blockSize)],signal))[id%p.blockSize];
      return {...refs[i],text:row.text,version};
    })).then(rows=>rows.filter(Boolean));
  }
}
