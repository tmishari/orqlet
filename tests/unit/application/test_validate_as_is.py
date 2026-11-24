"""`validate as-is`: facts only, evidence that resolves, uncertainty kept (proposal 17.3)."""

from __future__ import annotations

from typing import Any

import pytest

from orqlet.application.usecases.validate_as_is import AsIsOptions, validate_as_is
from orqlet.application.usecases.validation import ValidationResult
from orqlet.domain.findings import Verdict
from orqlet.domain.resources import credential_problems, hidden_text_problems
from tests.support.artifacts import (
    AS_IS,
    BASE,
    LATER,
    LEDGER,
    REPO_FILES,
    SOURCE,
    World,
    as_is,
    evidence,
    fact,
    happy_task,
    ledger,
    make_world,
    question,
    with_front_matter,
)

pytestmark = pytest.mark.unit


def run(
    world: World, document: dict[str, Any], *, body: str = "", options: AsIsOptions | None = None
) -> ValidationResult:
    world.put(AS_IS, with_front_matter(document, body))
    return validate_as_is(world.services(), AS_IS, options)


def codes(result: ValidationResult) -> list[str]:
    return [finding.code for finding in result.findings]


def test_a_sound_file_passes_and_its_summary_leads_with_the_uncertainty() -> None:
    result = run(make_world(), as_is())

    assert result.verdict is Verdict.PASS
    assert codes(result) == []
    assert result.data["facts"] == 2
    assert (result.data["unknowns"], result.data["material_unknowns"]) == (1, 1)
    assert result.data["contradictions"] == 0


def test_validation_never_writes() -> None:
    world = make_world()
    world.put(AS_IS, with_front_matter(as_is()))
    before = world.project.snapshot()

    validate_as_is(world.services(), AS_IS)

    assert world.project.snapshot() == before


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda d: d["facts"][0]["evidence"][0].update(sha256="0" * 64), "ORQ-E335"),
        (lambda d: d["facts"][0]["evidence"][0].update(lines="40-45"), "ORQ-E334"),
        (lambda d: d["facts"][0]["evidence"][0].update(path="src/pkg/gone.py"), "ORQ-E333"),
        (lambda d: d["facts"][0]["evidence"][0].update(revision=LATER), "ORQ-E332"),
    ],
)
def test_evidence_that_does_not_resolve_at_the_bound_revision_fails(mutate: Any, code: str) -> None:
    document = as_is()
    mutate(document)

    result = run(make_world(), document)

    assert result.verdict is Verdict.FAIL
    assert code in codes(result)


def test_an_unknown_revision_is_not_run_and_never_a_pass() -> None:
    result = run(make_world(commits=False), as_is())

    assert result.verdict is Verdict.NOT_RUN
    assert codes(result) == []
    assert "not in this repository" in result.not_run[0]


def test_a_file_without_facts_proves_nothing() -> None:
    result = run(make_world(), as_is(facts=[]))

    assert result.verdict is Verdict.NOT_RUN
    assert "no facts" in result.not_run[0]


def test_the_size_budget_counts_facts_and_never_unknowns_or_contradictions() -> None:
    long_unknown = {"id": "U-2", "what": "word " * 300, "material": False}
    ok = run(make_world(), as_is(unknowns=[long_unknown]))
    over = run(make_world(), as_is(size_budget={"max_words": 3}))

    assert ok.verdict is Verdict.PASS
    assert "ORQ-E337" in codes(over)


def test_advice_in_a_fact_or_in_the_text_is_flagged_but_does_not_fail_the_file() -> None:
    document = as_is(facts=[fact(1, "The module should be split into two.")])

    result = run(make_world(), document, body="We recommend a rewrite.")

    assert result.verdict is Verdict.PASS
    assert codes(result) == ["ORQ-W338", "ORQ-W338"]


def test_ids_are_unique_within_their_kind() -> None:
    document = as_is(facts=[fact(1), fact(1, "Another fact.", start=5, end=6)])

    assert "ORQ-E336" in codes(run(make_world(), document))


def test_the_header_and_the_body_agree_on_the_base_revision_and_the_task() -> None:
    document = as_is()
    document["header"]["bound"]["base_revision"] = LATER
    assert "ORQ-E330" in codes(run(make_world(), document))

    other_task = as_is(task="other")
    assert codes(run(make_world(), other_task)).count("ORQ-E331") == 2


