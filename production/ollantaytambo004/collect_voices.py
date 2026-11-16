"""Assemble and revalidate sixteen independently rendered country artifacts."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,wave
LANGS=["en","vi","es","fr","ja","ko","de","it","pt","nl","pl","sv","da","fi","no","cs"]
def read(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def sha(p):
    with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--artifacts",type=Path,default=Path("work/voice_artifacts"))
    ap.add_argument("--out",type=Path,default=Path("outputs/voices"))
    args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    tracks=[];profiles=[];sources=set();proofs={};missing=[]
    for lang in LANGS:
        folder=args.artifacts/("004_voice_"+lang)
        if not (folder/"MANIFEST.json").is_file():
            missing.append(lang);continue
        m=read(folder/"MANIFEST.json")
        assert m["complete"] is True and len(m["tracks"])==1,lang
        t=m["tracks"][0]
        assert t["language"]==lang and t["word_coverage_verified"] and not t["speech_truncated"],lang
        assert t["lossless_master"]["sample_frames"]==31248000 and t["lossless_master"]["sample_rate"]==24000,lang
        audio=folder/t["file"];assert audio.is_file() and sha(audio)==t["sha256"],lang
        probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-select_streams","a:0",
            "-show_entries","stream=codec_name,sample_rate,channels,duration:format=duration","-of","json",str(audio)]))
        stream=probe["streams"][0];duration=float(stream.get("duration",probe["format"]["duration"]))
        assert abs(duration-1302)<.0001 and stream["codec_name"]=="aac" and stream["channels"]==1,lang
        assert int(stream["sample_rate"])==24000 and abs(t["duration_seconds"]-1302)<.0001,lang
        shutil.copy2(audio,args.out/audio.name)
        country_profiles=read(folder/"VOICE_PROFILES_LOCKED.json")["profiles"]
        assert len(country_profiles)==1 and country_profiles[0]["language"]==lang,lang
        profile=country_profiles[0]
        assert profile["gender"].casefold()=="male" and profile["voice_id"]==t["voice_id"],lang
        if lang=="vi":assert profile["voice_id"]=="vi-VN-NamMinhNeural"
        profiles.append(profile);tracks.append(t);sources.add(m["source_script_sha256"])
        provenance=read(folder/"TOOL_PROVENANCE.json")
        assert provenance["status"]=="complete" and provenance["original_source_modified"] is False,lang
        assert provenance["source_git_blob_sha1"]=="8df7c8375d9693bed644167290a3bb86cca705c0",lang
        proofs[lang]=provenance
        write(args.out/("TOOL_PROVENANCE_"+lang+".json"),provenance)
        for report in folder.glob("*_REPORT.json"):shutil.copy2(report,args.out/report.name)
        if lang=="en":
            wav=folder/(Path(t["file"]).stem+".wav")
            assert wav.is_file() and sha(wav)==t["lossless_sha256"]
            with wave.open(str(wav),"rb") as f:
                assert (f.getnchannels(),f.getsampwidth(),f.getframerate(),f.getnframes())==(1,2,24000,31248000)
            shutil.copy2(wav,args.out/wav.name)
    assert len(sources)<=1,"Country tracks came from different English scripts."
    if missing:
        write(args.out/"MANIFEST_PARTIAL.json",{"complete":False,"missing_languages":missing,"tracks":tracks})
        raise RuntimeError("Still missing completed voices: "+",".join(missing))
    assert len(tracks)==16 and len(list(args.out.glob("*.m4a")))==16
    manifest={"complete":True,"episode":"004-ollantaytambo","target_seconds":1302,
        "sample_exact_wav_frames":31248000,"sample_rate":24000,
        "all_requested_languages":True,"tracks":tracks,"source_script_sha256":next(iter(sources)),
        "alignment":"22 shared chapter boundaries; scene SRT files are planning references."}
    profile={"episode":"004-ollantaytambo","catalogue_verified":True,"audio_generated":True,
        "target_seconds":1302,"main_language":"en","profiles":profiles,
        "reuse":"Keep the exact locale, voice_id, native_rate and native_pitch for later episodes.",
        "alignment":"21 chapters of60seconds plus final42seconds; final2seconds without narration."}
    write(args.out/"MANIFEST.json",manifest)
    write(args.out/"VOICE_PROFILES_LOCKED.json",profile)
    write(args.out/"TOOL_PROVENANCE.json",{"status":"complete","original_melo_backend_unmodified":True,
        "source_git_blob_sha1":"8df7c8375d9693bed644167290a3bb86cca705c0","countries":proofs})
    print("VOICE_PROFILES_JSON="+json.dumps(profile,ensure_ascii=False),flush=True)
    print("AUDIO_MANIFEST_SUMMARY="+json.dumps([{"language":t["language"],"voice_id":t["voice_id"],
        "duration_seconds":t["duration_seconds"],"file":t["file"],"sha256":t["sha256"]} for t in tracks]),flush=True)
    print("VERIFIED:16 male tracks, each1302seconds, all requested languages, complete speech.",flush=True)
if __name__=="__main__":main()
