"""Contract suites must not trigger real inference when models are installed locally."""
import pytest


@pytest.fixture(autouse=True)
def isolate_optional_local_model(request, monkeypatch):
    if request.node.path.name not in {'test_app.py', 'test_clones.py', 'test_voice_jobs.py', 'test_local_cloning_api.py'}:
        return
    import app
    # The remote/missing-engine contract tests select their own backend. Tests
    # for a ready local backend override this explicitly; real inference has a
    # separate functional smoke check using the supplied references.
    monkeypatch.setattr(app.cosy_engine, 'availability', lambda: {
        'ready': False, 'model_ready': False, 'dependencies': False,
        'missing_dependencies': [], 'ffmpeg': True, 'styles': list(app.cosy_engine.STYLES),
        'reason': 'Chưa bật mô hình Hmong trong kiểm thử hợp đồng.'})
