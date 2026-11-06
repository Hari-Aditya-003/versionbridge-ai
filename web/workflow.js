/* Shared architecture guide and evidence-driven run graph. */
function initialFlow() {
  return {nodes:Object.fromEntries(['source','baseline','analysis','cloud','local','policy','verify','evidence','review'].map(id=>[id,'pending'])),backend:'cloud',label:'Ready for a run',attempt:0};
}
function reduceFlow(previous, event) {
  const state={...previous,nodes:{...previous.nodes}};
  const done=(...ids)=>ids.forEach(id=>state.nodes[id]='done');
  if(event.event==='project') { const fresh=initialFlow();fresh.nodes.source='active';fresh.label='Preparing source';return fresh; }
  if(event.event==='stage' && event.step===0) { done('source');state.nodes.baseline='active';state.label='Reproducing failure'; }
  if(event.event==='analysis') { done('source','baseline');state.nodes.analysis='active';state.label='Localizing and classifying'; }
  if(event.event==='routing' || event.event==='diagnosis') {
    state.backend=/ollama|local|qwen/i.test(event.provider||event.model||'')?'local':'cloud';
    done('source','baseline','analysis');state.nodes[state.backend]=event.event==='diagnosis'?'done':'active';
    state.nodes[state.backend==='local'?'cloud':'local']='pending';
    state.nodes.policy=event.event==='diagnosis'?'active':'pending';state.nodes.verify='pending';
    state.attempt=event.attempt||state.attempt||1;state.label=event.event==='diagnosis'?'Checking the proposed edit':`Authoring candidate ${state.attempt}`;
  }
  if(event.event==='stage' && event.step===2) { done('policy');state.nodes.verify='active';state.label='Running original and independent checks'; }
  if(event.event==='rejected') { state.nodes[Object.keys(event.verification_tests||{}).length?'verify':'policy']='rejected';state.label='Candidate rejected'; }
  if(event.event==='result') {
    done('source','baseline','analysis',state.backend,'policy','verify','evidence');state.nodes.review='active';
    state.label='Verified against listed checks · review the patch';
  }
  if(event.event==='error') {state.label='Unverified';Object.keys(state.nodes).forEach(k=>{if(state.nodes[k]==='active')state.nodes[k]='rejected';});}
  return state;
}
if(typeof module!=='undefined') module.exports={initialFlow,reduceFlow};
if(typeof document!=='undefined') (()=>{
  const nodes=[
    {id:'source',x:35,y:95,icon:'⌁',title:'Source intake',sub:'Pinned snapshot · queue',detail:'Resolve a pinned source revision or load a reviewed project. The web service queues the job; a separate worker prepares the source and immutable hashes.'},
    {id:'baseline',x:295,y:95,icon:'▶',title:'Baseline sandbox',sub:'Reproduce the failure',detail:'A new no-network Docker container runs the original test suite. The pipeline requires a complete, genuinely failing baseline before proposing a repair.'},
    {id:'analysis',x:555,y:95,icon:'⌘',title:'Fault diagnosis',sub:'Context · category router',detail:'Bounded source analysis and diagnostics identify affected symbols and the repair category. Models receive relevant source and failure data within a restricted edit scope.'},
    {id:'cloud',x:875,y:45,icon:'✦',title:'Cloud model',sub:'Primary → bounded fallback',detail:'The worker calls a registered Vultr model and records the requested and served IDs. A rejected candidate can trigger one sequential fallback with bounded failure feedback.'},
    {id:'local',x:875,y:225,icon:'▣',title:'Private model',sub:'Dell · quantized Ollama',detail:'The optional private profile calls Ollama through a loopback SSH tunnel. Fresh GPU readings govern admission, and the same policy and verifier apply.'},
    {id:'policy',x:875,y:425,icon:'{ }',title:'Patch policy',sub:'Scope · syntax · checksums',detail:'Trusted code binds proposed spans to original-source checksums. Paths, protected tests, syntax, signatures, edit size and new sensitive operations are checked before execution.'},
    {id:'verify',x:555,y:425,icon:'✓',title:'Fresh verification',sub:'Original + independent checks',detail:'A pristine candidate runs in a fresh container using the same image and original test inventory. V2 migrations also run independent behavior checks owned by a trusted supervisor.'},
    {id:'evidence',x:295,y:425,icon:'≡',title:'Run evidence',sub:'Files · outputs · TXT export',detail:'Collect actual source snapshots, candidate changes, model receipts, individual test outcomes and container teardown. Save a readable TXT bundle with the captured run files and results.'},
    {id:'review',x:35,y:425,icon:'↗',title:'Maintainer review',sub:'Inspect · download · decide',detail:'A passing run is verified against its listed checks. Inspect and download the proposed patch, then decide whether to apply it to your repository.'}
  ];
  const links=[['source','baseline','M225 140 H295'],['baseline','analysis','M485 140 H555'],['analysis','cloud','M745 140 H795 Q815 140 815 110 V105 Q815 90 835 90 H875'],['analysis','local','M745 140 H795 Q815 140 815 160 V250 Q815 270 835 270 H875'],['cloud','policy','M1065 90 H1080 Q1095 90 1095 110 V450 Q1095 470 1065 470'],['local','policy','M1065 270 H1080 Q1095 270 1095 290 V450 Q1095 470 1065 470'],['policy','verify','M875 470 H745'],['verify','evidence','M555 470 H485'],['evidence','review','M295 470 H225']];
  const instances=[];
  document.querySelectorAll('[data-workflow]').forEach((root,index)=>{
    const guide=root.dataset.workflow==='guide';let state=initialFlow(),timer,paused=false,tourIndex=0;
    const prefix=`wf-${index}`;
    root.classList.add('workflow-board');
    root.innerHTML=`<div class="wf-toolbar"><span class="wf-kicker">VERSIONBRIDGE / EXECUTION GRAPH</span><span class="wf-mode">${guide?'ANIMATED ARCHITECTURE GUIDE':'LIVE RUN EVENTS'}</span>${guide?'<button class="wf-toggle" type="button">Pause animation</button>':''}</div><div class="wf-scroll" tabindex="0" aria-label="Architecture workflow canvas; scroll horizontally on small screens"><div class="wf-canvas"><svg class="wf-wires" viewBox="0 0 1120 580" aria-hidden="true"><defs><marker id="${prefix}-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10Z" fill="currentColor"/></marker></defs>${links.map(([a,b,d])=>`<path class="wf-edge" data-from="${a}" data-to="${b}" d="${d}" marker-end="url(#${prefix}-arrow)"/>`).join('')}<text x="790" y="58" class="wf-label">CLOUD</text><text x="786" y="307" class="wf-label">OR LOCAL</text><text x="673" y="375" class="wf-label">MODEL CLAIMS → EXECUTED EVIDENCE</text></svg>${nodes.map(n=>`<button type="button" class="wf-node" data-node="${n.id}" data-status="pending" style="left:${n.x}px;top:${n.y}px" aria-pressed="false"><span class="wf-port in"></span><span class="wf-node-icon">${n.icon}</span><span class="wf-node-title">${n.title}</span><span class="wf-node-sub">${n.sub}</span><span class="wf-node-state">Ready</span><span class="wf-port out"></span></button>`).join('')}</div></div><div class="wf-bottom"><span class="wf-legend"><i></i>${guide?'Illustrated flow · not a running job':'Waiting for an execution event'}</span><span>One backend per attempt · policy and tests decide</span></div><div class="wf-explanation"><strong>Source intake</strong><p>${nodes[0].detail}</p></div>`;
    const explanation=root.querySelector('.wf-explanation');
    function select(id){const node=nodes.find(n=>n.id===id);root.querySelectorAll('[data-node]').forEach(el=>el.setAttribute('aria-pressed',String(el.dataset.node===id)));explanation.querySelector('strong').textContent=node.title;explanation.querySelector('p').textContent=node.detail;}
    function paint(){root.querySelectorAll('[data-node]').forEach(el=>{const value=state.nodes[el.dataset.node];el.dataset.status=value;el.querySelector('.wf-node-state').textContent={pending:'Ready',active:guide?'Flowing':'In progress',done:'Complete',rejected:'Rejected'}[value];});root.querySelectorAll('.wf-edge').forEach(edge=>{edge.dataset.status=state.nodes[edge.dataset.to]==='active'?'active':state.nodes[edge.dataset.from]==='done'&&state.nodes[edge.dataset.to]==='done'?'done':'pending';});if(!guide)root.querySelector('.wf-legend').lastChild.textContent=state.label;}
    root.querySelectorAll('[data-node]').forEach(el=>el.addEventListener('click',()=>select(el.dataset.node)));
    if(guide){const order=['source','baseline','analysis','cloud','policy','verify','evidence','review'];const step=()=>{state=initialFlow();order.slice(0,tourIndex).forEach(id=>state.nodes[id]='done');state.nodes[order[tourIndex]]='active';paint();tourIndex=(tourIndex+1)%order.length;};const start=()=>{clearInterval(timer);timer=setInterval(()=>{if(!document.hidden&&!matchMedia('(prefers-reduced-motion: reduce)').matches)step();},1450);};step();start();root.querySelector('.wf-toggle').addEventListener('click',event=>{paused=!paused;event.target.textContent=paused?'Play animation':'Pause animation';if(paused)clearInterval(timer);else start();});}
    else paint();
    instances.push({reset(){state=initialFlow();paint();},event(event){state=reduceFlow(state,event);paint();}});
  });
  window.VersionBridgeWorkflow={reset(){instances.forEach(i=>i.reset());},event(event){instances.forEach(i=>i.event(event));}};
})();
