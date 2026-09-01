import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


def load_verify_module():
    spec = importlib.util.spec_from_file_location(
        "verify", ROOT / "scripts" / "verify.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_main_stops_and_returns_the_first_failure(monkeypatch) -> None:
    verify = load_verify_module()
    results = iter((0, 7, 0))
    executed_commands = []

    def fake_run(command, check):
        executed_commands.append((command, check))
        return SimpleNamespace(returncode=next(results))

    monkeypatch.setattr(verify.subprocess, "run", fake_run)

    assert verify.main() == 7
    assert executed_commands == [
        ((sys.executable, "src/manage.py", "check"), False),
        ((sys.executable, "-m", "ruff", "format", "--check", "."), False),
    ]
