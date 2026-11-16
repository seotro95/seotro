"""Build the reviewable Ollantaytambo 004 document package; no external dependencies."""
from pathlib import Path
import argparse, csv, hashlib, json, shutil, zipfile
P = Path(__file__).resolve().parent
VOICES = {
"en": ("en-US", "en-US-AndrewNeural"), "vi": ("vi-VN", "vi-VN-NamMinhNeural"),
"es": ("es-ES", "es-ES-AlvaroNeural"), "fr": ("fr-FR", "fr-FR-HenriNeural"),
"ja": ("ja-JP", "ja-JP-KeitaNeural"), "ko": ("ko-KR", "ko-KR-InJoonNeural"),
"de": ("de-DE", "de-DE-ConradNeural"), "it": ("it-IT", "it-IT-DiegoNeural"),
"pt": ("pt-PT", "pt-PT-DuarteNeural"), "nl": ("nl-NL", "nl-NL-MaartenNeural"),
"pl": ("pl-PL", "pl-PL-MarekNeural"), "sv": ("sv-SE", "sv-SE-MattiasNeural"),
"da": ("da-DK", "da-DK-JeppeNeural"), "fi": ("fi-FI", "fi-FI-HarriNeural"),
"no": ("nb-NO", "nb-NO-FinnNeural"), "cs": ("cs-CZ", "cs-CZ-AntoninNeural")}
LABELS = {"en":"English","vi":"Viet_Nam_Nam_Minh","es":"Tay_Ban_Nha","fr":"Phap","ja":"Nhat",
"ko":"Han","de":"Duc","it":"Y","pt":"Bo_Dao_Nha","nl":"Ha_Lan","pl":"Ba_Lan",
"sv":"Thuy_Dien","da":"Dan_Mach","fi":"Phan_Lan","no":"Na_Uy","cs":"Sec"}
def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))
def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
def validated(rows, field):
    if isinstance(rows, dict):
        rows = rows.get("rows", rows.get("scenes", rows.get("prompts", [])))
    assert len(rows) == 131, (field, len(rows))
    assert [int(r["id"]) for r in rows] == list(range(1,132)), field
    assert all(isinstance(r.get(field), str) for r in rows), field
    return rows
