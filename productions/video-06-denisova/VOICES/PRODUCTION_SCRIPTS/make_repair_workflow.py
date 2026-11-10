import json,re
from pathlib import Path
R=Path(__file__).parent
jobs=json.load(open(R/'ORIGINAL_JOBS_FINAL.json'))['jobs'];assert all(j['status']=='completed' for j in jobs)
failed=[re.search(r'voices \(([^)]+)\)',j['name']).group(1) for j in jobs if j['name'].startswith('voices (') and j['conclusion']!='success'];assert failed
repairs=json.load(open(R/'VOICE_TIMING_REPAIRS.json'));invalid={x['locale']:x['chapters'] for x in repairs['repairs']};assert all(l in failed for l in invalid)
plan={'original_run_id':42791520378,'original_preview_verified':True,'failed_locales':failed,'invalidate_chapters':invalid}
init=(R/'job_init.py').read_text();needle="locale=sys.argv[1];mode=sys.argv[2]\n";assert needle in init
init=init.replace(needle,needle+'''repair=Path('input/REPAIR_PLAN.json')
if repair.exists() and mode=='full':
    plan=json.loads(repair.read_text());out=work/'voice/audio'/locale;out.mkdir(parents=True,exist_ok=True)
    rows=json.loads((dest/f'{locale}.json').read_text());marker=out/'raw-repair-applied.json';text_hash=hashlib.sha256(json.dumps(rows,ensure_ascii=False).encode()).hexdigest()
    previous=json.loads(marker.read_text()) if marker.exists() else {}
    if previous.get('script_hash')!=text_hash:
        for chapter in plan['invalidate_chapters'].get(locale,[]):
            for p in out.glob(f'raw-{chapter:03d}-*'):
                if p.is_file():p.unlink()
            print('Regenerating only revised chapter:',locale,chapter,flush=True)
        marker.write_text(json.dumps({'script_hash':text_hash,'original_run_id':plan['original_run_id']}))
''')
(R/'job_init_repair.py').write_text(init)
workflow=(R/'github-build/.github/workflows/siberia-final-voices.yml').read_text()
a=workflow.index('  preview:\n');b=workflow.index('  voices:\n')
workflow=workflow[:a]+'''  preview:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Reuse verified original English preview
        run: python -c "import json; p=json.load(open('input/REPAIR_PLAN.json')); assert p['original_preview_verified']; print('English30second preview already verified in original run',p['original_run_id'])"
'''+workflow[b:]
workflow=re.sub(r'        locale: \[[^\n]+\]', '        locale: ['+', '.join(failed)+']',workflow)
a=workflow.index('      - name: Restore partial audio');b=workflow.index('      - name: Render expressive narration',a)
workflow=workflow[:a]+'''      - name: Restore checkpoint from this repair attempt if present
        id: restore_own
        continue-on-error: true
        uses: actions/download-artifact@v4
        with:
          github-token: ${{ github.token }}
          run-id: ${{ github.run_id }}
          name: dn06-checkpoint-${{ matrix.locale }}
          path: build/voice/audio/${{ matrix.locale }}
      - name: Restore original checkpoint without resynthesizing completed chapters
        if: steps.restore_own.outcome == 'failure'
        uses: actions/download-artifact@v4
        with:
          github-token: ${{ github.token }}
          run-id: '42791520378'
          name: dn06-checkpoint-${{ matrix.locale }}
          path: build/voice/audio/${{ matrix.locale }}
'''+workflow[b:]
needle='''          pattern: dn06-voice-*
          path: artifacts''';assert needle in workflow
workflow=workflow.replace(needle,'''          github-token: ${{ github.token }}
          run-id: '42791520378'
          pattern: dn06-voice-*
          path: artifacts/original
      - uses: actions/download-artifact@v4
        with:
          pattern: dn06-voice-*
          path: artifacts/repair''')
entries=[dict(path='.github/workflows/siberia-final-voices.yml',mode='100644',type='blob',content=workflow),dict(path='scripts/job_init.py',mode='100644',type='blob',content=init),dict(path='input/REPAIR_PLAN.json',mode='100644',type='blob',content=json.dumps(plan,indent=2))]
for loc in failed:
 rows=json.load(open(R/'voice/scripts'/f'{loc}.json'));entries.append(dict(path=f'input/scripts/{loc}.json',mode='100644',type='blob',content=json.dumps([{k:x[k] for k in ['id','start','end','voice']} for x in rows],ensure_ascii=False)))
 if loc!='en-US':entries.append(dict(path=f'input/scripts/{loc}.terminology-v2',mode='100644',type='blob',content=(R/'voice/scripts'/f'{loc}.terminology-v2').read_text()))
for name in ['prosody.py','render_online.py']:
 entries.append(dict(path='scripts/'+name,mode='100644',type='blob',content=(R/name).read_text()))
(R/'repair-tree-entries.json').write_text(json.dumps(entries,ensure_ascii=False));(R/'REPAIR_PLAN.json').write_text(json.dumps(plan,indent=2));(R/'GITHUB_ACTIONS_REPAIR_WORKFLOW.yml').write_text(workflow);print(json.dumps({'failed_locales':failed,'entries':len(entries),'characters':len((R/'repair-tree-entries.json').read_text())}))
