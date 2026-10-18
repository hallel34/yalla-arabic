// Lists every Arabic text the course speaks, with the respelled text sent to the voice (ttsText in index.html)
// and the Hebrew transliteration the app shows for it. Usage: node tools/tts_texts.js > texts.json
const fs=require('fs'),path=require('path');
const s=fs.readFileSync(path.join(__dirname,'..','index.html'),'utf8');
const src=s.slice(s.indexOf('/* ===================== CONTENT'),s.indexOf('/* ===================== STATE'));
const digits=s.match(/const DIGIT_SAY=.*;/)[0];
const tts=s.slice(s.indexOf('const TTS_OVR'),s.indexOf('function speakOnline('));
const out=new Function(digits+src+tts+`
  const rows=[],seen=new Set();
  const add=(text,exp,kind)=>{if(seen.has(text))return;seen.add(text);rows.push({text,kind,exp,tts:ttsText(text)});};
  const tr={};Object.values(ITEMS).forEach(it=>{if(it.kind==='word')tr[it.ar]=it.tr;});
  Object.values(ITEMS).forEach(it=>{
    if(it.kind==='letter'){add(LETTER_SAY[it.ar],it.tr,'letter');add(it.exAr,it.exTr,'example');}
    else if(it.kind==='digit')add(DIGIT_SAY[it.ar],it.tr,'word'); else add(it.ar,it.tr,'word');});
  LESSONS.forEach(L=>L.sents.forEach(x=>add(x.toks.join(' '),x.toks.map(t=>tr[t]||'').join(' '),'sentence')));
  ['مَرْحَبا، يَلّا نِتْعَلَّم عَرَبي','بْرافو عَلَيك'].forEach(t=>add(t,'','other'));
  return rows;`)();
process.stdout.write(JSON.stringify(out,null,1));
