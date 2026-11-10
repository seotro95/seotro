import concurrent.futures,hashlib,json,re,time
from pathlib import Path
from prepare_scripts import LANGS,source,chapters,translation_source,translate,adapt
R=Path(__file__).parent;S=R/'voice/scripts';selected=[0,1,2,3,4,5,9]
def clarified(ch):
 text=translation_source(ch)
 fixes={
 'Our last will reach beyond that cave':'Our final clue will reach beyond that cave',
 'an illustrative camp':'an illustration of an ancient living campsite',
 'Dating work at Denisova':'Research estimating the ages of archaeological material at Denisova',
 'between deposits':'between sediment layers',
 "The maker of a tool needs evidence of association, not just proximity.":"Identifying who made a tool requires evidence of an archaeological association, not just nearby objects.",
 'A useful scientific claim must survive alternatives.':'A useful scientific explanation must remain well supported after alternative explanations are tested.',
 'then available for modern humans and Neanderthals':'available at that time for modern humans and Neanderthals',
 'a nuclear genome analysis':'an analysis of the genome from the cell nucleus',
 'a genome in the cell nucleus analysis':'an analysis of the genome from the cell nucleus',
 'a high sequencing coverage Denisovan genome':'a Denisovan genome reconstructed from repeated sequencing reads',
 'average coverage of about thirty times':'each genomic position was read about thirty times on average',
 'Researchers described each genomic position was read about thirty times on average.':'Researchers reported that each genomic position was read about thirty times on average.',
 'a high sequencing coverage genome':'a genome reconstructed from many sequencing reads',
 'every position is equally certain':'the information at every position in the genetic sequence is equally certain',
 'inherited segments':'inherited DNA segments',
 'the inherited record':'the inherited genetic record',
 'inherited contribution':'inherited genetic contribution',
 'interbreeding between ancestral populations':'people from different ancestral groups having offspring together',
 'contacts and population structure':'contacts between ancient groups and the structure of those groups',
 'one Siberian reference':'one ancient genome reference from Siberia',
 'Its samples anchor comparisons':'Its samples provide reference points for comparisons',
 'the body\'s response to low oxygen conditions at high altitude':'how the body responds to low oxygen at high altitude',
 'Its recovery history complicates dating.':'The way the fossil was recovered makes estimating its ancient age difficult.',
 'a jaw once difficult to place':'a jaw fossil once difficult to classify',
 'thirty ancient people had been sampled':'thirty ancient individuals had been sampled',
 'very little material':'a very small amount of bone sample material',
 'a small surviving piece':'a small surviving bone fragment',
 'one individual offers':'one sampled individual offers'}
 for a,b in fixes.items():text=text.replace(a,b)
 # Do not introduce an expanded gloss for every repetition of the same technical term.
 text=text.replace('mitochondrial DNA, the genetic material in mitochondria','mitochondrial DNA')
 return text
def run(loc):
 p=S/f'{loc}.json';marker=p.with_suffix('.review-clarity-v4')
 if marker.exists() and not __import__('os').environ.get('REVIEW_FORCE'):return loc
 rows=json.loads(p.read_text())
 for n in selected:
  text=clarified(chapters[n]);out=adapt(translate(text,LANGS[loc]),loc)
  # Match all scientific dates/numbers explicitly present in the clarified source.
  normalized=re.sub(r'[.,\s\u00a0\u202f]','',out)
  if loc=='ja-JP':normalized=re.sub(r'(\d+)万(\d{0,4})',lambda m:str(int(m[1])*10000+int(m[2] or 0)),normalized)
  for y in ['2008','2010','2012','2014','2018','2019','2021','2024','2025','2026','146000','160000']:
   if y in text:assert y in normalized,(loc,n+1,y)
  assert not re.search(r'\b(\w+)(?:\s+\1){4,}\b',out,re.I),(loc,n+1,'hallucinated repetition')
  rows[n]['voice']=out;rows[n]['source_en_clarity_review']=text;rows[n]['editorial_review']='Faithful scientific clarification before translation: dating means age estimation; coverage means repeated sequence reads; DNA inheritance rather than financial inheritance; independent native/listening review pending.'
  p.write_text(json.dumps(rows,ensure_ascii=False,indent=2));print(json.dumps({'clarity_review':loc,'chapter':n+1}),flush=True);time.sleep(1)
 p.with_suffix('.txt').write_text('\n\n'.join(x['voice'] for x in rows));p.with_suffix('.terminology-v2').write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'\n');marker.write_text('Assistant scientific clarity review; independent native listening review pending.\n');return loc
if __name__=='__main__':
 import sys,os
 langs=[l for l in LANGS if l not in ['mww','vi-VN']]
 if os.environ.get('REVIEW_LOCALES'):langs=os.environ['REVIEW_LOCALES'].split(',')
 if os.environ.get('REVIEW_CHAPTERS'):selected=[int(x)-1 for x in os.environ['REVIEW_CHAPTERS'].split(',')]
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  fs={pool.submit(run,l):l for l in langs};failed=[]
  for f in concurrent.futures.as_completed(fs):
   try:print('CLARITY_READY',f.result(),flush=True)
   except Exception as e:failed.append(fs[f]);print('REVIEW_ERROR',fs[f],type(e).__name__,str(e),flush=True)
 if failed:raise SystemExit(1)
