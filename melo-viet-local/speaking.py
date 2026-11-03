"""Punctuation-aware pacing and explicit emphasis, without changing spoken words."""
from copy import deepcopy
import re
from documents import STYLES,split_text


def marked_parts(text,enabled):
    if not enabled:return [(text,False)]
    parts=text.split('**')
    if len(parts)%2==0:
        raise ValueError('Dấu nhấn mạnh chưa khép kín. Dùng **cụm từ** hoặc tắt Nhận dấu nhấn mạnh.')
    result=[]
    for index,part in enumerate(parts):
        if index%2 and not part.strip():raise ValueError('Chọn một cụm từ bên trong **...**, không chỉ khoảng trắng.')
        if part:result.append((part,bool(index%2)))
    return result


def paced_pieces(text,limit,expressive):
    if not expressive:return split_text(text,limit)
    # Keep short sentences together to avoid chopping speech into isolated words.
    endings=[m.end() for m in re.finditer(r'[.!?…]+["”’»)]*(?:\s+|$)|[。！？]+["”’»)]*|[;:](?:\s+|$)|\n+',text)]
    if not endings or endings[-1]!=len(text):endings.append(len(text))
    result=[];start=0;buffer=''
    for end in endings:
        sentence=text[start:end];start=end
        if buffer and len(buffer)+len(sentence)>limit:
            result.extend(split_text(buffer,limit));buffer=''
        buffer+=sentence
        if len(buffer)>=min(80,limit):
            result.extend(split_text(buffer,limit));buffer=''
    if buffer:result.extend(split_text(buffer,limit))
    return result


def speech_plan(document,limit=480,style='neutral',expressive=False,emphasis=False):
    if style not in STYLES:raise ValueError('Kiểu nhịp đọc không hợp lệ.')
    doc=deepcopy(document);sources=[c['text'] for c in doc['cues']] if doc['format']=='srt' else [doc['text']]
    units=[];plain=[];base=STYLES[style]['pause_ms']
    for cue_index,source in enumerate(sources):
        spans=marked_parts(source,emphasis);plain.append(''.join(text for text,_ in spans))
        source_start=len(units);pending=''
        for text,is_emphasis in spans:
            for piece in paced_pieces(text,limit,expressive):
                if not any(c.isalnum() for c in piece):
                    if len(units)>source_start:units[-1]['text']+=piece
                    else:pending+=piece
                    continue
                units.append({'text':pending+piece,'emphasis':is_emphasis});pending=''
        if pending and len(units)>source_start:units[-1]['text']+=pending
        if doc['format']=='srt':
            for unit in units[source_start:]:unit['cue']=cue_index
    if not units:raise ValueError('Nội dung không có lời đọc.')
    for index,unit in enumerate(units):
        piece=unit['text'];pause=base
        if expressive:
            ending=piece.rstrip().rstrip('"”’»)')
            if piece.endswith('\n') or '\n\n' in piece[-4:]:pause=base+140
            elif ending.endswith(('?','？')):pause=base+60
            elif ending.endswith(('!','！')):pause=base+30
            elif ending.endswith(('.', '。', '…')):pause=base+70
            elif ending.endswith((';',':')):pause=base+40
            else:pause=max(30,min(80,base//2))
        if unit['emphasis']:
            if index:units[index-1]['pause_ms']+=60
            pause+=70
        unit.update(pause_ms=pause,speed_scale=.94 if unit['emphasis'] else 1.0,gain_db=1.0 if unit['emphasis'] else 0.0)
    if doc['format']=='srt':
        for cue,text in zip(doc['cues'],plain):cue['text']=text
        doc['text']='\n'.join(plain)
    else:doc['text']=plain[0]
    units[-1]['pause_ms']=0
    return doc,units
