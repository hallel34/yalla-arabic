#!/usr/bin/env python3
"""Records the course with a Microsoft Azure neural voice (no human recording needed).

Needs an Azure Speech resource: AZURE_SPEECH_KEY and AZURE_SPEECH_REGION (e.g. westeurope).
The voice reads ttsText() of each text: Palestinian spelling with full vowels.

  node tools/tts_texts.js > /tmp/rows.json

  # 1. compare voices on a few words -> samples.html (open it and listen)
  python3 tools/azure_audio.py samples /tmp/rows.json samples.html

  # 2. record everything with the chosen voice and embed it in index.html (window.AUDIO)
  python3 tools/azure_audio.py all /tmp/rows.json ar-JO-TaimNeural
"""
import sys, os, json, base64, html, time, urllib.request, urllib.error

KEY=os.environ.get('AZURE_SPEECH_KEY'); REGION=os.environ.get('AZURE_SPEECH_REGION','westeurope')
# Levantine voices, closest to Palestinian
VOICES=['ar-JO-TaimNeural','ar-JO-SanaNeural','ar-LB-RamiNeural','ar-LB-LaylaNeural','ar-SY-LaithNeural','ar-SY-AmanyNeural']
SAMPLE_WORDS=['خَمْسة','قَهْوة','مَرْحَبا','كيفَك؟','مْنيح','شُكْراً','بَدّي قَهْوة مِن فَضْلَك','باء','عَيْن']

def synth(text,voice,rate):
    lang='-'.join(voice.split('-')[:2])
    ssml=(f"<speak version='1.0' xml:lang='{lang}'><voice name='{voice}'>"
          f"<prosody rate='{rate}'>{html.escape(text)}</prosody></voice></speak>")
    req=urllib.request.Request(f'https://{REGION}.tts.speech.microsoft.com/cognitiveservices/v1',data=ssml.encode('utf8'),method='POST',headers={
        'Ocp-Apim-Subscription-Key':KEY,'Content-Type':'application/ssml+xml',
        'X-Microsoft-OutputFormat':'audio-24khz-48kbitrate-mono-mp3','User-Agent':'yalla-arabic'})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req,timeout=30) as r: return r.read()
        except urllib.error.HTTPError as e:
            if e.code==429 and attempt<3: time.sleep(2**attempt); continue
            sys.exit(f'Azure refused ({e.code}): {e.read().decode(errors="replace")[:300]}. Check the key and region.')

def main():
    if not KEY: sys.exit('Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION first.')
    mode,rows_path=sys.argv[1],sys.argv[2]; rows={r['text']:r for r in json.load(open(rows_path,encoding='utf8'))}
    if mode=='samples':
        out=sys.argv[3] if len(sys.argv)>3 else 'samples.html'
        cells=[]
        for v in VOICES:
            row=[]
            for w in SAMPLE_WORDS:
                r=rows.get(w,{'tts':w,'kind':'word'})
                mp3=synth(r['tts'],v,'-25%' if r['kind']=='letter' else '-10%')
                row.append(f"<td><div class=ar>{html.escape(w)}</div><audio controls preload=none src='data:audio/mpeg;base64,{base64.b64encode(mp3).decode()}'></audio></td>")
            cells.append(f"<tr><th>{v}</th>{''.join(row)}</tr>")
        open(out,'w',encoding='utf8').write("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'><title>Voice samples</title>"
            "<style>body{font-family:system-ui;margin:16px}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:6px;vertical-align:top}"
            ".ar{font-size:22px;direction:rtl}audio{width:140px}</style><div style='overflow-x:auto'><table>"+''.join(cells)+"</table></div>")
        print('wrote',out)
    elif mode=='all':
        voice=sys.argv[3]; audio={}
        for i,r in enumerate(rows.values()):
            mp3=synth(r['tts'],voice,'-25%' if r['kind']=='letter' else '-10%')
            audio[r['text']]='data:audio/mpeg;base64,'+base64.b64encode(mp3).decode()
            if i%25==0: print(i,'/',len(rows),flush=True)
        page=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','index.html')
        s=open(page,encoding='utf8').read(); a=s.index('window.AUDIO='); b=s.index(';\n</script>',a)
        s=s[:a]+'window.AUDIO='+json.dumps(audio,ensure_ascii=False,separators=(',',':'))+s[b:]
        open(page,'w',encoding='utf8').write(s); print(len(audio),'clips embedded with',voice)
    else: sys.exit(__doc__)

if __name__=='__main__': main()
