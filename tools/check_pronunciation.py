#!/usr/bin/env python3
"""Checks how the voice will pronounce every course text.

Runs espeak-ng (the phonemizer the recorded voice uses) on ttsText() of each text and compares the
result with the Hebrew transliteration shown in the app. Prints the mismatches.

  node tools/tts_texts.js > /tmp/rows.json
  python3 tools/check_pronunciation.py /tmp/rows.json <dir that contains espeak-ng-data>

Letters are skipped: their Hebrew names are written without vowel points.
"""
import sys, json
import re, subprocess
V='V'
def heb2skel(tr):
    tr=tr.replace("'",'׳').replace('’','׳')
    tr=re.sub(r'[?\-.,!]',' ',tr)
    out=[]
    words=tr.split()
    for w in words:
        chars=list(w); i=0; toks=[]  # (cons, vowel_after)
        while i<len(chars):
            c=chars[i]; i+=1
            if not ('א'<=c<='ת'): continue
            ger=False; marks=[]
            while i<len(chars) and (chars[i]=='׳' or '֑'<=chars[i]<='ׇ'):
                if chars[i]=='׳': ger=True
                else: marks.append(chars[i])
                i+=1
            toks.append((c,ger,marks))
        s=''
        for k,(c,ger,m) in enumerate(toks):
            vow=any(x in m for x in 'ֲֳִֵֶַָֻ')
            prev=toks[k-1] if k else None
            prevV=bool(prev) and any(x in prev[2] for x in 'ֲֳִֵֶַָֻ')
            nxt=toks[k+1] if k+1<len(toks) else None
            last=k==len(toks)-1
            if c=='ו' and ('ּ' in m or 'ֹ' in m) and not vow: s+=V; continue
            if c=='י' and not vow and 'ּ' not in m:
                if prev and (prevV or not any(x in prev[2] for x in 'ְ')) and not (nxt is None and prevV and False):
                    if prevV and any(x in prev[2] for x in 'ִֵֶ'): continue   # mater after i/e
                    if prevV: s+='y'; continue
                    s+=V; continue
            if c=='ה' and last and prevV and not vow: continue
            if c=='א': cons=''
            elif ger: cons={'ג':'J','ד':'d','ח':'x','ע':'g','ת':'t','צ':'d','ז':'J'}.get(c,'?')
            else: cons={'ב':'b','ג':'g','ד':'d','ה':'h','ו':'w','ז':'z','ח':'H','ט':'t','י':'y','כ':'k','ך':'k','ל':'l','מ':'m','ם':'m','נ':'n','ן':'n','ס':'s','ע':'E','פ':'f','ף':'f','צ':'s','ץ':'s','ק':'','ר':'r','ש':'S','ת':'t'}.get(c,'?')
            s+=cons+(V if vow else '')
        out.append(s)
    return norm(' '.join(out))
def norm(s):
    s=re.sub(r'[\u0300-\u036f.]','',s).replace(' ','')
    s=re.sub(r'V[yw](?=[^V]|$)','V',s)
    s=re.sub(r'(.)\1+',r'\1',s)
    return s
IPAMAP=[('dˤ','d'),('tˤ','t'),('sˤ','s'),('ðˤ','d'),('zˤ','z'),('dʒ','J'),('ʒ','J'),('χ','x'),('x','x'),('ħ','H'),('ʕ','E'),('ɣ','g'),('ʁ','g'),('ʃ','S'),('θ','t'),('ð','d'),('q','g?'),('ʔ',''),('j','y')]
def ipa2skel(ipa):
    ipa=re.sub(r'\([a-z]+\)','',ipa)
    ipa=re.sub(r'[ˈˌːˑ‿ \-]','',ipa)
    for a,b in IPAMAP: ipa=ipa.replace(a,b)
    ipa=ipa.replace('g?','')
    ipa=re.sub(r'[aeiouɑæɐəɪʊɛɔɒʌ]',V,ipa)
    return norm(ipa)
def espeak(t,voice_dir):
    return subprocess.run(['espeak-ng','--path='+voice_dir,'-v','ar','-q','--ipa',t],capture_output=True,text=True).stdout.strip()
def lev(a,b):
    p=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        c=[i]
        for j,cb in enumerate(b,1): c.append(min(p[j]+1,c[-1]+1,p[j-1]+(ca!=cb)))
        p=c
    return p[-1]

if __name__=='__main__':
    rows=json.load(open(sys.argv[1])); voice=sys.argv[2]; bad=0; n=0
    for r in rows:
        if r['kind'] not in ('word','example') or not r['exp']: continue
        n+=1; ip=espeak(r['tts'],voice); a=heb2skel(r['exp']); b=ipa2skel(ip); d=lev(a,b)
        if d: bad+=1; print(f"{d}  {r['text']}  ->  {r['tts']}   app: {r['exp']} [{a}]   voice: {ip} [{b}]")
    print(f"{bad} of {n} differ")
