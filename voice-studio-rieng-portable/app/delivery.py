"""Genre pacing and real bundled-reference recommendations.

VieNeu 3.8.3 derives prosody from its selected preset/reference. Its ``style``
argument is ignored by both Nano and Turbo. These profiles therefore control
only speaking rate, pauses and explicit emphasis; they never inject a style
prompt, rewrite the script, add non-verbal sounds, or shift pitch.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from types import MappingProxyType


@dataclass(frozen=True)
class DeliveryProfile:
    label: str
    description: str
    speed: float
    pause: float
    emphasis_speed: float = .94
    emphasis_gain: float = 1.12
    nano_speakers: tuple[str, ...] = ('Minh Quân', 'Trúc Ly')
    turbo_speakers: tuple[str, ...] = ('Hải Đăng', 'Ngọc Huyền')


_STORY_NANO = ('Anh Khôi', 'Mỹ Duyên', 'Đức Trí')
_STORY_TURBO = ('Thiện Minh', 'Ngọc Linh', 'Thái Sơn', 'Quỳnh Anh')
_NEWS_NANO = ('Ái Hân', 'Mai Anh', 'Hữu Quân', 'Xuân Tiên')
_NEWS_TURBO = ('Mai Anh', 'Thùy Dung', 'Minh Đức', 'Minh Triết')

DELIVERY_PROFILES = MappingProxyType({
    'natural': DeliveryProfile('Tự nhiên', 'Giữ nhịp gốc của giọng đã chọn.', 1.0, .22),
    'news': DeliveryProfile('Tin tức', 'Nhịp rõ, gọn; gợi ý giọng có mẫu đọc tin tức.', 1.04, .25, .97, 1.08,
                            _NEWS_NANO, _NEWS_TURBO),
    'review': DeliveryProfile('Review', 'Nhịp trò chuyện, nghỉ vừa; nhấn các từ bạn đánh dấu.', 1.02, .28, .95, 1.10),
    'story': DeliveryProfile('Kể chuyện', 'Nhịp chậm vừa, nghỉ dài hơn; gợi ý giọng có mẫu kể chuyện.', .94, .5,
                             nano_speakers=_STORY_NANO, turbo_speakers=_STORY_TURBO),
    'horror': DeliveryProfile('Kinh dị · nhịp chậm', 'Đọc chậm, nghỉ dài; chọn mẫu giọng phù hợp để tạo sắc thái.', .90, .58,
                              .92, 1.10, _STORY_NANO, ('Thiện Minh', 'Thiền Tâm Đức', 'Thanh Bình')),
    'fairytale': DeliveryProfile('Cổ tích', 'Nhịp thong thả, tách ý rõ; gợi ý giọng có mẫu đọc truyện.', .93, .5,
                                 .93, 1.10, ('Mỹ Duyên', 'Đức Trí', 'Anh Khôi'),
                                 ('Ngọc Linh', 'Quỳnh Anh', 'Mỹ Duyên', 'Kim Thanh')),
    'documentary': DeliveryProfile('Thuyết minh', 'Nhịp đều, chậm vừa, nghỉ giữa các ý.', .96, .4,
                                   .96, 1.08, _NEWS_NANO, ('Minh Đức', 'Mai Anh', 'Thùy Dung')),
    'ad': DeliveryProfile('Quảng cáo', 'Nhịp nhanh vừa, nghỉ ngắn; nhấn các từ bạn đánh dấu.', 1.08, .18,
                          .95, 1.12, ('Trúc Ly', 'Minh Quân'), ('Trúc Ly', 'Hải Đăng')),
    'calm': DeliveryProfile('Chậm rãi', 'Nhịp chậm, khoảng nghỉ dài; giữ cao độ của giọng.', .88, .65,
                            .96, 1.08, _STORY_NANO, ('Thiền Tâm Đức', 'Ngọc Huyền', 'Thục Đoan')),
    # Retain existing saved jobs and their exact basic speed/pause settings.
    'energetic': DeliveryProfile('Sôi nổi', 'Nhịp nhanh, khoảng nghỉ ngắn.', 1.12, .16),
})

# Compatibility for narration/worker imports and previously saved jobs.
PROFILES = {name: (profile.speed, profile.pause) for name, profile in DELIVERY_PROFILES.items()}

# Exact preset names/descriptions from VieNeu 3.8.3's bundled
# assets/voices_v3_nano.json and assets/voices_v3_turbo.json. These references,
# rather than the deprecated style= argument, condition native voice prosody.
_PRESETS = {
    'vieneu_nano': (
        ('Adam', 'male', 'Nam · Nam · Giọng đọc tự nhiên'),
        ('Ái Hân', 'female', 'Nữ · Nam · Phong cách tin tức'),
        ('Mỹ Duyên', 'female', 'Nữ · Bắc · Phong cách đọc truyện'),
        ('Đức Trí', 'male', 'Nam · Bắc · Phong cách đọc truyện'),
        ('Hữu Quân', 'male', 'Nam · Bắc · Phong cách tin tức'),
        ('Xuân Tiên', 'female', 'Nữ · Bắc · Phong cách tin tức'),
        ('Mai Anh', 'female', 'Nữ · Bắc · Phong cách tin tức'),
        ('Trúc Ly', 'female', 'Nữ · Bắc · Phong cách tự nhiên'),
        ('Anh Khôi', 'male', 'Nam · Bắc · Phong cách kể chuyện'),
        ('Minh Quân', 'male', 'Nam · Bắc · Phong cách tự nhiên'),
        ('Mạnh Dũng', 'male', 'Nam · Bắc · Phong cách tự nhiên'),
    ),
    'vieneu': (
        ('Adam bựa', 'male', 'Nam · Bắc · Phong cách tự nhiên'),
        ('Trúc Ly', 'female', 'Nữ · Bắc · Phong cách tự nhiên'),
        ('Thiện Minh', 'male', 'Nam · Bắc · Phong cách kể chuyện'),
        ('Mai Anh', 'female', 'Nữ · Bắc · Phong cách tin tức'),
        ('Hải Đăng', 'male', 'Nam · Bắc · Phong cách tự nhiên'),
        ('Thùy Dung', 'female', 'Nữ · Nam · Phong cách tin tức'),
        ('Thiền Tâm Đức', 'male', 'Nam · Bắc · Phong cách kể chuyện'),
        ('Ngọc Huyền', 'female', 'Nữ · Bắc · Giọng đọc tự nhiên'),
        ('Quang Sơn', 'male', 'Nam · Trung · Phong cách tự nhiên'),
        ('Ngọc Trân', 'female', 'Nữ · Trung · Phong cách tự nhiên'),
        ('Minh Đức', 'male', 'Nam · Bắc · Phong cách tin tức'),
        ('Phạm Tuyên', 'male', 'Nam · Bắc · Phong cách tự nhiên'),
        ('Thái Sơn', 'male', 'Nam · Nam · Phong cách kể chuyện'),
        ('Xuân Vĩnh', 'male', 'Nam · Bắc · Phong cách tự nhiên'),
        ('Thanh Bình', 'male', 'Nam · Bắc · Phong cách kể chuyện'),
        ('Ngọc Linh', 'female', 'Nữ · Bắc · Phong cách kể chuyện'),
        ('Đoan Trang', 'female', 'Nữ · Bắc · Phong cách tự nhiên'),
        ('Thục Đoan', 'female', 'Nữ · Nam · Phong cách kể chuyện'),
        ('Minh Triết', 'male', 'Nam · Nam · Phong cách tin tức'),
        ('Mỹ Duyên', 'female', 'Nữ · Nam · Phong cách đọc truyện'),
        ('Quỳnh Anh', 'female', 'Nữ · Bắc · Phong cách đọc truyện'),
        ('Đức Trí', 'male', 'Nam · Nam · Phong cách đọc truyện'),
        ('Kim Thanh', 'female', 'Nữ · Nam · Phong cách đọc truyện'),
        ('Adam', 'male', 'Nam · Nam · Giọng đọc tự nhiên'),
        ('Quốc Tuấn', 'male', 'Nam · Bắc · Phong cách tự nhiên'),
    ),
}


def get_profile(name='natural'):
    try:
        return DELIVERY_PROFILES[name or 'natural']
    except KeyError:
        raise ValueError('Phong cách đọc không hợp lệ. Hãy chọn lại phong cách có sẵn.') from None


def supported_preset_voices():
    """Fresh metadata records for the shipped Vietnamese preset references."""
    return [{'engine': engine, 'speaker': speaker, 'name': speaker,
             'gender': gender, 'description': description, 'languages': ['vi']}
            for engine, entries in _PRESETS.items()
            for speaker, gender, description in entries]


def genre_recommendations(name='natural', engine=None):
    """Return names, not new style prompts; never modify an existing voice choice."""
    profile = get_profile(name)
    names = {'vieneu_nano': list(profile.nano_speakers), 'vieneu': list(profile.turbo_speakers)}
    return names if engine is None else names.get(engine, [])


def profile_catalog():
    """JSON-safe UI metadata. Recommendations never replace a user's voice."""
    return [
        {'id': name, 'label': profile.label, 'description': profile.description,
         'speed': profile.speed, 'pause': profile.pause,
         'emphasis_speed': profile.emphasis_speed, 'emphasis_gain': profile.emphasis_gain,
         'recommended_speakers': genre_recommendations(name)}
        for name, profile in DELIVERY_PROFILES.items()
    ]


def segment_delivery(job, emphasis=False):
    """Resolve numeric controls; the caller still enforces original SRT bounds.

    ``paragraph_pause=None`` follows the genre. An explicit zero remains zero.
    Only an explicitly emphasized segment gets emphasis gain or extra slowing.
    """
    profile = get_profile(job.get('delivery', 'natural'))
    speed = float(job.get('speed', 1))
    pause = job.get('paragraph_pause')
    pause = profile.pause if pause is None else float(pause)
    if not math.isfinite(speed) or speed <= 0:
        raise ValueError('Tốc độ đọc phải là số dương hữu hạn.')
    if not math.isfinite(pause) or not 0 <= pause <= 10:
        raise ValueError('Khoảng nghỉ phải từ 0 đến 10 giây.')
    return {'tempo': speed*profile.speed*(profile.emphasis_speed if emphasis else 1),
            'gain': profile.emphasis_gain if emphasis else 1.0, 'pause': pause}


def supported_nonverbal_cues(engine):
    """Only documented, trained tokens; no automatic insertion into a script."""
    if engine in {'vieneu', 'vieneu_nano'}:
        return ['[cười]', '[thở dài]', '[hắng giọng]']
    return []
