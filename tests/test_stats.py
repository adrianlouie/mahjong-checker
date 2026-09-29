import pytest

from stats import run


def test_run_reports_consistent_results():
    result = run(trials=500, seed=1)
    assert result["trials"] == 500
    assert 0 <= result["wins"] < 5              # winning hands are extremely rare
    assert sum(result["distribution"].values()) == pytest.approx(1)


def test_run_is_repeatable_with_a_seed():
    assert run(200, seed=3) == run(200, seed=3)
