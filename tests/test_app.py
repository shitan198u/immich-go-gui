"""Entry-point tests for app.py."""

import app as app_module


def test_exception_hook_installed(monkeypatch):
    logged = []

    class FakeLogger:
        def critical(self, msg, exc_info=None):
            logged.append((msg, exc_info))

    monkeypatch.setattr(app_module.QTimer, "singleShot", lambda *_a, **_k: None)
    monkeypatch.setattr(app_module.sys, "excepthook", lambda *a, **k: None)
    app_module._install_exception_hook(FakeLogger())
    app_module.sys.excepthook(ValueError, ValueError("boom"), None)
    assert logged
    assert logged[0][0] == "Unhandled exception"


def test_run_self_test_success(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "default_config_dir", lambda: tmp_path)
    code = app_module.run_self_test()
    assert code == 0
    assert not (tmp_path / ".self-test-write").exists()


def test_run_self_test_failure(monkeypatch):
    def fake_build(*args, **kwargs):
        raise RuntimeError("simulated plan failure")

    monkeypatch.setattr(app_module, "build_plan_from_state", fake_build)
    code = app_module.run_self_test()
    assert code == 1