@pytest.mark.parametrize(
    ("data", "code"),
    [
        (b"no front matter at all\n", "ORQ-E324"),
        (b"---\nschema: orqlet.as-is/v1\n---\n", "ORQ-E325"),
        (b"---\nanchor: &a 1\nschema: orqlet.as-is/v1\n---\n", "ORQ-E325"),
        (b"x" * (512 * 1024 + 1), "ORQ-E323"),
    ],
)
def test_a_file_that_cannot_be_trusted_is_reported_not_crashed_on(data: bytes, code: str) -> None:
    world = make_world()
    world.put(AS_IS, data)

    result = validate_as_is(world.services(), AS_IS)

    assert result.verdict is Verdict.FAIL
    assert codes(result) == [code]


def test_a_missing_file_and_an_unsafe_path_are_findings() -> None:
    world = make_world()

    assert [
        f.code for f in validate_as_is(world.services(), "docs/design/demo/as-is.md").findings
    ] == ["ORQ-E321"]
    assert [f.code for f in validate_as_is(world.services(), "../outside.md").findings] == [
        "ORQ-E320"
    ]


def test_a_validation_error_names_the_field_and_not_the_value() -> None:
    document = as_is()
    document["facts"][0]["statement"] = ""

    result = run(make_world(), document)

    message = result.findings[0].message
    assert "facts.0.statement" in message


def test_an_unknown_cites_a_question_that_must_exist_in_the_ledger() -> None:
    world = make_world()
    world.put_yaml(LEDGER, ledger())
    document = as_is(unknowns=[{"id": "U-1", "what": "x", "material": True, "question_ref": "Q-9"}])

    assert "ORQ-E339" in codes(run(world, document))


def test_without_a_ledger_a_question_reference_is_only_a_warning() -> None:
    document = as_is(unknowns=[{"id": "U-1", "what": "x", "material": True, "question_ref": "Q-1"}])

    result = run(make_world(), document)

    assert (result.verdict, codes(result)) == (Verdict.PASS, ["ORQ-W339"])


def test_an_open_question_that_blocks_research_fails_the_file() -> None:
    world = make_world()
    world.put_yaml(LEDGER, ledger(questions=[question(1, blocks=["research"])]))

    result = run(world, as_is())

    assert result.verdict is Verdict.FAIL
    assert "ORQ-E345" in codes(result)


def test_an_answered_question_blocks_nothing() -> None:
    world = make_world()
    happy_task(world)

    assert validate_as_is(world.services(), AS_IS).verdict is Verdict.PASS


FRAGMENT = {
    "schema": "orqlet.as-is-fragment/v1",
    "fragment_id": "cli-area",
    "base_revision": BASE,
    "scope": {"paths": ["src/**"], "request_ref": "demo"},
    "facts": [],
    "unknowns": [{"id": "U-1", "what": "Whether exit codes are stable", "material": False}],
    "contradictions": [{"id": "C-1", "sources": ["a.md", "b.md"], "note": "Two defaults"}],
}


def fragments_world() -> World:
    world = make_world()
    world.put_yaml("scratch/fragments/cli-area.yaml", FRAGMENT)
    return world


def test_an_unknown_or_contradiction_of_a_fragment_cannot_be_dropped() -> None:
    options = AsIsOptions(fragments_dir="scratch/fragments")

    result = run(fragments_world(), as_is(), options=options)

    assert [f.code for f in result.findings] == ["ORQ-E340", "ORQ-E340"]
    assert "cli-area/U-1" in result.findings[0].message


def test_a_fragment_entry_is_kept_when_it_is_named_in_merged_from_or_repeated_verbatim() -> None:
    document = as_is(
        unknowns=[
            {
                "id": "U-1",
                "what": "Merged entry",
                "material": False,
                "merged_from": ["cli-area/U-1"],
            }
        ],
        contradictions=[
            {"id": "C-1", "sources": ["a.md", "b.md"], "note": "Two defaults"}  # verbatim
        ],
    )

    result = run(
        fragments_world(), document, options=AsIsOptions(fragments_dir="scratch/fragments")
    )

    assert result.verdict is Verdict.PASS


