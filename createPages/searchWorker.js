// SPDX-License-Identifier: CC0-1.0
// CHANGELOG: 2026-11-01 Isolate cancellable Bible searches from the interface.
import {SearchEngine,fetchJSON} from './searchCore.js';
let engine, controller;
self.onmessage=async ({data})=>{
  if(data.type==='init') {
    const base=new URL(data.base);
    engine=new SearchEngine(data.manifest, async (name,signal)=>{
      if(!/^[a-z]+-[a-f0-9]{24}\.bin$/.test(name)) throw new Error('Invalid search asset.');
      return fetchJSON(new URL(name,base),signal);
    });
    return;
  }
  if(data.type==='cancel'){controller?.abort();return;}
  if(data.type==='context') {
    try{self.postMessage({contextId:data.contextId,context:await engine.context(data.reference)});}
    catch(error){self.postMessage({contextId:data.contextId,error:error.message});}
    return;
  }
  controller?.abort(); controller=new AbortController();
  const signal=controller.signal;
  try {
    if(!engine) throw new Error('Search is still loading.');
    const result=await engine.search(data.options,signal,progress=>self.postMessage({id:data.id,progress}));
    if(!signal.aborted) self.postMessage({id:data.id,result});
  } catch(error) {
    if(error.name!=='AbortError') self.postMessage({id:data.id,error:error.message});
  }
};
