"""Entry-point tests for app.py."""

from dataclasses import replace
from types import SimpleNamespace

import app as app_module
import core.flag_registry as flag_registry_module


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


def test_run_self_test_prints_ok_on_success(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(app_module, "default_config_dir", lambda: tmp_path)
    code = app_module.run_self_test()
    captured = capsys.readouterr()
    assert code == 0
    assert "self-test: ok" in captured.out


def test_run_self_test_empty_registry_fails(monkeypatch, capsys):
    empty_registry = replace(flag_registry_module.REGISTRY, tabs={})
    monkeypatch.setattr(flag_registry_module, "REGISTRY", empty_registry)
    code = app_module.run_self_test()
    captured = capsys.readouterr()
    assert code == 1
    assert "self-test: flag registry empty" in captured.err


def test_run_self_test_plan_with_errors_fails(monkeypatch, capsys):
    fake_plan = SimpleNamespace(errors=["binary path is required"])
    monkeypatch.setattr(
        app_module, "build_plan_from_state", lambda **kwargs: fake_plan
    )
    code = app_module.run_self_test()
    captured = capsys.readouterr()
    assert code == 1
    assert "self-test: plan errors:" in captured.err
    assert "binary path is required" in captured.err


def test_run_self_test_config_dir_write_failure(tmp_path, monkeypatch, capsys):
    """default_config_dir pointing at an unwritable location should be caught."""
    blocked_file = tmp_path / "blocked"
    blocked_file.write_text("not a directory", encoding="utf-8")
    monkeypatch.setattr(
        app_module, "default_config_dir", lambda: blocked_file / "config"
    )
    code = app_module.run_self_test()
    captured = capsys.readouterr()
    assert code == 1
    assert "self-test failed:" in captured.err


def test_run_self_test_creates_and_cleans_up_config_dir(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "nested" / "config"
    monkeypatch.setattr(app_module, "default_config_dir", lambda: cfg_dir)
    code = app_module.run_self_test()
    assert code == 0
    assert cfg_dir.is_dir()
    assert not (cfg_dir / ".self-test-write").exists()
