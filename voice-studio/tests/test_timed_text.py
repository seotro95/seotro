from narration import spoken_text, plan_segments


def test_clock_labels_removed_but_spoken_numbers_preserved():
    text='1\n00:00:01,500 --> 00:00:04,000\nGiá 200.000 đồng, 5 phút và 12:30 là giờ hẹn.\n\n[01:30] Xin chào.\n02:40.500 Lời tiếp.\n(03:50) Cảm ơn.'
    assert spoken_text(text).strip()=='Giá 200.000 đồng, 5 phút và 12:30 là giờ hẹn.\n\nXin chào.\nLời tiếp.\nCảm ơn.'
    parts=plan_segments({'text':text,'input_format':'txt'})
    assert not any('-->' in s.text or '[01:30]' in s.text for s in parts)
    assert '200.000' in ' '.join(s.text for s in parts)


def test_opt_out_and_srt_timing_preserved():
    assert plan_segments({'text':'01:30 Xin chào.','skip_timestamps':False})[0].text=='01:30 Xin chào.'
    parts=plan_segments({'text':'1\n00:00:01,500 --> 00:00:04,000\nXin chào.','input_format':'srt'})
    assert len(parts)==1 and parts[0].cue==0 and parts[0].text=='Xin chào.'


def test_packed_timed_text_avoids_short_inferences():
    text='\n'.join(f'00:{n:02d} Câu số {n}.' for n in range(10))
    classic=plan_segments({'text':text})
    packed=plan_segments({'text':text,'segment_plan':'nano-packed-v1'})
    assert len(packed)<len(classic)
    assert ' '.join(s.text for s in packed)==' '.join(s.text for s in classic)
