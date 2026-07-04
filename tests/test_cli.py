from typer.testing import CliRunner

from ecl_trainer.cli import app


def test_cli_help_lists_expected_commands():
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "verify-log" in result.output
    assert "hf-card-export" in result.output
    assert "supply-chain-evidence" in result.output
    assert "lifecycle" in result.output
    assert "mlops-pack" in result.output
