"""The shipped defaults must be the newly supplied recordings, not the old pair."""
import hashlib
import wave

from hmong_assets import ROOT, reference, references, source


def test_new_sources_replace_both_old_defaults():
    expected = {
        'female': ('hmong nữ 2(1).MP3', '874f510e723f48fcd093d55a5ba4613fc80107a863261658ec9d3961ef493d84'),
        'male': ('hmong nam 2.MP3', 'bc9104c2ebe00471abc46283c52627b2cadc615d96f15f1dc9d576b1316d78c8'),
    }
    old = {'29285370b91db8465222b2056b204110c6dded1a60c9004c7fb8747fe4978c9c',
           '2c3467e7b5f0e49a3277397c00762810f657fd1bbd36f738a7e17d0f067f6222',
           '24a2d3e0ae3aab305b47bdc8e13c3d8b64381ab3aa019ec1da5ebecef4e27c15'}
    user_words = {
        'male': 'hais tias tus neeng uas nyob rau ntawm yug ib sab no nws xav dag tsis rau yug',
        'female': 'nyob zoo os yawb txiv , kuv nim qhov los xwb, ntseem tsis ntaub muaj dab tsis li os',
    }
    for gender, (filename, checksum) in expected.items():
        item = references()[gender]
        original = source('hmong-' + gender)
        assert item['user_filename'] == filename
        assert hashlib.sha256(original.read_bytes()).hexdigest() == checksum
        assert item['sha256'] == checksum and checksum not in old
        assert item['reference_text_verified'] is True
        assert item['reference_text_source'] == 'user_provided_for_selected_excerpt'
        assert item['reference']['text'] == user_words[gender]


def test_both_references_use_the_final_short_recordings():
    entries = references()
    assert 4.69 < entries['female']['duration'] < 4.72
    for gender, expected_seconds in [('female', 4.7), ('male', 4.7)]:
        path, words = reference('hmong-' + gender)
        assert words and path == ROOT / entries[gender]['reference_file']
        with wave.open(str(path)) as audio:
            assert (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) == (1, 2, 24000)
            assert abs(audio.getnframes() / 24000 - expected_seconds) < .001
            samples = audio.readframes(audio.getnframes())
            assert any(samples)
