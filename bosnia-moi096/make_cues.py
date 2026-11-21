import json,re
from pathlib import Path
R=Path(__file__).parent;C=json.loads((R/'EPISODE.json').read_text())
visuals=[
'''macro|One pale sandstone slab with an existing angular fracture, tiny sediment bands visible; the illustrative opening object remains fixed.
field|A low exposed rock layer in the foreground and a wooded angular hill beyond in a plausible central Bosnian valley.
model|Separate outdoor comparison models of a continuous natural hill and a small assembled wall, no giant built pyramid.
field|Anonymous adult observer follows the continuous edge of a rock layer without touching or removing material.
macro|Thin natural sediment band crosses the slab and continues into adjoining solid rock beyond the fracture.
landscape|Wide green central Bosnian valley with a town in the middle distance, forested slopes and a river corridor.
heritage|Modest weathered medieval wall remains on a wooded summit, an illustrative regional heritage setting without invented exact Visoki floor plan.
model|A tiny medieval wall comparison sits on the surface of a much larger natural layered hill model, clearly different scales.
heritage|Close-to-wide view of low masonry remains standing on natural bedrock, no pyramid beneath the historic wall.
landscape|An angular wooded hill seen across the valley from a plausible visitor viewpoint, ordinary irregular natural slopes.
macro|Two separate comparison replicas on an outdoor support: naturally fractured stone and deliberately laid masonry stone, no text.
macro|The camera reveals the surrounding rock attached behind the natural slab replica while the separate wall stone has visible placement contacts.
model|Three outdoor teaching objects: an irregular hill relief, a layered rock section, and a small assembled wall, all unlabelled.
field|An adult observer compares the hill profile with a nearby undisturbed outcrop from an established path.
macro|The same thin sediment band continues smoothly from the opening slab into its neighboring rock.
field|A low tracking view follows the continuous band along the outcrop into the ground.
model|Close on the support and contacts of a deliberately assembled small wall comparison model.
model|Natural layer and assembled wall remain separate while the camera changes angle to reveal their different boundaries.
heritage|A small old wall sits on an older natural ledge in a clearly illustrative outdoor comparison.
landscape|The wooded triangular hillside from a valley path, with a second ordinary ridge visible beyond.''',
'''landscape|A wooded angular hill framed from one low viewpoint, two slopes converging in perspective without perfect geometric symmetry.
landscape|Slow lateral movement lets a second ridge enter the hill silhouette, maintaining physically plausible parallax.
field|An adult walker pauses on a valley path and turns toward another viewpoint of the same illustrative hill.
landscape|The less familiar side of the hill reveals gullies, uneven ridges, and irregular vegetation across the slopes.
field|Anonymous adult sets an unbranded surveying instrument on an established path; its display faces away and shows no data.
field|A survey prism and distant hill share the frame, equipment physically plausible and all scales unreadable.
landscape|A naturally north-facing-looking forested slope under neutral light, with no compass graphic or claimed measured alignment.
model|A simple layered hillside relief beside a separate small masonry model, no ideal pyramid template.
model|Tilted resistant layers project through a hillside teaching model while adjacent weaker bands sit lower.
landscape|A steep rocky ridge rises above a lower vegetated strip in an outdoor erosion comparison landscape.
landscape|A small river corridor runs between two wooded hills in a green valley.
field|Shallow rainwater travels along an existing soil channel below a resistant rock ledge; no instant catastrophic erosion.
model|A triangular exposed edge narrows along a resistant tilted layer in a simplified outdoor hillside model.
model|A continuous camera arc reveals the same model's outline changing from triangular to irregular.
field|An adult observer stands below the slope on a path, looking between the rock underfoot and the hill above.
model|An unlabelled terrain relief and an open rock section occupy the same outdoor table, no measured digital elevation data.
landscape|Three neighboring irregular wooded hills seen in one wide frame, each with distinct slopes and gullies.
landscape|A lateral reveal shows the less symmetrical side of the main illustrative hill and its connection to a ridge.
model|The small outdoor erosion model stays visibly a teaching object, separate from the real surrounding landscape.
macro|The lens approaches a gravel-rich stone surface with rounded pebbles embedded in a fine matrix.''',
'''macro|Rounded pebbles remain embedded in a pale fine matrix within a stable conglomerate comparison specimen.
macro|Oblique close-up shows many pebble sizes and natural mineral binding within the same conglomerate replica.
macro|Three separate comparison replicas show coarse conglomerate, granular sandstone, and fine mud-rich rock outdoors.
deep_time|Illustrative ancient river carries gravel into a shallow sedimentary basin, no people, structures, or animals.
model|A separate outdoor depositional model displays loose sediment beside its compacted and mineral-bound comparison stage.
macro|Natural pale mineral material fills spaces among grains in a rock replica, credible non-glowing texture.
macro|The natural conglomerate replica remains fixed as daylight reveals the binding matrix around its pebbles.
field|An extended outcrop alternates conglomerate-like coarse layers with sandstone and fine sediment bands.
field|A measured camera move follows the same coarse material from a small surface into the adjoining continuous layer.
field|Wide-to-close view preserves the layer above, the sample-like patch, and the layer below in one outcrop.
macro|A natural conglomerate replica and a deliberately cast comparison block remain separate on an outdoor bench.
macro|Focus shifts between the two comparison textures without morphing either specimen or asserting a scientific identification.
macro|Close view follows one embedded pebble into its surrounding fine matrix on the natural comparison specimen.
field|A sharp camera angle reveals the sediment boundary around the coarse layer instead of isolating one rectangular fragment.
model|Two inert comparison specimens of different shapes rest beside an unbranded outdoor loading-frame teaching prop, no operating test or numeric result.
macro|Strong-looking natural rock and visibly artificial cast material are compared visually without strength numbers or graphs.
field|Adult hands position sealed unlabelled comparison containers near a nondestructive outcrop observation station.
macro|A single embedded pebble and the matrix surrounding it fill the frame in raking outdoor daylight.
macro|The specimen's texture and its enclosing boundary remain in the same focus plane, no claimed original sampled artifact.
macro|Existing intersecting fractures divide a sandstone comparison slab into angular pieces without new breakage.''',
'''macro|Two existing straight fractures intersect in a pale sandstone layer, defining a sharply angular natural block.
macro|A stable natural joint plane continues through a continuous rock layer, no mortar, tool, or new cracking action.
model|Separate outdoor stages show a continuous sediment layer and its later fractured counterpart, no morphing or real-time tectonic event.
macro|Matching sediment bands remain aligned across a narrow existing fracture in an illustrative rock comparison.
field|A camera track follows related fractures from the foreground slab into the same surrounding outcrop.
macro|Angular fracture edges show plausible mineral grains and weathering, no fabricated chisel marks.
field|Soil above tilted natural ledges creates a step-like exposed profile on an illustrative hillside.
model|A cutaway through the hillside teaching model reveals continuous tilted layers behind apparent surface paving.
model|A separately laid stone pavement model sits beside a continuous sedimentary layer model, both outdoors.
macro|Camera glides from the flat top to the edge of each separate comparison surface, retaining their different internal structures.
macro|Three separate replica gaps show mineral filling, loose soil, and a masonry contact without labels or analytical claims.
field|A low view keeps boundaries above and below a fracture visible in one undisturbed outcrop.
model|Side view of an outdoor section model shows thin layers continuing behind step-like ledges.
field|A documented-looking educational excavation replica has exposed ledges and an undisturbed margin; adult observer stands outside it.
model|Two separate before-and-after teaching models show how removal changes a visible surface, not actual site damage.
macro|Two inert comparison surfaces show a plausible worked stone face and a natural fracture, no assertion either was recovered at Visoko.
heritage|An illustrative rough-stone dry wall has credible support contacts and irregular unworked pieces, no mortar required.
macro|Close view follows the corner of a laid wall stone to its bearing contact and supporting stones.
field|The camera widens from one attractive fracture to the full outcrop and the adjacent ground.
heritage|A small deliberately assembled wall comparison and a continuous natural rock layer occupy distinct outdoor supports.''',
'''history|Clearly adult medieval regional mason sets a modest stone into a small ordinary wall, no pyramid project or exact Visoki reconstruction.
history|The same adult mason checks the contact between two rough stones in a modest regional medieval building illustration.
model|An outdoor section model shows a foundation cut, laid stones, and a later deposit meeting the wall.
model|Four separate physical teaching stages show prepared ground, laid wall, occupied surface, and later partial burial.
heritage|An adult observer follows the base of a small illustrative wall without moving stones or entering fragile ruins.
model|The wall base truncates a replica soil boundary in a separate educational section model.
field|A natural rock ledge continues behind its exposed edge into a coherent outcrop.
heritage|A small illustrative wall rests directly on an existing natural ledge, with both masonry and rock clearly visible.
model|A simple natural hill model supports a tiny later wall on its summit, retaining the difference in scale.
heritage|Modest medieval wall remains on natural summit bedrock, plausible Bosnia regional setting and no invented monument plan.
model|The camera reveals that a small wall comparison occupies only a small part of the full hillside relief.
model|A larger outdoor construction-sequence teaching object displays connected foundation boundaries, arranged stone, and a working surface.
field|Adult hands compare physical model positions over a completely blank field-board surface with no drawn lettering or measurements.
heritage|A modest later terrace and field boundary on an illustrative hillside, clearly smaller than the whole natural landform.
field|An ordinary shallow field edge lies beside a bedrock outcrop, no grand architectural implication.
history|Adult regional medieval workers build a modest rough-stone wall using ordinary baskets and hand tools, no exact historical reconstruction claim.
heritage|A wall base, adjacent occupation-surface replica, and small inert pottery replica form a coherent outdoor teaching scene.
model|Three separate teaching stages show wall placement, use, and later burial with no dates or clocks.
heritage|Rough dry-stone masonry rests on credible supports in natural daylight, no universal construction pattern implied.
macro|One small charcoal comparison fragment rests within an inert soil section replica between two stones.''',
'''macro|A charcoal comparison fragment remains within a clearly illustrative intact soil section beside stones.
macro|Separate sandstone comparison specimen and charcoal replica remain distinct on an outdoor support.
model|Three unlabelled physical stages depict sedimentary rock, organic material, and a later stone wall, no numbered timeline.
model|The camera moves across those three separate stages while each retains its own boundaries and material identity.
macro|A small charcoal comparison fragment beside a separate dry twig, no laboratory equipment or false analytical result.
history|Clearly adult generic premodern craft worker handles stored wood beside an ordinary outdoor hearth, no dated Visoko event claim.
model|Separate tree-growth, dry-wood, charcoal, and soil-context teaching props remain inert outdoors, no animated numeric ages.
field|Adult observer studies a replica bounded deposit beside a laid stone comparison wall, without collecting real material.
model|A sealed layer beneath a small wall is compared with loose material in an open crack above it, visibly separate model compartments.
macro|The charcoal replica stays in its original teaching-model pocket while camera reveals all surrounding boundaries.
model|A later cut crosses an earlier soil-layer replica, contact physically legible without text.
model|A prepared educational section shows a root channel and a separate later cut crossing earlier layers, no automatic real-site interpretation.
model|Camera follows the edges of a later filled cut through an older model layer on an outdoor table.
model|Three separate layer sequence models show relative earlier and later events without calendar graphics.
macro|Rock specimen, charcoal replica, and masonry contact remain distinct objects with no implied shared birthday.
model|A small comparison fragment placed near a wall is visibly separated from the actual foundation-context model.
history|A modest regional dwelling illustration shows repair to an ordinary wall by clearly adult workers, no claimed specific phase at Visoko.
heritage|An illustrative small wall occupies an older natural hillside with multiple visible geological layers beneath it.
field|An inert soil-context replica remains undisturbed, adult observer keeps hands away from the fragile contact.
field|A modest passage entrance in a wooded hillside, generic illustrative setting with no claim to reproduce a real Ravne portal.''',
'''field|From an established path, a modest generic passage entrance appears in a wooded natural slope, no grand gateway.
model|An outdoor passage cutaway model shows rock, passage boundary, fill, and a small later support separately.
model|A narrow passage is cut through a much larger natural hill teaching model, without converting the hill into architecture.
field|Adult observer maps a generic illustrative passage entrance using an unbranded instrument, display and notes face away.
macro|A cutaway replica shows the contact between the passage boundary and the natural rock layers it crosses.
model|A clear outdoor model shows a passage truncating a continuous pre-existing layer.
model|A later small wall partly closes a passage within a separate outdoor teaching model.
model|Three separate physical stages depict natural rock, cut passage, and subsequent infill, no exact real tunnel chronology.
landscape|A natural hill and a separate modest passage entrance occupy different parts of a wooded landscape, no connecting graphic.
model|Two unlabelled proposed routes are separate removable model pieces rather than a revealed actual underground network.
field|Unbranded ground-penetrating-radar cart travels slowly on an open field path, screen turned away and no invented trace.
model|A simple outdoor section model includes contrasting sediment, damp soil, and a small void, no fake radar color plot.
field|Clearly adult field operator follows a measured-looking straight path with an unbranded instrument, no visible scale values.
model|The camera follows a section's material boundaries, with no glowing chamber, treasure, or invented analytical data.
field|An adult observer compares the surface location with an inert outdoor ground-section model, no drilling or excavation.
field|A plain generic passage threshold shows surrounding soil and rock plus a modest modern maintenance support, no age attribution.
macro|The passage model's cut surface, later fill, and separate support remain legible in close-up.
model|The hill and passage models remain separate while the camera reveals the missing physical connection between them.
field|The generic passage entrance remains modest, still, and physically separate from any claimed monument.
field|An outdoor table holds a closed plain folder beside rock and wall models, no readable page, seal, journal cover, or fake document.''',
'''field|A closed plain research folder rests outdoors beside a natural outcrop comparison, no readable author name or simulated paper.
model|Physical hill relief, orientation rod, and rock comparison are separate props on a field table, no graphs or numbers.
field|Unbranded survey equipment faces an irregular wooded slope, all screens and scales unreadable.
macro|A natural rock comparison specimen rests beside a sealed unlabelled sample container at an outdoor observation station.
field|Clearly adult observer matches the physical specimen-like patch to a nearby undisturbed layer without removing material.
field|Two anonymous adult observers separately inspect the same inert comparison model from established positions, no named expert portrayal.
macro|One unchanged angular block remains in view as the camera reveals its full context rather than duplicating it into many specimens.
field|Plain closed folders remain beside physical comparison models, no portraits, academic logos, or readable publication text.
model|A physical construction-sequence model exposes foundation, placed stones, and later deposits in one coherent outdoor frame.
landscape|A quiet path and irregular wooded hill provide an ordinary visitor setting, all visible people absent or clearly adult.
heritage|Modest regional medieval ruins under careful conservation, no readable heritage plaque or invented institutional certification.
field|Adult observer studies an intact margin beside a teaching excavation replica; no damage to a genuine archaeological site.
model|Three separate outdoor comparison objects depict terrain, a layered rock section, and a deliberately assembled wall.
model|Camera glides around the three models so their different material relationships remain physically visible.
field|Continuous layers, natural fractures, and a small erosion gully coexist in an illustrative natural outcrop.
heritage|A separate small wall comparison shows arranged stones, a meaningful base, and an adjoining occupation-surface replica.
field|An adult observer revisits the same rock layer in changed natural light, no changed sample or newly revealed treasure.
model|The camera returns from a hill silhouette model to the physical boundaries in its open section.
landscape|An irregular wooded natural hill rises above a valley, without exposed giant pyramid faces or artificial casing.
heritage|A low medieval wall ruin occupies a natural summit, inviting a closer archaeological view.''',
'''heritage|Low weathered regional medieval masonry on a wooded summit, not a surveyed reconstruction of the full Visoki stronghold.
heritage|The camera keeps the modest historic wall and the much larger natural hill separate in scale, no UNESCO logo or sign.
heritage|Adult observer follows a visible wall base from a safe path without touching or moving stones.
model|A small medieval wall comparison model includes an ordinary entrance gap and successive wall contacts, not an exact site plan.
field|Outdoor teaching station with a blank plan board, inert pottery replica, and section model, no text or invented records.
field|A careful-looking educational trench replica on a plateau has intact margins; clearly adult observers stand outside it.
macro|Several separately arranged inert pottery comparison replicas represent different periods without labels or claimed site attribution.
macro|One undecorated pottery replica remains in a clearly illustrative bounded soil layer.
macro|Slow focus shift keeps the pottery replica and the boundary of its deposit visible together.
model|Two separate teaching scenes compare the fragment in context and a loose comparison fragment, no movement of real finds.
field|An intact margin in an educational section replica remains preserved beside the observed portion.
landscape|An undisturbed grassy patch beside a wooded plateau path, adult observer pauses at a respectful distance.
heritage|Quiet conserved low ruins blend with the surrounding landscape, no display case or laboratory.
landscape|Wide Bosnian valley with wooded hills and modest distant settlement, no crowds or fantasy monuments.
history|Clearly adult regional medieval potter works beside a modest dwelling in an illustrative outdoor scene, not a reconstructed documented individual.
heritage|An established path allows a safe view toward low historic masonry and the valley beyond.
landscape|Summit view connects a modest masonry foreground to the wider valley on an older natural hillside.
model|A layered natural hill teaching model supports a very small later wall, both histories visible without merging them.
field|Undisturbed ground beside the replica excavation remains intact, no promised undiscovered chamber or artifact.
macro|Return to the exact same illustrative opening sandstone slab and its stable angular corner.''',
'''macro|The opening slab retains the same angular fracture, grains, and thin sediment band in matching natural daylight.
macro|Camera widens slightly to reveal the slab's continuous surrounding layer rather than an isolated cut-looking block.
macro|Raking light shows grains, natural binding matrix, and a pre-existing fracture in the same comparison slab.
field|Camera pulls back from the opening outcrop to the wooded hill and valley, maintaining modest natural terrain scale.
model|An irregular hill silhouette model connects to its open section with continuous natural rock layers.
field|A natural outcrop combines sediment layers, existing fractures, and weathered slopes without engineered pyramid casing.
heritage|A separate small wall comparison reveals a construction base, placed stones, and an adjoining surface replica.
heritage|Modest medieval remains occupy natural summit bedrock, no invented ancient megastructure underneath.
model|The camera follows the full sequence in separate natural-layer and assembled-wall comparison models.
landscape|A natural wooded hill with an ordinary summit heritage setting, no false discovery reveal.
model|The three comparison models return together: natural terrain, layered rock section, small assembled wall.
model|Distinct boundaries show continuous natural layering beside separately laid masonry stones.
macro|Separate rock, charcoal, and small masonry-contact teaching props remain distinct, no visible ages or clocks.
field|Two anonymous adult observers inspect an intact educational model from different sides, notes and displays unreadable.
macro|The opening stone's corner and thin sediment band remain stable, revealing tangible details without magical transformation.
field|A close-to-wide camera move connects stone edge, outcrop, and natural hillside in one continuous motion.
landscape|The wooded valley is seen under restrained warm side light, ordinary geological beauty without fantasy architecture.
macro|The opening slab remains untouched as nearby grasses move gently in the breeze.
landscape|A modest archaeological heritage landscape and intact surrounding ground share a quiet final frame.
field|An undisturbed grassy patch beside the original outcrop, no new object revealed and no promised buried treasure.'''
]
parts=re.split(r'^## .+\n',(R/'SCRIPT_MASTER.txt').read_text(),flags=re.M)[1:];rows=[];t=0
def allocation(lines,target,fixed):
 weights=[len(re.findall(r"\b[\w'-]+\b",x)) for x in lines];ideal=[w/sum(weights)*target for w in weights]
 ds=[max(3,min(10,round(v))) for v in ideal]
 for i,v in fixed.items():ds[i]=v
 while sum(ds)!=target:
  step=1 if sum(ds)<target else -1;valid=[i for i in range(len(lines)) if i not in fixed and 3<=ds[i]+step<=10]
  assert valid
  k=min(valid,key=lambda i:(ds[i]+step-ideal[i])**2-(ds[i]-ideal[i])**2);ds[k]+=step
 return ds
