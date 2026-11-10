import concurrent.futures,hashlib,json,re,time
from pathlib import Path
import prepare_scripts as P
R=Path(__file__).parent;S=R/'voice/scripts'
OVERRIDES={
22:'Practical knowledge of places, seasons, materials and other people could help a community use a difficult environment. This is an explanation of a possibility, not a recovered personal biography.',
23:'People needed to maintain their equipment and practical skills. Tools wear out and conditions change, so useful knowledge had to be supported by continued work.',
27:'A deliberately shaped object differs from an unworked material on the ground. Its manufacture involved choices about collecting material, selecting a working place and changing its shape.',
28:'Archaeologists examine object surfaces, breakage, manufacturing traces and the surrounding deposits. These relationships help explain the object and can be lost if it is removed without records.',
31:'An illustration may show an adult repairing a seam in animal skin. The actual archaeological evidence is a surviving sewing tool and its context, not the identity of that illustrated maker.',
34:'These distinctions allow us to recognise skilled activity while admitting that we do not know the conversations or all the meanings associated with that work.',
35:'Objects survive selectively. Durable stone and bone may remain when wood, fibres, animal skins and many other materials from everyday life have disappeared.',
62:'The research team called a genetic grouping represented by the Yana individuals Ancient North Siberians. This is a scientific label, not a known ancient tribal name.',
64:'Those findings do not assign the ancient individuals a modern nationality or a present-day European or East Asian identity.',
65:'A scientific grouping summarises genetic relationships in a model. It does not establish a flag, shared language, uniform appearance or complete cultural identity.',
67:'Ancient genetic groupings organise incomplete evidence. Future samples may reveal additional differences within a group, rather than confirming a perfectly uniform population.',
68:'The name Ancient North Siberians helps researchers discuss an ancient genetic grouping that was previously poorly sampled. It does not establish a people with exact known territorial borders.',
69:'Identifying an ancient population does not identify the first people who ever used every part of the region. The earliest known sample describes the current limit of evidence.',
70:'A later discovery may extend the record, change relationships between samples or reveal an ancient population currently represented only indirectly in models.',
72:'Two samples create a further question. How much can material from only two ancient individuals reveal about a community or a much larger population?',
73:'The two Yana individuals were not identified as close genetic relatives. Their genomes did not show the signatures of recent reproduction between close relatives tested in the study.',
76:'The study used a demographic model to estimate effective population size, a technical measure of genetic population history. This is not a count of people living beside one campfire.',
77:'A demographic model estimates consequences of biological reproduction and inherited DNA without counting everyone alive. Its assumptions and the period it represents remain important.',
78:'A genetic population estimate should not be illustrated as an exact count of residents in one ancient village. A fixed crowd can falsely suggest that this uncertain quantity is a direct census.',
80:'Contacts may develop through many ordinary movements over generations. Meetings, shared knowledge and biological relationships do not necessarily leave identical traces in archaeological deposits.',
81:'A tool may spread through exchange or teaching without its maker travelling with it. DNA is inherited through biological reproduction, so those histories need not match exactly.',
82:'Archaeology and genetics are useful together because they study different evidence. Archaeology examines material traces of work and activity, while genetics investigates inherited biological relationships.',
83:'Neither method can answer every question addressed by the other. A sewing needle cannot identify all ancestry, and a genome cannot explain every meaning of a sewing needle.',
84:"The Yana findings also inform comparisons with the archaeological site of Mal'ta in Siberia, near Lake Baikal. An ancient genome from that site had already become important.",
85:"The individual sampled at the Siberian archaeological site of Mal'ta lived around24000 years ago. The Yana samples are several thousand years older and come from a different northern location.",
86:'Genetic comparisons connect these ancient histories within a wider northern Eurasian background. The groups were not identical, and the evidence does not identify a single known group travelling together.',
88:'Human population histories include both separation and mixing of inherited genetic ancestry. A diagram may therefore need both branches and additional connections, while still lacking many ancient samples.',
89:'One sampled ancient individual is different from the ancestral population investigated using that sample. The individual provides evidence but does not perfectly represent everyone in the population.',
90:'A line between two sampled places on a map may indicate shared genetic ancestry. It does not automatically indicate direct movement from one place to the other.',
91:'An older related individual is not automatically the direct ancestor of every younger individual. The older sample may represent a related branch near the relevant ancestral population.',
93:"Comparing Yana and the Siberian archaeological site of Mal'ta adds different views of northern history. Differences between them are informative evidence, rather than an obstacle to ignore."
}
def source_text(ch):
 rows=[r for r in P.source if r['start']>=int(ch['start_seconds']) and r['end']<=int(ch['end_seconds'])]
 text=' '.join(OVERRIDES.get(r['id'],r['voice']) for r in rows)
 text=re.sub(r'\bhide\b','animal skin',text);text=re.sub(r'\bhides\b','animal skins',text)
 for a,b in P.NUMBERS.items():text=text.replace(a,b)
 return text

def run(loc):
 p=S/f'{loc}.json';rows=json.loads(p.read_text());marker=S/f'{loc}.review-clarity-v3'
 if marker.exists():return loc
 for n in [1,2,5,6,7]:
  en=source_text(P.chapters[n]);out=P.adapt(P.translate(en,P.LANGS[loc]),loc);assert out.strip()
  norm=re.sub(r'[.,\s\u00a0\u202f]','',out)
  for y in ['2001','2019']:
   if y in en and y not in norm:raise ValueError((loc,n,y))
  rows[n]['voice']=out;rows[n]['source_en']=en;rows[n]['clarity_review']='Ambiguous archaeological/genetic metaphors faithfully disambiguated before translation'
  print(json.dumps({'clarity_review':loc,'chapter':n+1}),flush=True);time.sleep(1)
 p.write_text(json.dumps(rows,ensure_ascii=False,indent=2));p.with_suffix('.txt').write_text('\n\n'.join(x['voice'] for x in rows));p.with_suffix('.terminology-v2').write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'\n');marker.write_text('Known misleading literal translations corrected; native editorial/listening review remains pending.\n');return loc
if __name__=='__main__':
 langs=[l for l in P.LANGS if l not in ['mww','vi-VN']]
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  fs={pool.submit(run,l):l for l in langs};errors=[]
  for f in concurrent.futures.as_completed(fs):
   try:print('REVIEW_READY',f.result(),flush=True)
   except Exception as e:errors.append(fs[f]);print('REVIEW_ERROR',fs[f],repr(e),flush=True)
 if errors:raise SystemExit(1)
