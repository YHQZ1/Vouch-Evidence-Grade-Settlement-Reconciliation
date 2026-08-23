from __future__ import annotations

from pathlib import Path

from synthetic_data.cli import main


def test_cli_generate_verify_and_frozen_check(tmp_path: Path, capsys) -> None:
    assert (
        main(["generate", "--dataset", "held-out", "--data-root", str(tmp_path)]) == 0
    )
    verify_args = [
        "verify",
        "--dataset",
        "held-out",
        "--data-root",
        str(tmp_path),
    ]
    assert main(verify_args) == 0
    assert main(["verify", "--all", "--data-root", str(tmp_path)]) == 1
    assert main(["check-frozen", "--data-root", str(tmp_path)]) == 1
    assert "error:" in capsys.readouterr().err


def test_cli_returns_nonzero_for_missing_dataset(tmp_path: Path) -> None:
    verify_args = [
        "verify",
        "--dataset",
        "development",
        "--data-root",
        str(tmp_path),
    ]
    assert main(verify_args) == 1