def test_a_fragments_folder_that_is_not_there_or_is_empty_is_reported() -> None:
    missing = run(make_world(), as_is(), options=AsIsOptions(fragments_dir="scratch/none"))
    assert "ORQ-E321" in codes(missing)

    world = make_world()
    world.project.add_dir("scratch/empty")
    empty = run(world, as_is(), options=AsIsOptions(fragments_dir="scratch/empty"))
    assert empty.verdict is Verdict.NOT_RUN


def test_the_scope_is_stale_when_a_file_in_it_changed_since_the_base_revision() -> None:
    changed = dict(make_world().vcs._revisions[BASE])
    changed["src/pkg/mod.py"] = SOURCE + b"# edited\n"
    world = make_world(other_revisions={LATER: changed})

    result = run(world, as_is(), options=AsIsOptions(against=LATER))

    assert result.verdict is Verdict.NOT_RUN
    assert codes(result) == ["ORQ-W341"]
    assert "src/pkg/mod.py" in result.findings[0].message


def test_a_moved_head_that_leaves_the_scope_alone_is_fine() -> None:
    changed = dict(make_world().vcs._revisions[BASE])
    changed["docs/guide.md"] = b"# Guide, edited\n"
    world = make_world(other_revisions={LATER: changed})

    result = run(world, as_is(), options=AsIsOptions(against=LATER))

    assert result.verdict is Verdict.PASS


def test_comparing_with_a_revision_that_does_not_exist_is_not_run() -> None:
    result = run(make_world(), as_is(), options=AsIsOptions(against="f" * 40))

    assert result.verdict is Verdict.NOT_RUN


def test_evidence_helper_agrees_with_the_domain_hash() -> None:
    assert evidence()["lines"] == "1-2"


# --- task-owned evidence at another revision (task workflow-efficiency, P-3) ---------------------
OWNED = "docs/design/demo/evidence/web/page.md"
CLEAN_OWNED = "docs/design/demo/evidence/web/clean.md"
LIMIT = 256 * 1024
MARKER = "UNIQUE-MARKER-OF-THE-PAGE"  # clean text that no message may repeat
PAGE = f"# Page\nFirst line of text. {MARKER}\nSecond line of text.\n".encode()
EDITED_PAGE = b"# Page\nFirst line, edited.\nSecond line of text.\n"

# Credential-shaped values, assembled at run time (ORQLET-SEC-003).
TOKEN = "".join(("gh", "p_", "Zq7Xv3Lm9Tk2", "Rb8Wc4Yd6Hn1", "Pf5Gs0Jx"))
ACCESS_KEY = "".join(("AK", "IA", "QZ7XV3LM", "9TK2RB8W"))


def page_with(third_line: str) -> bytes:
    """A page of four lines whose line 3 is the given text."""
    return f"# A page\nA clean line. {MARKER}\n{third_line}\nA last clean line.\n".encode()


def page_of(size: int) -> bytes:
    """Clean text of exactly `size` bytes, in lines of 63 characters (no line is long)."""
    line = (b"Plain page text. " * 4)[:63] + b"\n"
    whole, rest = divmod(size, len(line))
    return line * whole + b"x" * rest


def shows_part_of(text: str, secret: str, width: int = 8) -> bool:
    """True when `width` consecutive characters of `secret` are in `text`."""
    return any(secret[i : i + width] in text for i in range(len(secret) - width + 1))


def owned_world(files: dict[str, bytes]) -> World:
    """The usual repository plus these files, committed (so read at HEAD) and in the work tree."""
    return make_world({**REPO_FILES, **files})


def owned_fact(
    number: int,
    path: str,
    content: bytes,
    *,
    revision: str = LATER,
    start: int = 1,
    end: int = 2,
) -> dict[str, Any]:
    return fact(
        number,
        "The page records a line.",
        path=path,
        start=start,
        end=end,
        content=content,
        revision=revision,
    )


def owned_document(*owned: dict[str, Any]) -> dict[str, Any]:
    """The usual AS-IS file (A-1 cites the base revision) plus the given facts."""
    return as_is(facts=[fact(1), *owned])


def validate_at(world: World, path: str, document: dict[str, Any]) -> ValidationResult:
    world.put(path, with_front_matter(document))
    return validate_as_is(world.services(), path)


def message_of(result: ValidationResult, code: str) -> str:
    return " ".join(f.message for f in result.findings if f.code == code)


