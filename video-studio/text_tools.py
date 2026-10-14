"""Deterministic local editing helpers; no generative model or online service."""
import re


def edit_text(text, task='tidy'):
    lines = [re.sub(r'[ \t]+',' ', line).strip() for line in text.splitlines()]
    text = '\n'.join(line for line in lines if line)
    if not text:
        raise ValueError('Hãy nhập nội dung cần biên tập.')
    if task == 'tidy':
        return re.sub(r'\s+([,.!?;:])', r'\1', text)
    topic = text.splitlines()[0][:150]
    if task == 'titles':
        return '\n'.join([f'1. {topic}: những điều cần biết', f'2. Khám phá {topic}',
                          f'3. Bắt đầu với {topic} như thế nào?', f'4. Góc nhìn mới về {topic}',
                          f'5. {topic} trong 60 giây'])
    if task == 'outline':
        return ('KHUNG KỊCH BẢN 60 GIÂY\n\nChủ đề: ' + topic +
                '\n\n0–5 giây — Mở đầu\nNêu câu hỏi chính hoặc tình huống liên quan đến chủ đề.' +
                '\n\n5–20 giây — Bối cảnh\nGiới thiệu vấn đề và vì sao người xem nên quan tâm.' +
                '\n\n20–45 giây — Nội dung chính\nChia nội dung của bạn thành 2–3 ý, kèm ví dụ hoặc hình minh họa.' +
                '\n\n45–55 giây — Điểm cần nhớ\nNhắc lại thông điệp chính bằng một câu ngắn.' +
                '\n\n55–60 giây — Kết thúc\nĐặt câu hỏi hoặc lời mời hành động phù hợp.' +
                '\n\nNội dung nguồn:\n' + text)
    raise ValueError('Tác vụ biên tập không hợp lệ.')
