from __future__ import annotations
import json
from pathlib import Path
from .subtitles import read_srt,read_txt,align_txt

LABELS={'auto':'Tự nhận diện','en':'Anh','vi':'Việt Nam','es':'Tây Ban Nha','fr':'Pháp','ja':'Nhật','ko':'Hàn','de':'Đức','it':'Ý','pt':'Bồ Đào Nha','nl':'Hà Lan','pl':'Ba Lan','sv':'Thụy Điển','da':'Đan Mạch','fi':'Phần Lan','no':'Na Uy','cs':'Séc','hmn':'H’Mông — dùng SRT tham chiếu Anh'}

def subtitle_language(cues):
    from langid.langid import LanguageIdentifier,model
    detector=LanguageIdentifier.from_modelstring(model,norm_probs=True)
    code,prob=detector.classify(' '.join(c['text'] for c in cues)[:12000])
    return {'nb':'no','nn':'no','jv':'jw'}.get(code,code),float(prob)

def visual_reference(wav,cues,job,settings,duration,ctx,original_asr):
    """English queries share the original audio clock; voice/caption text stays native."""
    from .analysis import transcribe
    requested=settings['language'];code=requested;source='user';confidence=None
    if code=='auto':
        if original_asr:
            code=json.loads((job/'transcript.json').read_text(encoding='utf-8-sig'))['language'];source='whisper'
        else:code,confidence=subtitle_language(cues);source='subtitle_estimate'
    reference=Path(settings['visual_script_path']) if settings.get('visual_script_path') else None
    meta={'detected_language':code,'language_detection_source':source,'subtitle_language_confidence':confidence,'visual_matching':'original_en','visual_alignment_ratio':None};warnings=[]
    if reference and reference.suffix.lower()=='.srt':
        meta['visual_matching']='reference_en_srt';return read_srt(reference,duration),meta,warnings
    if code=='hmn':raise ValueError('Whisper không hỗ trợ nhận dạng H’Mông đáng tin cậy. Chọn ngôn ngữ H’Mông, cung cấp SRT tiếng Anh đúng mốc ở ô Tham chiếu Anh; thêm SRT H’Mông nếu muốn phụ đề H’Mông.')
    if code!='en' or (source=='subtitle_estimate' and confidence is not None and confidence<.8):
        # A subtitle-language estimate must not force the audio decoder to speak
        # that language. It may be a translated subtitle of a different voice.
        hint=code if source in ['user','whisper'] else 'auto'
        translated=transcribe(wav,job,ctx,settings['whisper_model'],hint,settings['whisper_model_path'],settings['threads'],settings['quality']=='fast',task='translate')
        info=json.loads((job/'transcript_visual_en.json').read_text(encoding='utf-8-sig'));meta['detected_language']=info['language'];meta['language_detection_source']='whisper';meta['visual_matching']='translated_en';visual=translated
    else:visual=cues
    if reference:
        if reference.suffix.lower()!='.txt':raise ValueError('Tham chiếu Anh cần là TXT hoặc SRT tiếng Anh.')
        visual,ratio=align_txt(read_txt(reference),visual,duration);meta.update(visual_matching='reference_en_txt',visual_alignment_ratio=ratio)
        if ratio<.55:warnings.append(f'Kịch bản tham chiếu Anh chỉ khớp {ratio:.0%} lời theo mốc; hãy kiểm tra lại cảnh và phụ đề.')
    if meta['visual_matching']=='translated_en':warnings.append('Dùng bản dịch tiếng Anh theo mốc để chọn hình. Nhận dạng/dịch tên riêng và chi tiết có thể sai; nên xem các cảnh được đánh dấu.')
    return visual,meta,warnings