def test_a_task_owned_entry_at_another_revision_is_read_at_head_and_passes() -> None:
    """AC-2. expected_behavior_source: BC-22; ADR-003 decision 2 (a task-owned entry may cite
    another revision, is read at HEAD and its lines are checked against its sha256); EC-5. The
    cited revision is not a revision of the repository."""
    world = owned_world({OWNED: PAGE})

    result = run(world, owned_document(owned_fact(2, OWNED, PAGE)))

    assert result.verdict is Verdict.PASS
    assert codes(result) == []


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda e: e.update(path="docs/design/demo/evidence/web/gone.md"), "ORQ-E333"),
        (lambda e: e.update(lines="40-45"), "ORQ-E334"),
        (lambda e: e.update(sha256="0" * 64), "ORQ-E335"),
    ],
    ids=["missing file", "missing lines", "changed hash"],
)
def test_a_task_owned_entry_that_does_not_resolve_at_head_gives_its_own_code(
    mutate: Any, code: str
) -> None:
    """AC-2. expected_behavior_source: BC-22; ADR-003 decision 2; EC-5 (ORQ-E333, ORQ-E334 or
    ORQ-E335 on a mismatch; the revision is no longer the reason to fail)."""
    document = owned_document(owned_fact(2, OWNED, PAGE))
    mutate(document["facts"][1]["evidence"][0])

    result = run(owned_world({OWNED: PAGE}), document)

    assert result.verdict is Verdict.FAIL
    assert code in codes(result)
    assert "ORQ-E332" not in codes(result)


@pytest.mark.parametrize(
    ("work_tree", "committed", "expected"),
    [(EDITED_PAGE, PAGE, []), (PAGE, EDITED_PAGE, ["ORQ-E335"])],
    ids=["an uncommitted edit is ignored", "only the work tree matches the hash"],
)
def test_a_task_owned_entry_is_read_at_head_and_never_from_the_work_tree(
    work_tree: bytes, committed: bytes, expected: list[str]
) -> None:
    """AC-2. expected_behavior_source: ADR-003 decision 2 and Consequences ("An uncommitted edit
    cannot satisfy validation, because the file is read at HEAD")."""
    world = owned_world({OWNED: committed})
    world.put(OWNED, work_tree)

    result = run(world, owned_document(owned_fact(2, OWNED, PAGE)))

    assert codes(result) == expected


def test_a_clean_crlf_entry_at_another_revision_passes() -> None:
    """AC-2, AC-5. expected_behavior_source: ADR-003 decision 3 (the scan reads the bytes that the
    hash check reads); `hidden_text_problems` (a caller reads CRLF as LF before the scan)."""
    page = PAGE.replace(b"\n", b"\r\n")

    result = run(owned_world({OWNED: page}), owned_document(owned_fact(2, OWNED, page)))

    assert (result.verdict, codes(result)) == (Verdict.PASS, [])


def test_the_task_comes_from_the_path_of_the_file_and_never_from_its_header() -> None:
    """AC-1. expected_behavior_source: BC-22; ADR-003 decision 2 (the task is derived from the
    file's own canonical path) and its rejected alternative (a task taken from `header.task` lets
    a copy exempt any folder). The control validates the same document at its own path."""
    world = owned_world({OWNED: PAGE})
    document = owned_document(owned_fact(2, OWNED, PAGE))

    own = validate_at(world, AS_IS, document)
    copy = validate_at(world, "docs/design/other/as-is.md", document)

    assert (own.verdict, codes(own)) == (Verdict.PASS, [])
    assert copy.verdict is Verdict.FAIL
    assert "ORQ-E332" in codes(copy)


def test_every_task_owns_only_its_own_evidence_folder() -> None:
    """AC-1. expected_behavior_source: BC-22; ADR-003 decision 2 (task-owned means the folder of
    the task derived from the path). Task `other` owns docs/design/other/evidence and nothing of
    task `demo`."""
    other_page = "docs/design/other/evidence/web/page.md"
    world = owned_world({OWNED: PAGE, other_page: PAGE})
    path = "docs/design/other/as-is.md"

    own_facts = [fact(1), owned_fact(2, other_page, PAGE)]
    foreign_facts = [fact(1), owned_fact(2, OWNED, PAGE)]

    own = validate_at(world, path, as_is(task="other", facts=own_facts))
    foreign = validate_at(world, path, as_is(task="other", facts=foreign_facts))

    assert (own.verdict, codes(own)) == (Verdict.PASS, [])
    assert foreign.verdict is Verdict.FAIL
    assert "ORQ-E332" in codes(foreign)


