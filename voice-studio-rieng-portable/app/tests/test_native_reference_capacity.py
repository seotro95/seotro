"""Full reference audio must fit VoxCPM2 without reloading its verified model."""
import ctypes as C

import pytest

import native_synthesis as native


@pytest.mark.parametrize(('frames', 'rate', 'capacity'), [
    (238080, 16000, 240000), (238081, 16000, 240640),
    (240000, 16000, 240640), (360000, 24000, 240640),
    (1323000, 44100, 481280), (1440000, 48000, 481280),
    (240000, 8000, 481280), (5760000, 192000, 481280),
    (72000, 24000, 240000), (714241, 48000, 240640),
])
def test_reference_capacity_uses_native_resampling_and_whole_patch_padding(frames, rate, capacity):
    assert native._voxcpm_reference_capacity(frames, rate) == capacity


@pytest.mark.parametrize(('frames', 'rate'), [(0, 16000), (480001, 16000),
                                             (True, 16000), (300, 300), (480000, 16000.0)])
def test_invalid_or_overlong_reference_is_rejected_without_truncation(frames, rate):
    with pytest.raises(ValueError):
        native._voxcpm_reference_capacity(frames, rate)


class SessionLibrary:
    def __init__(self):
        self.freed, self.created, self.options_freed = [], [], 0
        self.fail = False
        self.next_handle = 10
    def audiocpp_options_create(self):
        self.options = {}
        return C.c_void_p(3)
    def audiocpp_options_set(self, options, name, value):
        self.options[name.decode()] = value.decode()
        return 0
    def audiocpp_options_free(self, options):
        self.options_freed += 1
    def audiocpp_session_create(self, model, task, mode, backend, options, result):
        self.next_handle += 1
        result._obj.value = self.next_handle
        self.created.append({'model': model.value, 'device': backend._obj.backend.decode(),
                             'threads': backend._obj.threads, 'options': dict(self.options)})
        return 1 if self.fail else 0
    def audiocpp_session_free(self, handle):
        self.freed.append(handle.value)
    def audiocpp_last_error(self):
        return b'encoder allocation failed'


def session_fixture(device='cuda', performance='cuda_perf'):
    session = native.NativeSession.__new__(native.NativeSession)
    session.family, session.device, session.threads = 'voxcpm2', device, 4
    session.native_performance = performance
    session.model, session.registry, session.session = C.c_void_p(2), C.c_void_p(1), C.c_void_p(4)
    session.lib = SessionLibrary()
    session._encoder_sample_capacity = 240000
    session.info = {'voxcpm_reference_encoder_capacity': 240000}
    return session


def test_short_references_keep_the_original_session_and_its_capacity():
    session = session_fixture()
    session._ensure_reference_capacity(238080, 16000)
    assert session.session.value == 4
    assert not session.lib.freed and not session.lib.created
    assert session.info['voxcpm_reference_encoder_capacity'] == 240000


@pytest.mark.parametrize(('device', 'performance'), [('cpu', 'off'), ('cuda', 'off'), ('cuda', 'cuda_perf')])
def test_long_reference_grows_once_retaining_model_registry_and_all_device_options(device, performance):
    session = session_fixture(device, performance)
    model, registry = session.model, session.registry
    session._ensure_reference_capacity(720000, 24000)
    assert session.lib.freed == [4]
    assert session.model is model and session.registry is registry
    assert session.lib.created == [{'model': 2, 'device': device, 'threads': 4, 'options': {
        'voxcpm2.mem_saver': 'false', 'voxcpm2.prompt_cache_slots': '4',
        'voxcpm2.perf_mode': performance, 'voxcpm2.audiovae_encoder_sample_capacity': '481280'}}]
    assert session.info['voxcpm_reference_encoder_capacity'] == 481280
    current = session.session
    session._ensure_reference_capacity(720000, 24000)
    session._ensure_reference_capacity(72000, 24000)
    assert session.session is current and len(session.lib.created) == 1
    assert session.lib.options_freed == 1


def test_failed_growth_does_not_double_free_or_report_uncreated_capacity_and_can_retry():
    session = session_fixture()
    session.lib.fail = True
    with pytest.raises(RuntimeError, match='encoder allocation failed'):
        session._ensure_reference_capacity(720000, 24000)
    assert session.lib.freed == [4, 11]
    assert not session.session and session._encoder_sample_capacity == 240000
    assert session.info['voxcpm_reference_encoder_capacity'] == 240000
    assert session.model.value == 2 and session.registry.value == 1
    session.lib.fail = False
    session._ensure_reference_capacity(72000, 24000)
    assert session.session.value == 12 and session._encoder_sample_capacity == 240000
    assert 'voxcpm2.audiovae_encoder_sample_capacity' not in session.lib.created[-1]['options']
    assert session.lib.freed == [4, 11]


def test_overlong_reference_does_not_destroy_the_working_session():
    session = session_fixture()
    with pytest.raises(ValueError):
        session._ensure_reference_capacity(720001, 24000)
    assert session.session.value == 4 and not session.lib.freed


def test_omnivoice_session_is_not_changed_by_voxcpm_capacity_handling():
    session = session_fixture()
    session.family = 'omnivoice'
    session._ensure_reference_capacity(720000, 24000)
    assert session.session.value == 4 and not session.lib.freed
