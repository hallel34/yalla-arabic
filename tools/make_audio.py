#!/usr/bin/env python3
"""Records every course text with the Piper ar_JO-kareem voice and embeds the clips in index.html (window.AUDIO).

  pip install sherpa-onnx numpy        # and ffmpeg on PATH
  # voice: https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-ar_JO-kareem-medium.tar.bz2
  node tools/tts_texts.js > /tmp/rows.json
  python3 tools/make_audio.py /tmp/rows.json <unpacked voice dir>

The voice reads ttsText() of each text (Palestinian spelling with full vowels), not the text itself.
"""
import sys, os, json, base64, subprocess
import numpy as np, sherpa_onnx

rows=json.load(open(sys.argv[1])); vd=sys.argv[2]
tts=sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
    vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=os.path.join(vd,'ar_JO-kareem-medium.onnx'),
        tokens=os.path.join(vd,'tokens.txt'),data_dir=os.path.join(vd,'espeak-ng-data')),num_threads=4)))
audio={}
for r in rows:
    a=tts.generate(r['tts'],sid=0,speed=0.75 if r['kind']=='letter' else 0.85)
    x=np.array(a.samples,dtype=np.float32); loud=np.where(np.abs(x)>0.01)[0]
    pad=int(0.05*a.sample_rate); x=x[max(0,loud[0]-pad):loud[-1]+3*pad]; x=x/np.abs(x).max()*0.9
    mp3=subprocess.run(['ffmpeg','-loglevel','error','-f','s16le','-ar',str(a.sample_rate),'-ac','1','-i','-',
        '-c:a','libmp3lame','-b:a','32k','-f','mp3','-'],input=(x*32767).astype(np.int16).tobytes(),capture_output=True,check=True).stdout
    audio[r['text']]='data:audio/mpeg;base64,'+base64.b64encode(mp3).decode()
page=os.path.join(os.path.dirname(__file__),'..','index.html')
s=open(page,encoding='utf8').read(); i=s.index('window.AUDIO='); j=s.index(';\n</script>',i)
s=s[:i]+'window.AUDIO='+json.dumps(audio,ensure_ascii=False,separators=(',',':'))+s[j:]
open(page,'w',encoding='utf8').write(s); print(len(audio),'clips')