for section,(part,plan,seconds) in enumerate(zip(parts,visuals,C['section_seconds']),1):
 lines=[x for x in part.splitlines() if x.strip()];scene=plan.splitlines();assert len(lines)==len(scene)==20,(section,len(lines),len(scene))
 first=seconds//2;second=seconds-first
 durations=allocation(lines[:10],first,{0:10} if section==1 else {})+allocation(lines[10:],second,{8:7,9:4 if section==10 else 5})
 for i,(voice,vis,dur) in enumerate(zip(lines,scene,durations)):
  mode,visual=vis.split('|',1);kind='rehook' if i in (0,10) else 'caveat' if i==18 else 'turn' if i==19 else 'scene' if i in (3,13) else 'narration'
  rows.append(dict(id=len(rows)+1,section=section,start=t,end=t+dur,kind=kind,voice=voice,visual=visual,mode=mode));t+=dur
assert len(rows)==C['english_cues'] and t==C['target_seconds'] and all(not re.search(r'\d',x['voice']) for x in rows)
(R/'CUES_MASTER.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
(R/'CUES_MASTER.tsv').write_text('\n'.join('\t'.join(map(str,[x['id'],x['section'],x['start'],x['end'],x['kind'],x['voice'],x['visual'],x['mode']])) for x in rows)+'\n')
print('CUES_READY',len(rows),'seconds',t,'words',sum(len(re.findall(r"\b[\w'-]+\b",x['voice'])) for x in rows))
print('DURATIONS',sorted({x['end']-x['start'] for x in rows}))
print('FIRST',[(x['id'],x['start'],x['end']) for x in rows[:5]])
print('PACING_EXTREMES',[(x['id'],x['end']-x['start'],len(x['voice'].split())) for x in rows if not 1.7<=len(x['voice'].split())/(x['end']-x['start'])<=3.7])
