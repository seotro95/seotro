"""Validate genre recommendations and controls against the public app contract."""
import json
import math

import pytest

from delivery import (DELIVERY_PROFILES, PROFILES, genre_recommendations, get_profile, profile_catalog,
                      segment_delivery, supported_nonverbal_cues, supported_preset_voices)


def test_previous_saved_profile_rates_remain_compatible():
    assert {name: PROFILES[name] for name in ('natural', 'story', 'news', 'calm', 'energetic')} == {
        'natural': (1, .22), 'story': (.94, .5), 'news': (1.04, .25),
        'calm': (.88, .65), 'energetic': (1.12, .16)}


def test_genre_catalog_is_serializable_and_recommends_actual_supported_voice_groups():
    catalog = json.loads(json.dumps(profile_catalog(), ensure_ascii=False))
    assert {'news', 'review', 'story', 'horror', 'fairytale', 'documentary', 'ad', 'calm'} <= {item['id'] for item in catalog}
    nano = {'Adam', 'Ái Hân', 'Mỹ Duyên', 'Đức Trí', 'Hữu Quân', 'Xuân Tiên',
            'Mai Anh', 'Trúc Ly', 'Anh Khôi', 'Minh Quân', 'Mạnh Dũng'}
    turbo = {'Adam bựa', 'Trúc Ly', 'Thiện Minh', 'Mai Anh', 'Hải Đăng', 'Thùy Dung',
             'Thiền Tâm Đức', 'Ngọc Huyền', 'Quang Sơn', 'Ngọc Trân', 'Minh Đức',
             'Phạm Tuyên', 'Thái Sơn', 'Xuân Vĩnh', 'Thanh Bình', 'Ngọc Linh',
             'Đoan Trang', 'Thục Đoan', 'Minh Triết', 'Mỹ Duyên', 'Quỳnh Anh',
             'Đức Trí', 'Kim Thanh', 'Adam', 'Quốc Tuấn'}
    for item in catalog:
        assert set(item['recommended_speakers']['vieneu_nano']) <= nano
        assert set(item['recommended_speakers']['vieneu']) <= turbo
        assert .85 <= item['speed'] <= 1.15 and 0 <= item['pause'] <= .7
        assert not any(key in item for key in ('style_prompt', 'pitch', 'instruct'))


def test_explicit_pause_zero_overrides_genre_and_emphasis_does_not_mutate_job():
    job = {'text': 'Đây là lời gốc?', 'delivery': 'story', 'speed': 1.1, 'paragraph_pause': 0}
    before = dict(job)
    controls = segment_delivery(job, emphasis=True)
    assert controls['tempo'] == pytest.approx(1.1*.94*.94)
    assert controls['gain'] == 1.12 and controls['pause'] == 0
    assert job == before
    assert segment_delivery({'delivery': 'story', 'paragraph_pause': None})['pause'] == .5


@pytest.mark.parametrize('speed', [0, -1, math.inf, math.nan])
def test_invalid_numeric_controls_cannot_reach_the_audio_engine(speed):
    with pytest.raises(ValueError, match='Tốc độ'):
        segment_delivery({'speed': speed})


def test_only_documented_model_nonverbal_tokens_are_advertised():
    assert supported_nonverbal_cues('vieneu_nano') == ['[cười]', '[thở dài]', '[hắng giọng]']
    assert supported_nonverbal_cues('vieneu') == supported_nonverbal_cues('vieneu_nano')
    assert supported_nonverbal_cues('system') == []
    assert supported_nonverbal_cues('qwen') == []
    assert get_profile(None) == DELIVERY_PROFILES['natural']
    with pytest.raises(ValueError, match='Phong cách'):
        get_profile('fake-sad-prompt')


def test_recommended_reference_styles_are_present_without_mutating_voice_metadata():
    presets = supported_preset_voices()
    assert len([voice for voice in presets if voice['engine'] == 'vieneu_nano']) == 11
    assert len([voice for voice in presets if voice['engine'] == 'vieneu']) == 25
    for genre in DELIVERY_PROFILES:
        for engine, speakers in genre_recommendations(genre).items():
            available = {voice['speaker'] for voice in presets if voice['engine'] == engine}
            assert set(speakers) <= available
    story = genre_recommendations('story', 'vieneu_nano')
    assert 'Anh Khôi' in story
    assert any(voice['speaker'] == 'Anh Khôi' and 'kể chuyện' in voice['description'] for voice in presets)
    assert genre_recommendations('news', 'qwen') == []
    presets[0]['name'] = 'changed by caller'
    assert supported_preset_voices()[0]['name'] == 'Adam'
