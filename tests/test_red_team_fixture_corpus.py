from pathlib import Path

from ecl_trainer.core.policy import NoPayloadValidator
from ecl_trainer.red_team import BUILTIN_FIXTURES, iter_fixture_paths, load_fixture, run_corpus, run_fixture

FIXTURE_ROOT = Path(__file__).parent / "red_team_fixtures"


def test_red_team_fixture_corpus_executes_expected_outcomes():
    paths = iter_fixture_paths(FIXTURE_ROOT)
    assert len(paths) >= 8
    for path in paths:
        result = run_fixture(load_fixture(path))
        assert result["passed"], result
        NoPayloadValidator().validate(result)


def test_red_team_corpus_report_is_metadata_only():
    report = run_corpus(FIXTURE_ROOT)
    assert report["corpus_source"] == "fixture_directory"
    assert report["failed_count"] == 0
    assert report["passed_count"] == report["fixture_count"]
    NoPayloadValidator().validate(report)


def test_builtin_red_team_corpus_is_full_and_self_consistent(tmp_path):
    report = run_corpus(tmp_path / "missing-fixtures")
    assert report["corpus_source"] == "packaged_fixture_directory"
    assert report["fixture_count"] == len(BUILTIN_FIXTURES) == 9
    assert report["failed_count"] == 0
    assert report["passed_count"] == report["fixture_count"]
    NoPayloadValidator().validate(report)
