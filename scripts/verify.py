import subprocess
import sys

COMMANDS = (
    ("Django system check", ("src/manage.py", "check")),
    ("Ruff format check", ("-m", "ruff", "format", "--check", ".")),
    ("Ruff lint", ("-m", "ruff", "check", ".")),
    ("pytest", ("-m", "pytest")),
)


def main() -> int:
    """품질 검사를 순서대로 실행하고 첫 실패를 반환한다."""
    for label, arguments in COMMANDS:
        print(f"\n==> {label}", flush=True)
        result = subprocess.run((sys.executable, *arguments), check=False)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
