import pytest

from orqlet.domain.findings import Verdict, combine, is_success

pytestmark = pytest.mark.unit


def test_only_pass_is_success() -> None:
    assert is_success(Verdict.PASS)
    assert not is_success(Verdict.FAIL)
    assert not is_success(Verdict.NOT_RUN)


def test_fail_beats_not_run_which_beats_pass() -> None:
    assert combine([Verdict.PASS, Verdict.NOT_RUN, Verdict.FAIL]) is Verdict.FAIL
    assert combine([Verdict.PASS, Verdict.NOT_RUN]) is Verdict.NOT_RUN
    assert combine([Verdict.PASS, Verdict.PASS]) is Verdict.PASS


def test_no_evidence_is_never_success() -> None:
    assert combine([]) is Verdict.NOT_RUN
