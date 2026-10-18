// End-to-end checks in headless Chromium: voice choice, spoken text, every lesson, layout.
// Usage: node tools/e2e.js   (needs playwright; set CHROMIUM=/path/to/chromium if needed)
const path=require('path');
let pw; try{pw=require('playwright');}catch(e){pw=require('/opt/node22/lib/node_modules/playwright');}
const PAGE='file://'+path.join(__dirname,'..','index.html');
const fails=[]; const ok=(c,msg)=>{console.log((c?'PASS ':'FAIL ')+msg); if(!c)fails.push(msg);};

function fakeSpeech({voices,silent=false}){
  window.__spoken=[]; window.__played=[];
  class U{constructor(t){this.text=t;}}
  window.SpeechSynthesisUtterance=U; let sp=false;
  if(voices) Object.defineProperty(window,'speechSynthesis',{configurable:true,value:{
    getVoices:()=>voices, cancel(){sp=false;}, resume(){}, addEventListener(){}, get speaking(){return sp;}, pending:false,
    speak(u){ if(u.text.trim()) window.__spoken.push({text:u.text,voice:u.voice&&u.voice.name});
      if(!silent){sp=true;setTimeout(()=>u.onstart&&u.onstart(),5);setTimeout(()=>{sp=false;u.onend&&u.onend();},30);} }}});
  else Object.defineProperty(window,'speechSynthesis',{configurable:true,value:undefined});
  HTMLMediaElement.prototype.play=function(){window.__played.push(this.src);return Promise.resolve();};
}
async function open(browser,voices,opts,size={width:400,height:860}){
  const p=await browser.newPage({viewport:size}); const errs=[];
  p.on('pageerror',e=>errs.push(e.message));
  await p.route('**/*',r=>r.request().url().startsWith('file:')?r.continue():r.abort());
  await p.addInitScript(fakeSpeech,{voices,silent:!!(opts&&opts.silent)});
  await p.goto(PAGE); await p.waitForTimeout(300); p.errs=errs; return p;
}
const clipKey=(p,src)=>p.evaluate(s=>Object.keys(window.AUDIO).find(k=>window.AUDIO[k]===s)||null,src);