def tc(seconds, srt=False):
    h, rem = divmod(int(seconds),3600)
    m, s = divmod(rem,60)
    if srt:
        return f"{h:02}:{m:02}:{s:02},000"
    return f"{m:02}:{s:02}" if not h else f"{h:02}:{m:02}:{s:02}"
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",default="outputs/documents")
    args=parser.parse_args()
    out=Path(args.out)
    out.mkdir(parents=True,exist_ok=True)
    master=validated(read(P/"script_master.json"),"en")
    assert all(r["en"].strip() and r["vi"].strip() for r in master[:130])
    assert not master[130]["en"].strip() and not master[130]["vi"].strip()
    prompts=validated(read(P/"scene_prompts.json"),"text")
    assert all("Video không có âm thanh, không có lời nói." in r["text"] for r in prompts)
    assert all(("Không có trẻ em" in r["text"] or "không có trẻ em" in r["text"]) for r in prompts)
    translations={"en":[{"id":r["id"],"text":r["en"]} for r in master],
                  "vi":[{"id":r["id"],"text":r["vi"]} for r in master]}
    for lang in VOICES:
        if lang not in translations:
            rows=validated(read(P/"translations"/f"{lang}.json"),"text")
            assert all(r["text"].strip() for r in rows[:130]) and not rows[130]["text"].strip(),lang
            translations[lang]=rows
    for lang, rows in translations.items():
        filename=f"004_{lang}_{LABELS[lang]}"
        plain="\n\n".join(r["text"] for r in rows if r["text"].strip())+"\n"
        write(out/"05_VOICE_TEXTS"/f"{filename}.txt",plain)
        timed="\n\n".join(f'{r["id"]:03} | {tc((r["id"]-1)*10)} | {r["text"]}' for r in rows)
        write(out/"05_VOICE_TEXTS"/f"{filename}_timed.txt",timed+"\n")
        cues=[]
        for r in rows:
            n=int(r["id"]); start=(n-1)*10; end=n*10 if n<131 else 1302
            cues.append(f'{n}\n{tc(start,True)} --> {tc(end,True)}\n{r["text"]}')
        write(out/"06_SRT_SCENE_REFERENCE"/f"{filename}.srt","\n\n".join(cues)+"\n")
        chapters=[]
        for group in range(22):
            first=group*6
            last=min(first+6,130)
            text=" ".join(r["text"] for r in rows[first:last])
            start=group*60
            end=start+(59.75 if group<21 else 39.75)
            def stamp(value):
                millis=round(value*1000)
                hh,rem=divmod(millis,3600000);mm,rem=divmod(rem,60000);ss,ms=divmod(rem,1000)
                return f"{hh:02}:{mm:02}:{ss:02},{ms:03}"
            chapters.append(f"{group+1}\n{stamp(start)} --> {stamp(end)}\n{text}")
        chapters.append("23\n00:21:39,750 --> 00:21:42,000\n")
        write(out/"07_SRT_MELO_EXACT"/f"{filename}_23cues.srt","\n\n".join(chapters)+"\n")
    write(out/"01_SCRIPT_EN.txt","\n\n".join(r["en"] for r in master if r["en"])+"\n")
    write(out/"02_KICH_BAN_VI.txt","\n\n".join(r["vi"] for r in master if r["vi"])+"\n")
    write(out/"03_MASTER_SCRIPT.json",json.dumps(master,ensure_ascii=False,indent=2)+"\n")
    counts=[]
    for batch,start in enumerate(range(0,131,10),1):
        end=min(start+10,131)
        header=("004. OLLANTAYTAMBO — ENGLISH MAIN VIDEO\n"
                "Lịch dựng 21:42. Mỗi prompt tạo một clip 10 giây; cảnh131 dùng 2 giây đầu.\n"
                "VOICE là lời tham chiếu để ghép sau. Chỉ đưa dòng PROMPT vào công cụ tạo video.\n"
                "Hình có người chỉ dùng người trưởng thành từ25tuổi. Nhãn giả thuyết thêm khi dựng.\n\n")
        chunks=[]
        for i in range(start,end):
            r=master[i]; n=int(r["id"]); final=n==131
            span=f'{tc(i*10)}–{tc(1302 if final else (i+1)*10)}'
            chunks.append(f'{n}.\nTIMELINE: {span}; GENERATE: 10s; USE: {2 if final else 10}s\n'
                          f'VOICE EN: {r["en"] or "[Silence]"}\n'
                          f'VOICE VI: {r["vi"] or "[Im lặng]"}\n'
                          f'PROMPT: {prompts[i]["text"]}\n')
        write(out/"04_VIDEO_PROMPTS"/f"{batch:02}_prompts_{start+1:03}-{end:03}.txt",header+"\n".join(chunks))
        counts.append(end-start)
    assert counts==[10]*13+[1],counts
    with (out/"04_STORYBOARD.csv").open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.writer(f)
        writer.writerow(["id","start","end","generate_seconds","used_seconds","voice_en","voice_vi","video_prompt","evidence"])
        for i,r in enumerate(master):
            n=i+1
            writer.writerow([n,tc(i*10),tc(n*10 if n<131 else 1302),10,10 if n<131 else 2,
                             r["en"],r["vi"],prompts[i]["text"],r.get("evidence","See prompt/source notes")])
    titles=read(P/"titles_thumbnails.json")
    if isinstance(titles,dict): titles=titles.get("items",titles.get("titles",[]))
    assert len(titles)==5
    blocks=[]
    for i,t in enumerate(titles,1):
        title_en=t.get("title_en",t.get("en",""));title_vi=t.get("title_vi",t.get("vi",""))
        prompt=t.get("prompt",t.get("thumbnail_prompt",""))
        assert title_en and title_vi and prompt
        blocks.append(f'{i}. EN: {title_en}\nVI: {title_vi}\n'
                      f'HEADLINE EN: {t.get("headline_en","")}\nHEADLINE VI: {t.get("headline_vi","")}\n'
                      f'THUMBNAIL PROMPT: {prompt}\n')
    write(out/"08_TITLES_THUMBNAILS.txt","\n".join(blocks))
    for src,dst in [("research.md","09_NGHIEN_CUU_VA_NGUON.md"),("source_video_notes.md","10_VIDEO_NGUON_VA_NHIP_DUNG.md")]:
        if (P/src).is_file():shutil.copy2(P/src,out/dst)
    profile={"episode":"004-ollantaytambo","target_seconds":1302,"main_language":"en",
             "provider":"Original Melo + Viet Studio1.3.1 online backend via edge-tts7.3.1",
             "native_rate":"+0%","native_pitch":"+0Hz","style":"friendly",
             "voices":{locale:voice for locale,voice in VOICES.values()}}
    voice_dir=out.parent/"voices"
    verified=(voice_dir/"VOICE_PROFILES_LOCKED.json").is_file()
    if verified:
        profile=read(voice_dir/"VOICE_PROFILES_LOCKED.json")
    write(out/"VOICE_PROFILES_LOCKED.json",json.dumps(profile,ensure_ascii=False,indent=2)+"\n")
    if (voice_dir/"MANIFEST.json").is_file():shutil.copy2(voice_dir/"MANIFEST.json",out/"VOICE_AUDIO_MANIFEST.json")
    readme="""# 004. Ollantaytambo — bộ sản xuất 21:42

Tiếng Anh là bản video chính. Có16bản lời đọc: Anh, Việt (Nam Minh), Tây Ban Nha, Pháp, Nhật, Hàn, Đức, Ý, Bồ Đào Nha, Hà Lan, Ba Lan, Thụy Điển, Đan Mạch, Phần Lan, Na Uy, Séc.

- 131prompt theo thứ tự, chia14TXT:13tệp×10prompt và tệpcuối1prompt.
- Mỗi clip tạo10giây. Dùng đủ10giây cảnh1–130; cảnh131 dùng2giây đầu:1302giây=21:42.
- Mỗi prompt quy định rõ video không âm thanh, không lời nói và không có trẻ em. Mọi người được thể hiện đều trưởng thành từ25tuổi.
- VOICE EN/VI trong tệp prompt chỉ cung cấp bối cảnh. Giọng đọc được ghép ở hậu kỳ; không yêu cầu công cụ tạo video đọc lời.
- Cảnh Inca là phục dựng giáo dục, Andes thế kỷXV. Cơ chế chưa được chứng minh được gọi là giả thuyết, không phải tư liệu quay lịch sử.
- Các nhãn bản đồ, số liệu và chữ thumbnail nên thêm trong phần mềm dựng, tránh để công cụ hình ảnh tự vẽ chữ.
- Nguồn MP4 GitHub được xác định bằng metadata nhưng chưa xem/đo trực tiếp do lỗi máy Cloud. Phương án này theo công thức sản xuất do người dùng cung cấp; không gán các nhận xét dựng cho video nguồn.
- 06_SRT_SCENE_REFERENCE là lịch tham chiếu cảnh10giây, không phải thời gian từng từ đã đo từ audio.
- 07_SRT_MELO_EXACT là23cue dùng lại trong Melo:21chương60giây,40giây lời cuối và2giây kết im lặng.
- Pipeline audio căn theo22chương, nên các ngôn ngữ chung tổngthời lượng và mốc chương; không mặc nhiên khớp từng từ hoặc từng ranh giới10giây.
- Giữ đúnglocale, voiceID và thông số trong VOICE_PROFILES_LOCKED.json cho tập tiếp theo.
- WAV tiếng Anh là bản chuẩn dựng;16M4A là các bản voice riêng. Chỉ coi audio đã hoàn tất khi gói chứa tệp âm thanh và MANIFEST đã kiểm tra.
- Không cắt lời để ép thời lượng; pipeline đo âm thanh, thay đổi tốc độ giữ cao độ, rồi thêm khoảng lặng ngắn.
- Các bản dịch được biên soạn cho lời kể bản địa. Tên địa danh được giữ ổn định; tránh coi hình minh họa là bằng chứng.
"""
    write(out/"00_DOC_TRUOC.md",readme)
    repro=out/"11_REPRODUCE"
    repro.mkdir(parents=True,exist_ok=True)
    for name in ["build_documents.py","render_voices.py","requirements.txt","script_master.json","scene_prompts.json","titles_thumbnails.json"]:
        if (P/name).is_file():shutil.copy2(P/name,repro/name)
    for folder in ["translations","vendor"]:
        if (P/folder).is_dir():shutil.copytree(P/folder,repro/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns("__pycache__","*.pyc"))
    manifest={"episode":"004-ollantaytambo","target_seconds":1302,"scene_count":131,
              "prompt_txt_count":14,"prompt_counts":counts,"languages":list(VOICES),
              "english_word_count":sum(len(r["en"].split()) for r in master),
              "main_language":"en","source_video_viewed":False,
              "audio_profile_file_present":verified,"documents_complete":True}
    write(out/"PACKAGE_MANIFEST.json",json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    hashes=[]
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name!="SHA256SUMS.txt":
            hashes.append(hashlib.sha256(path.read_bytes()).hexdigest()+"  "+path.relative_to(out).as_posix())
    write(out/"SHA256SUMS.txt","\n".join(hashes)+"\n")
    archive=out.parent/"004_Ollantaytambo_Documents.zip"
    with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as z:
        for path in sorted(out.rglob("*")):
            if path.is_file():z.write(path,path.relative_to(out))
    print(json.dumps({"documents_complete":True,"scene_count":131,"prompt_txt_count":14,"languages":16,
                      "english_word_count":manifest["english_word_count"],"zip":str(archive)},ensure_ascii=False),flush=True)
if __name__=="__main__":main()