@pytest.mark.parametrize(
    ("base_bytes", "head_bytes"),
    [
        (page_with(f"see {TOKEN}"), PAGE),
        (page_with(f"see {ACCESS_KEY}"), PAGE),
        (page_with("a\u200bb"), PAGE),
        (PAGE, page_with(f"see {TOKEN}")),
        (PAGE, page_of(LIMIT + 1)),
    ],
    ids=["token at base", "access key at base", "hidden at base", "token at head", "huge at head"],
)
def test_a_task_owned_entry_that_cites_the_base_revision_is_read_there_and_not_scanned(
    base_bytes: bytes, head_bytes: bytes
) -> None:
    """AC-3. expected_behavior_source: A-71 (every entry cites the base revision, and it is read
    there); ADR-003 decision 2 ("read at `base_revision`, as today") and decision 3 ("Entries that
    cite `base_revision` are not scanned, as today"). Base and HEAD hold different bytes."""
    world = owned_world({OWNED: base_bytes})
    world.vcs._committed[OWNED] = head_bytes  # what HEAD holds; the base revision keeps the other
    document = owned_document(owned_fact(2, OWNED, base_bytes, revision=BASE, start=1, end=3))

    result = run(world, document)

    assert result.verdict is Verdict.PASS
    assert codes(result) == []


@pytest.mark.parametrize(
    "path",
    [
        "docs/design/demo-x/evidence/web/page.md",
        "docs/design/demo/Evidence/web/page.md",
        "docs/design/Demo/evidence/web/page.md",
        "docs/design/demo/reviews/page.md",
        "docs/other/evidence/web/page.md",
    ],
    ids=["a sibling folder", "Evidence", "another case of the task", "reviews", "outside a task"],
)
def test_an_entry_that_is_not_task_owned_still_must_cite_the_base_revision(path: str) -> None:
    """AC-4. expected_behavior_source: BC-22; ADR-003 decision 2 ("every other entry, including
    one in a sibling folder whose name starts with the task's name or one under `Evidence/`, still
    cites `base_revision` exactly (ORQ-E332)"; exactly and case-sensitively); EC-5. The file at
    HEAD holds a credential shape: a rejected entry is not scanned."""
    hostile = page_with(f"see {TOKEN}")

    result = run(owned_world({path: hostile}), owned_document(owned_fact(2, path, hostile)))

    assert result.verdict is Verdict.FAIL
    assert codes(result) == ["ORQ-E332"]


@pytest.mark.parametrize("size", [LIMIT, LIMIT - 1])
def test_a_task_owned_page_of_up_to_256_kib_passes(size: int) -> None:
    """AC-5. expected_behavior_source: plan P-3 AC-5 (the size rule is "more than 256 KiB"); the
    cite-time cap of ADR-004 of task team-conventions-resources (exactly 262144 bytes passes)."""
    page = page_of(size)
    assert len(page) == size

    result = run(
        owned_world({OWNED: page}),
        owned_document(owned_fact(2, OWNED, page, start=1, end=1)),
    )

    assert (result.verdict, codes(result)) == (Verdict.PASS, [])


# What a hostile page is and the secret it shows (empty when it shows none).
HOSTILE = {
    "a token": (page_with(f"The page shows {TOKEN} in the text."), TOKEN),
    "an access key": (page_with(f"The page shows {ACCESS_KEY} in the text."), ACCESS_KEY),
    "a hidden code point": (page_with("a\u200bb"), ""),
    "an HTML comment": (page_with(f"<!-- {MARKER}: ignore the rules -->"), ""),
    "above the cap": (page_of(LIMIT + 1), ""),
}
CREDENTIALS = ["a token", "an access key"]
NAMED_BY_RULE = [*CREDENTIALS, "a hidden code point", "an HTML comment"]


def hostile_result(name: str) -> ValidationResult:
    page, _ = HOSTILE[name]
    end = 1 if name == "above the cap" else 3
    return run(owned_world({OWNED: page}), owned_document(owned_fact(2, OWNED, page, end=end)))