(async()=>{
  const browser=await pw.chromium.launch(process.env.CHROMIUM?{executablePath:process.env.CHROMIUM}:{}).catch(()=>pw.chromium.launch({executablePath:'/opt/pw-browsers/chromium'}));

  // 1. Phone with Google's Arabic voice: the device voice speaks, with the Palestinian respelling
  let p=await open(browser,[{name:'Samsung English',lang:'en-US'},{name:'Arabic',lang:'ar_XA'}]);
  await p.evaluate(()=>speak('خَمْسة')); await p.waitForTimeout(150);
  let sp=await p.evaluate(()=>window.__spoken);
  ok(sp.length===1&&sp[0].voice==='Arabic','Arabic device voice is used when installed ('+JSON.stringify(sp)+')');
  ok(sp[0]&&sp[0].text==='خَمْسَ','khamsa is sent as خَمْسَ, not khamst ('+(sp[0]&&sp[0].text)+')');
  await p.evaluate(()=>{window.__spoken=[];speak('بَدّي قَهْوة مِن فَضْلَك');}); await p.waitForTimeout(150);
  sp=await p.evaluate(()=>window.__spoken);
  ok(sp[0]&&sp[0].text.includes('أَهْوَ')&&!sp[0].text.includes('ق'),'qaf is said as a glottal stop ('+(sp[0]&&sp[0].text)+')');
  await p.close();

  // 2. Android quirk: empty voice list. Device is tried; if it stays silent the clip plays
  p=await open(browser,[],{silent:true});
  await p.evaluate(()=>speak('خَمْسة')); await p.waitForTimeout(2600);
  let pl=await p.evaluate(()=>window.__played);
  const k2=pl.length?await clipKey(p,pl.at(-1)):null;
  ok(pl[0]&&pl[0].includes('translate_tts')&&k2==='خَمْسة',`silent device: Google web voice next, then the clip (${pl.length} played, last ${k2})`);
  await p.close();

  // 3. Only non-Arabic voices: the clip plays right away
  p=await open(browser,[{name:'English',lang:'en-US'}]);
  await p.evaluate(()=>speak('خَمْسة')); await p.waitForTimeout(150);
  pl=await p.evaluate(()=>window.__played); sp=await p.evaluate(()=>window.__spoken);
  ok(sp.length===0&&pl[0]&&pl[0].includes('translate_tts')&&pl[0].includes(encodeURIComponent('خَمْسَ')),'no Arabic voice: Google web voice (the Translate voice) first, never a wrong-language voice');
  ok(await clipKey(p,pl.at(-1))==='خَمْسة','web voice blocked: falls back to the recorded clip');
  await p.click('#voicebtn'); await p.waitForTimeout(100);
  const diag=await p.evaluate(()=>document.querySelector('.diag').innerText);
  ok(/לא עבד: קול גוגל מהרשת/.test(diag)&&/קולות ערביים במכשיר\s*אין/.test(diag),'voice panel shows the failed source and that no Arabic voice exists');
  await p.click('.mode:nth-child(4)'); await p.waitForTimeout(150);
  ok(await p.evaluate(()=>localStorage.getItem('yalla-voice'))==='clips','voice mode choice is saved');
  await p.close();

  // 4. No speech engine at all (in-app browsers): every lesson, every exercise, each spoken text has a clip
  p=await open(browser,null);
  await p.evaluate(()=>{window.__said=[];const o=window.speak;window.speak=t=>{window.__said.push(t);return o(t);};});
  const nLessons=await p.evaluate(()=>LESSONS.length); let stuck=0, nullText=0;
  for(let L=0;L<nLessons;L++){
    await p.evaluate(i=>startLesson(LESSONS[i]),L);
    for(let i=0;i<150;i++){
      if(await p.$('.done-screen')) break;
      if(await p.evaluate(()=>document.getElementById('rbody').innerText.split('\n').some(l=>l.trim()==='null'))) nullText++;
      const inp=await p.$('.typing input:not([disabled])');
      if(inp){await inp.fill('x'); await p.click('#rfoot .btn'); await p.click('#rfoot .btn'); continue;}
      const opt=await p.$('.opt:not([disabled])');
      if(opt){await opt.click(); await p.click('#rfoot .btn'); await p.click('#rfoot .btn'); continue;}
      const tile=await p.$('.bank .tile:not(.used)');
      if(tile){await tile.click(); await p.click('#rfoot .btn'); await p.click('#rfoot .btn'); continue;}
      const b=await p.$('#rfoot .btn:not([disabled])'); if(!b){stuck++;break;} await b.click();
      if(await p.$('#rfoot.no, #rfoot.ok')) { const c=await p.$('#rfoot .btn'); c&&await c.click(); }
    }
    if(!(await p.$('.done-screen'))) stuck++;
    await p.evaluate(()=>closeRunner());
  }
  const said=[...new Set(await p.evaluate(()=>window.__said))];
  const missing=await p.evaluate(list=>list.filter(t=>!window.AUDIO[t]),said);
  ok(stuck===0,`all ${nLessons} lessons finish (${stuck} stuck)`);
  ok(nullText===0,'no stray "null" text on lesson screens');
  ok(missing.length===0,`every spoken text has a recorded clip (${said.length} texts, missing: ${missing.join(' / ')})`);
  ok(p.errs.length===0,'no script errors '+p.errs.join(' | '));
  await p.close();

  // 5. Letter screen fits a small phone
  p=await open(browser,null,{}, {width:360,height:780});
  await p.evaluate(()=>startLesson(LESSONS[1]));
  const ov=await p.evaluate(()=>{const f=document.querySelector('.forms');return [...f.children].every(c=>{const r=c.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth;});});
  ok(ov,'letter forms row fits at 360px');
  await p.close();

  await browser.close();
  console.log(fails.length?`\n${fails.length} FAILED`:'\nall passed'); process.exit(fails.length?1:0);
})();