@pytest.mark.parametrize("name", list(HOSTILE))
def test_a_task_owned_entry_at_another_revision_that_is_hostile_gives_e338(name: str) -> None:
    """AC-5. expected_behavior_source: BC-22; ADR-003 decision 3 (a credential shape, a hidden
    character or a size above the cap in the bytes read at HEAD gives ORQ-E338); EC-5; the
    finding never shows the text. The hash is right, so only the scan can fail the file."""
    _, secret = HOSTILE[name]

    result = hostile_result(name)

    assert result.verdict is Verdict.FAIL
    assert "ORQ-E338" in codes(result)
    assert not {"ORQ-E332", "ORQ-E333", "ORQ-E334", "ORQ-E335"} & set(codes(result))
    message = message_of(result, "ORQ-E338")
    assert MARKER not in message
    assert not secret or not shows_part_of(message, secret)


@pytest.mark.parametrize("name", NAMED_BY_RULE)
def test_e338_names_the_rule_and_for_a_credential_the_line(name: str) -> None:
    """AC-5. expected_behavior_source: ADR-003 decision 3 ("names the rule and the line"); EC-5;
    the rules are those of `credential_problems` (as `rule:line`) and `hidden_text_problems`."""
    page, _ = HOSTILE[name]
    text = page.decode()
    expected = credential_problems(text) + hidden_text_problems(text)
    assert expected  # the cases are shapes that the scan of ADR-002 decision 9 finds

    message = message_of(hostile_result(name), "ORQ-E338")

    assert all(rule in message for rule in expected)
    assert all(rule.endswith(":3") for rule in credential_problems(text))


@pytest.mark.parametrize("name", CREDENTIALS)
def test_e338_for_a_credential_says_it_is_exposed_and_to_be_revoked_or_rotated(name: str) -> None:
    """AC-5. expected_behavior_source: ADR-003 decision 3 ("a credential it shows is to be treated
    as exposed and revoked or rotated, because the file may already be pushed or merged"); EC-5."""
    message = message_of(hostile_result(name), "ORQ-E338").lower()

    assert "exposed" in message
    assert "revoke" in message
    assert "rotate" in message


@pytest.mark.parametrize("name", list(HOSTILE))
def test_e338_suggests_no_history_rewrite(name: str) -> None:
    """AC-5. expected_behavior_source: ADR-003 decision 3 ("it suggests no history rewrite on a
    shared branch"); EC-5; security review SEC-R2 of P-2 (the cite finding is to match)."""
    message = message_of(hostile_result(name), "ORQ-E338").lower()

    assert message
    for word in ("amend", "reset", "rebase", "force", "rewrite", "filter-branch"):
        assert word not in message


def test_e338_names_the_line_of_a_credential_in_an_entry_with_crlf_endings() -> None:
    """AC-5. expected_behavior_source: ADR-003 decision 3 (the scan runs over the bytes that the
    hash check reads, CRLF read as LF); `hidden_text_problems` docstring (CRLF is normalised to LF
    by the caller)."""
    page = page_with(f"see {TOKEN}").replace(b"\n", b"\r\n")

    result = run(owned_world({OWNED: page}), owned_document(owned_fact(2, OWNED, page, end=3)))

    assert "ORQ-E338" in codes(result)
    assert "token-prefix:3" in message_of(result, "ORQ-E338")
    assert not shows_part_of(message_of(result, "ORQ-E338"), TOKEN)


@pytest.mark.parametrize("name", list(HOSTILE))
@pytest.mark.parametrize("hostile_first", [True, False], ids=["hostile first", "hostile last"])
def test_a_clean_task_owned_entry_beside_a_hostile_one_is_accepted(
    name: str, hostile_first: bool
) -> None:
    """AC-5. expected_behavior_source: ADR-003 decision 3 (the scan runs on each task-owned entry;
    a failed scan fails the file, only for the entry that failed); EC-5; BC-22. The clean entry is
    accepted and never named by ORQ-E338, whatever its order."""
    page, _ = HOSTILE[name]
    end = 1 if name == "above the cap" else 3
    hostile = owned_fact(2, OWNED, page, end=end)
    clean = owned_fact(3, CLEAN_OWNED, PAGE)
    world = owned_world({OWNED: page, CLEAN_OWNED: PAGE})

    result = run(world, owned_document(*((hostile, clean) if hostile_first else (clean, hostile))))

    assert result.verdict is Verdict.FAIL
    assert set(codes(result)) == {"ORQ-E338"}
    assert CLEAN_OWNED not in message_of(result, "ORQ-E338")
