"""The link prompt of `init` (task team-conventions-resources, phase P-4).

Every test cites its `expected_behavior_source`. ADR-001 and ADR-002 are the files `adr-00*.md`
under docs/design/team-conventions-resources/design/, EC-n are the expected changes of the
manifest.yaml next to them, and AC-1 to AC-8 are the acceptance criteria of phase P-4 in
docs/design/team-conventions-resources/plan.yaml (AC-5: init with a terminal asks about links and
records the answers in the one plan of init; without a terminal it prints the hint and asks
nothing; an interrupted init converges on a re-run). "The interface decision" is the reading of the
plan author that the Tester of phase P-4 was given, because the ADRs do not spell it out:

`init` gains a link prompt that runs only when the prompter is interactive, `options.assume_yes` is
False and the profile is drafted in this run (a re-run with a profile on disk does not ask and
keeps the registry that is on disk). It asks `prompter.ask(Question(id='resources.links', ...,
options=('yes', 'no'), default='no'))`. On 'yes' it loops: `resources.url` (default ''; an empty
answer ends the loop), then `resources.id`, `resources.title`, `resources.kind` (options
api-guidelines, tool-docs, team-docs, other), `resources.note`, `resources.access` (options
public, login; default public), `resources.paths` (comma separated globs; default '') and
`resources.tool` (default ''; asked only when the kind is tool-docs). Each link is added in memory
with `resources_with(replace=False)`; a link that is refused (finding ORQ-E509) is reported as a
WARNING finding ORQ-E509, without the value, and skipped, and the loop goes on with the next
address; the same link is not asked again. The registry bytes (`contract_bytes` of the result) are
written in the one plan of `init`, after the profile and before the lock, and recorded in the lock
as seeded; with `access: login` the findings hold ORQ-I500. Without a terminal, or with
`assume_yes`, nothing is asked and the findings hold one INFO finding ORQ-I504 whose message says
to run `orqlet resources add`. With no links the registry stays the empty one.

These tests were written first, by the Tester of phase P-4, before the prompt existed.
`ScriptedPrompter` gives one fixed answer for each question id, so the tests of several links use
a prompter of their own that implements the `Prompter` protocol with a queue of links. The file
system is the in-memory fake of tests/fakes and the services are the ones of
tests/support/init_env.py (ORQLET-TEST-001). Credential-shaped text is assembled from parts at run
time and never written as one literal (ORQLET-SEC-003).

Behaviour that the design leaves open is deliberately not pinned here:
- the wording of the WARNING for a refused link (only its code ORQ-E509, its severity and that it
  holds no part of what was typed) and of ORQ-I504 beyond the command that it names;
- whether the fields of a link are still asked after an address that is plainly invalid (only that
  the same address is not asked again);
- the position of the link prompt among the other questions of `init`;
- whether a default is offered for the kind of a link (the tests always answer it);
- whether blanks around a comma in `resources.paths` are trimmed (the tests use none);
- whether ORQ-I504 is absent when the links were asked, and whether a re-run that does not ask
  says anything about links;
- whether a dry run with a terminal asks about links (only that it writes nothing);
- what a first `init` does in a directory that holds a registry but no profile;
- how many times the approval of the plan is asked (only that a no writes nothing).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.render.emit import YamlWriter
from orqlet.application.contracts.generated_lock import GeneratedLock, LockedFile
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.resources import Resource, Resources
from orqlet.application.ports.prompter import NoAnswerAvailable, Question
from orqlet.application.ports.vcs import RepoState
from orqlet.application.usecases.init_files import contract_bytes
from orqlet.application.usecases.init_project import InitOptions, InitResult, init_project
from orqlet.application.usecases.resources_source import load_resources, parse_resources
from orqlet.application.usecases.upgrade import UpgradeOptions, upgrade
from orqlet.domain.digest import sha256_hex
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.ownership import OwnerMode
from orqlet.domain.paths import CanonicalPath
from tests.fakes.prompter import ScriptedPrompter
from tests.fakes.vcs import FakeVcs
from tests.support.init_env import Env, tree
from tests.support.trees import repo

pytestmark = pytest.mark.unit

REGISTRY = ".orqlet/resources.yaml"
LOCK = ".orqlet/generated.lock.yaml"
PROFILE = ".orqlet/project-profile.yaml"
REGISTRY_PATH = CanonicalPath.parse(REGISTRY)
LOADER = StrictYamlLoader()
WRITER = YamlWriter()
LINKS_QUESTION = "resources.links"
HINT = "ORQ-I504"
LOGIN_NOTICE = "ORQ-I500"
REFUSED = "ORQ-E509"
LOGIN_WORDS = ("vendor", "owners", "internal", "login", "text")
# What `init` needs besides the links; the prompter is asked nothing else.
ANSWERS = {
    "repository.target_branch": "main",
    "repository.branch_naming": "",
    "repository.commit_convention": "",
    # Phase P-5 adds seven convention questions; an empty answer keeps each one unknown.
    "repository.branch_model": "",
    "repository.release_flow": "",
    "repository.pull_requests.shape": "",
    "repository.pull_requests.merge_strategy": "",
    "repository.pull_requests.reviewers": "",
    "repository.pull_requests.required_checks": "",
    "reviewer": "Ada",
}
YES = InitOptions(assume_yes=True, answers=ANSWERS)
ASK = InitOptions(answers=ANSWERS)
_MOST_ADDRESSES = 20  # more than any test asks for; a loop that goes on is a defect, not a wait
ALPHA_URL = "https://docs.example.com/guides/alpha"
BETA_URL = "https://wiki.example.com/spaces/team/beta"
# The questions of one link that has the kind team-docs, in the order of the decision.
QUESTIONS_OF_A_LINK = [
    "resources.url",
    "resources.id",
    "resources.title",
    "resources.kind",
    "resources.note",
    "resources.access",
    "resources.paths",
]
# A registry as a team writes it by hand: a comment and its own spacing. A re-run that serialised
# the parsed registry again would lose the comment and rewrite the file.
TEAM_REGISTRY = (
    b"# Links of our team\n"
    b"schema: orqlet.resources/v1\n"
    b"resources:\n"
    b"  - id: api-guide\n"
    b"    title: API guidelines\n"
    b"    kind: api-guidelines\n"
    b"    url: https://docs.example.com/api-guidelines\n"
    b"    note: Read before adding or changing an endpoint.\n"
    b"    access: public\n"
)

# --- credential-shaped values, assembled at run time (ORQLET-SEC-003) -----------------------------

TOKEN = "".join(("gh", "p_", "Zq7Xv3Lm9Tk2", "Rb8Wc4Yd6Hn1", "Pf5Gs0Jx"))
OPAQUE = "".join(("Zq7", "Xv3", "Lm9", "Tk2", "Rb8", "Wc4", "Yd6", "Hn1", "Pf5", "Gs0", "Jx"))


# --- a prompter with a queue of links -------------------------------------------------------------


class LinkPrompter:
    """A `Prompter` for the link prompt: the answers of each link come in turn.

    `resources.links` is answered yes (or no, with `wants_links=False`). Every time
    `resources.url` is asked, the next link of the queue becomes the current one and its address is
    the answer; with no link left the answer is empty, which ends the loop. Every other
    `resources.*` question is answered from the current link, or with the default of the question
    when the link does not say (as a person who presses return). Any other question is answered
    from `others`, and an unscripted one fails loudly. Every confirmation gets `approves`.
    `interactive=False` is a prompter without a terminal: it records the attempt and raises, as
    the real one does.
    """

    def __init__(
        self,
        links: Sequence[Mapping[str, str]] = (),
        *,
        interactive: bool = True,
        wants_links: bool = True,
        approves: bool = True,
        others: Mapping[str, str] | None = None,
    ) -> None:
        self._queue = list(links)
        self._interactive = interactive
        self._wants_links = wants_links
        self._approves = approves
        self._others = dict(others or {})
        self._current: Mapping[str, str] = {}
        self.questions: list[Question] = []
        self.confirmations: list[str] = []
        self.attempts: list[str] = []

    @property
    def interactive(self) -> bool:
        return self._interactive

    def ask(self, question: Question) -> str:
        if not self._interactive:
            self.attempts.append(question.id)
            raise NoAnswerAvailable(question.id)
        self.questions.append(question)
        if question.id == LINKS_QUESTION:
            return "yes" if self._wants_links else "no"
        if question.id == "resources.url":
            # A loop that does not end on an empty address would otherwise hang the suite.
            assert self.link_ids.count("resources.url") <= _MOST_ADDRESSES, "the loop did not end"
            self._current = self._queue.pop(0) if self._queue else {}
            return self._current.get("resources.url", "")
        if question.id.startswith("resources."):
            return self._current.get(question.id, question.default or "")
        if question.id in self._others:
            return self._others[question.id]
        raise AssertionError(f"unscripted question: {question.id}")

    def confirm(self, text: str, *, default: bool = False) -> bool:
        if not self._interactive:
            self.attempts.append(text)
            raise NoAnswerAvailable(text)
        self.confirmations.append(text)
        return self._approves

    # --- what the tests look at ---------------------------------------------------------------
    @property
    def link_ids(self) -> list[str]:
        """The ids of the questions of the loop, in the order they were asked."""
        return [
            question.id
            for question in self.questions
            if question.id.startswith("resources.") and question.id != LINKS_QUESTION
        ]

    @property
    def link_prompts(self) -> int:
        return sum(1 for question in self.questions if question.id == LINKS_QUESTION)

    def first(self, question_id: str) -> Question:
        return next(question for question in self.questions if question.id == question_id)


def link(url: str, resource_id: str, title: str, **answers: str) -> dict[str, str]:
    """The answers of one link of the kind team-docs; a key that is left out gets the default."""
    return {
        "resources.url": url,
        "resources.id": resource_id,
        "resources.title": title,
        "resources.kind": "team-docs",
        "resources.note": "Read before changing the module.",
        **{f"resources.{key}": value for key, value in answers.items()},
    }


# --- helpers --------------------------------------------------------------------------------------


def existing_env() -> Env:
    return Env(project=repo("uv_fastapi"), vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"))


def run(env: Env, prompter: LinkPrompter, options: InitOptions = ASK) -> InitResult:
    return init_project(replace(env.services(), prompter=prompter), options)


def registry_of(env: Env) -> Resources:
    resources, findings = load_resources(env.project, LOADER, REGISTRY)
    assert resources is not None, findings
    return resources


def entry_of(resources: Resources, resource_id: str) -> Resource:
    return next(item for item in resources.resources if item.id == resource_id)


def ids_of(resources: Resources) -> list[str]:
    return [item.id for item in resources.resources]


def read(env: Env, name: str) -> bytes:
    return env.project.read_bytes(CanonicalPath.parse(name))


def lock_entry(env: Env, name: str) -> LockedFile | None:
    lock = load_contract(LOADER, GeneratedLock, read(env, LOCK), source=LOCK)
    return next((item for item in lock.files if item.path == name), None)


def codes(result: InitResult) -> set[str]:
    return {finding.code for finding in result.findings}


def only(result: InitResult, code: str) -> list[Finding]:
    return [finding for finding in result.findings if finding.code == code]


def leaks(text: str, secret: str, width: int = 8) -> bool:
    """True when `text` shows `secret` or `width` characters of it in a row (any letter case)."""
    needle = secret.lower()
    haystack = text.lower()
    size = min(width, len(needle))
    return any(needle[start : start + size] in haystack for start in range(len(needle) - size + 1))


def applied_order(result: InitResult) -> list[str]:
    """The paths of the plan in the order in which `apply_plan` writes them: the lock last."""
    assert result.plan is not None
    ordered = sorted(result.plan.writes, key=lambda write: (write.last, write.path.sort_key()))
    return [str(write.path) for write in ordered]


def shown(findings: Sequence[Finding]) -> str:
    return "\n".join(f"{f.code}\n{f.message}\n{f.path}\n{f!r}" for f in findings)


# --- the question ---------------------------------------------------------------------------------


def test_a_terminal_is_asked_once_whether_there_are_links_with_options_yes_no_and_default_no() -> (
    None
):
    """AC-5. expected_behavior_source: the interface decision ("It asks `prompter.ask(Question(
    id='resources.links', ..., options=('yes','no'), default='no'))`")."""
    env = existing_env()
    prompter = LinkPrompter(wants_links=False)

    result = run(env, prompter)

    assert result.status == "applied", result.findings
    assert prompter.link_prompts == 1
    question = prompter.first(LINKS_QUESTION)
    assert question.options == ("yes", "no")
    assert question.default == "no"


def test_the_default_answer_leaves_the_empty_registry_and_asks_nothing_else() -> None:
    """AC-5. expected_behavior_source: the interface decision ("default='no'"; "With no links the
    registry stays the empty one") and plan P-4 file operation for test_init_project.py ("the
    interactive tests script ... the answer no"): a person who only presses return, as the fake
    `ScriptedPrompter` does with the default of a question, gets no loop."""
    env = existing_env()
    prompter = ScriptedPrompter(interactive=True, confirm_all=True)

    result = init_project(replace(env.services(), prompter=prompter), ASK)

    assert result.status == "applied", result.findings
    assert LINKS_QUESTION in prompter.asked
    assert not [name for name in prompter.asked if name.startswith("resources.url")]
    assert registry_of(env).resources == ()


def test_a_no_asks_nothing_else_and_leaves_the_empty_registry() -> None:
    """AC-5. expected_behavior_source: the interface decision (the loop runs "on 'yes'") and plan
    P-3 AC-2 (`init` writes an empty registry)."""
    env = existing_env()
    prompter = LinkPrompter([link(ALPHA_URL, "alpha", "Alpha guide")], wants_links=False)

    result = run(env, prompter)

    assert result.status == "applied", result.findings
    assert prompter.link_ids == []
    assert registry_of(env).resources == ()


# --- one link, several links, the end of the loop -------------------------------------------------


def test_one_link_is_written_in_the_plan_of_init_after_the_profile_and_before_the_lock() -> None:
    """AC-5. expected_behavior_source: AC-5 ("records the answers in the one plan of init"), the
    interface decision ("written in the one plan of init, after the profile and before the lock")
    and ADR-002 decision 6 ("the plan writes the profile before the registry")."""
    env = existing_env()
    prompter = LinkPrompter([link(ALPHA_URL, "alpha", "Alpha guide")])

    result = run(env, prompter)

    assert result.status == "applied", result.findings
    order = applied_order(result)
    assert order.index(PROFILE) < order.index(REGISTRY) < order.index(LOCK)
    assert order[-1] == LOCK
    found = entry_of(registry_of(env), "alpha")
    assert (found.url, found.title, found.kind, found.access) == (
        ALPHA_URL,
        "Alpha guide",
        "team-docs",
        "public",
    )
    assert found.note == "Read before changing the module."


def test_the_registry_is_written_as_the_contract_serialises_it_and_recorded_as_seeded() -> None:
    """AC-5. expected_behavior_source: the interface decision ("The registry bytes (`contract_bytes`
    of the result) ... recorded seeded in the lock") and ADR-002 decision 1 (owner seeded, no file
    class)."""
    env = existing_env()
    run(env, LinkPrompter([link(ALPHA_URL, "alpha", "Alpha guide")]))

    registry = registry_of(env)

    assert read(env, REGISTRY) == contract_bytes(WRITER, registry)
    recorded = lock_entry(env, REGISTRY)
    assert recorded is not None
    assert recorded.owner is OwnerMode.SEEDED
    assert recorded.file_class is None
    assert recorded.seeded_sha256 == sha256_hex(read(env, REGISTRY))


def test_several_links_are_written_in_order_of_id_whatever_the_order_they_were_typed() -> None:
    """AC-5. expected_behavior_source: AC-5 ("several links") and ADR-002 decision 1 (the entries
    are written in order of id)."""
    env = existing_env()
    links = [
        link("https://docs.example.com/zeta", "zeta", "Zeta"),
        link("https://docs.example.com/alpha", "alpha", "Alpha"),
        link("https://docs.example.com/mid", "mid", "Mid"),
    ]

    result = run(env, LinkPrompter(links))

    assert result.status == "applied", result.findings
    assert ids_of(registry_of(env)) == ["alpha", "mid", "zeta"]


def test_an_empty_address_ends_the_loop_at_once() -> None:
    """AC-5. expected_behavior_source: AC-5 ("the empty address that ends the loop") and the
    interface decision ("`resources.url` (default ''; an empty answer ends the loop)")."""
    env = existing_env()
    prompter = LinkPrompter()

    result = run(env, prompter)

    assert result.status == "applied", result.findings
    assert prompter.link_ids == ["resources.url"]
    assert registry_of(env).resources == ()


def test_the_loop_asks_for_the_next_address_until_it_gets_an_empty_one() -> None:
    """AC-5. expected_behavior_source: the interface decision ("it loops": the address is asked
    again after each link until an empty answer ends the loop)."""
    env = existing_env()
    prompter = LinkPrompter(
        [link(ALPHA_URL, "alpha", "Alpha"), link("https://docs.example.com/beta", "beta", "Beta")]
    )

    run(env, prompter)

    assert prompter.link_ids.count("resources.url") == 3  # two links and the empty address


# --- the questions of a link ----------------------------------------------------------------------


def test_the_questions_of_a_link_come_in_the_order_of_the_decision() -> None:
    """AC-5. expected_behavior_source: the interface decision (`resources.url`, then
    `resources.id`, `resources.title`, `resources.kind`, `resources.note`, `resources.access`,
    `resources.paths`; `resources.tool` only when the kind is tool-docs)."""
    env = existing_env()
    prompter = LinkPrompter([link(ALPHA_URL, "alpha", "Alpha guide")])

    run(env, prompter)

    assert prompter.link_ids == [*QUESTIONS_OF_A_LINK, "resources.url"]


def test_a_tool_docs_link_is_asked_for_its_tool_after_the_paths_and_the_tool_is_kept() -> None:
    """AC-5. expected_behavior_source: the interface decision ("`resources.tool` (default ''; asked
    only when kind is tool-docs)") and ADR-002 decision 1 (the tool is for `tool-docs`)."""
    env = existing_env()
    prompter = LinkPrompter(
        [
            link(
                "https://docs.example.com/fastapi",
                "fastapi-docs",
                "FastAPI",
                kind="tool-docs",
                tool="FastAPI",
            )
        ]
    )

    result = run(env, prompter)

    assert result.status == "applied", result.findings
    assert prompter.link_ids == [*QUESTIONS_OF_A_LINK, "resources.tool", "resources.url"]
    assert registry_of(env).covered_tools() == ("FastAPI",)


@pytest.mark.parametrize("kind", ["api-guidelines", "team-docs", "other"])
def test_the_tool_is_not_asked_for_another_kind(kind: str) -> None:
    """AC-5. expected_behavior_source: the interface decision (`resources.tool` "asked only when
    kind is tool-docs")."""
    env = existing_env()
    prompter = LinkPrompter([link(ALPHA_URL, "alpha", "Alpha guide", kind=kind)])

    run(env, prompter)

    assert "resources.tool" not in prompter.link_ids
    assert entry_of(registry_of(env), "alpha").kind == kind


def test_the_questions_have_the_options_and_defaults_of_the_decision() -> None:
    """AC-5. expected_behavior_source: the interface decision (`resources.url` default ''; the
    options of `resources.kind` are api-guidelines, tool-docs, team-docs, other; the options of
    `resources.access` are public, login with the default public; `resources.paths` default '';
    `resources.tool` default ''). The default of the kind is not stated, so it is not pinned."""
    env = existing_env()
    prompter = LinkPrompter(
        [link(ALPHA_URL, "alpha", "Alpha guide", kind="tool-docs", tool="Alpha")]
    )

    run(env, prompter)

    assert prompter.first("resources.url").default == ""
    assert prompter.first("resources.kind").options == (
        "api-guidelines",
        "tool-docs",
        "team-docs",
        "other",
    )
    access = prompter.first("resources.access")
    assert access.options == ("public", "login")
    assert access.default == "public"
    assert prompter.first("resources.paths").default == ""
    assert prompter.first("resources.tool").default == ""


def test_a_person_who_presses_return_for_access_and_paths_gets_a_public_link_without_paths() -> (
    None
):
    """AC-5. expected_behavior_source: the interface decision (the defaults: access public, paths
    '', tool '')."""
    env = existing_env()

    run(env, LinkPrompter([link(ALPHA_URL, "alpha", "Alpha guide")]))

    found = entry_of(registry_of(env), "alpha")
    assert found.access == "public"
    assert not (found.applies_to and found.applies_to.paths)
    assert found.tool is None


def test_the_paths_are_comma_separated_globs() -> None:
    """AC-5. expected_behavior_source: the interface decision (`resources.paths` is "comma
    separated globs")."""
    env = existing_env()
    paths = "src/api/**/*.py,tests/api/**/*.py"

    run(env, LinkPrompter([link(ALPHA_URL, "alpha", "Alpha guide", paths=paths)]))

    found = entry_of(registry_of(env), "alpha")
    assert found.applies_to is not None
    assert found.applies_to.paths == ("src/api/**/*.py", "tests/api/**/*.py")


# --- a link that the builder refuses --------------------------------------------------------------


def test_a_refused_link_is_skipped_with_a_warning_e509_and_the_next_one_is_added() -> None:
    """AC-5. expected_behavior_source: AC-5 ("an invalid address ... skipped"), the interface
    decision ("a link that is refused (finding ORQ-E509) is reported as a WARNING finding ORQ-E509
    ... and skipped, and the loop continues with the next address") and plan P-4 AC-1 (an invalid
    address is refused with ORQ-E509)."""
    env = existing_env()
    prompter = LinkPrompter(
        [
            link("http://docs.example.com/plain", "plain", "Plain http"),
            link("https://docs.example.com/good", "good", "Good"),
        ]
    )

    result = run(env, prompter)

    assert result.status == "applied", result.findings
    assert ids_of(registry_of(env)) == ["good"]
    (warning,) = only(result, REFUSED)
    assert warning.severity is Severity.WARNING


def test_the_same_address_is_not_asked_again_after_a_refusal() -> None:
    """AC-5. expected_behavior_source: the interface decision ("there is no re-ask of the same
    link"): two links, the first one refused, and the end of the loop are three addresses."""
    env = existing_env()
    prompter = LinkPrompter(
        [
            link("http://docs.example.com/plain", "plain", "Plain http"),
            link("https://docs.example.com/good", "good", "Good"),
        ]
    )

    run(env, prompter)

    assert prompter.link_ids.count("resources.url") == 3


def test_each_refused_link_has_its_own_warning() -> None:
    """AC-5. expected_behavior_source: the interface decision ("a link that is refused ... is
    reported as a WARNING finding ORQ-E509")."""
    env = existing_env()
    prompter = LinkPrompter(
        [
            link("http://docs.example.com/one", "one", "One"),
            link("https://docs.example.com/two", "two", "Two"),
            link("https://docs.example.com/three#frag", "three", "Three"),
        ]
    )

    result = run(env, prompter)

    assert result.status == "applied", result.findings
    assert ids_of(registry_of(env)) == ["two"]
    assert len(only(result, REFUSED)) == 2


def test_a_link_whose_id_is_taken_by_an_earlier_link_is_skipped_and_the_first_is_kept() -> None:
    """AC-5. expected_behavior_source: the interface decision (each link is added with
    `resources_with(replace=False)`, which refuses a repeated id) and plan P-3 AC-6 (the builder
    refuses a repeated id)."""
    env = existing_env()
    prompter = LinkPrompter(
        [
            link("https://docs.example.com/first", "alpha", "First"),
            link("https://docs.example.com/second", "alpha", "Second"),
        ]
    )

    result = run(env, prompter)

    assert result.status == "applied", result.findings
    assert entry_of(registry_of(env), "alpha").title == "First"
    assert len(only(result, REFUSED)) == 1


def test_the_warning_for_a_refused_link_shows_no_part_of_what_was_typed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC-5. expected_behavior_source: the interface decision ("reported as a WARNING finding
    ORQ-E509 (without the value)"), ORQLET-SEC-003 and ADR-002 decision 10."""
    env = existing_env()
    prompter = LinkPrompter(
        [
            link(
                f"https://docs.example.com/guide?token={TOKEN}",
                "leaky",
                f"[{OPAQUE}](x)",
                note=f"use `{OPAQUE}` first",
            ),
            link(ALPHA_URL, "esc", "two\x1b[2Jlines"),
        ]
    )

    result = run(env, prompter)
    streams = capsys.readouterr()

    assert registry_of(env).resources == ()
    assert len(only(result, REFUSED)) == 2
    text = shown(result.findings)
    for secret in (TOKEN, OPAQUE):
        assert not leaks(text, secret)
        assert not leaks(streams.out, secret)
        assert not leaks(streams.err, secret)
    assert "\x1b" not in text


# --- the notice for a login link ------------------------------------------------------------------


def test_a_link_of_access_login_gives_the_notice_about_the_model_vendor() -> None:
    """AC-5, AC-7. expected_behavior_source: the interface decision ("with `access: login` the
    findings of init contain ORQ-I500") and AC-7 / ADR-001 consequences (the words: page text goes
    to the client's model vendor; using the login route for internal content is an owners'
    decision)."""
    env = existing_env()

    result = run(env, LinkPrompter([link(BETA_URL, "beta", "Beta wiki", access="login")]))

    assert result.status == "applied", result.findings
    (notice,) = only(result, LOGIN_NOTICE)
    assert notice.severity is Severity.INFO
    assert all(word in notice.message.lower() for word in LOGIN_WORDS)
    assert entry_of(registry_of(env), "beta").access == "login"


def test_a_public_link_gives_no_notice() -> None:
    """AC-5, AC-7. expected_behavior_source: the interface decision (the notice is for
    `access: login`)."""
    env = existing_env()

    result = run(env, LinkPrompter([link(ALPHA_URL, "alpha", "Alpha guide")]))

    assert LOGIN_NOTICE not in codes(result)


# --- without a terminal, and with --yes --------------------------------------------------------


def test_without_a_terminal_init_asks_nothing_and_says_how_to_add_links() -> None:
    """AC-5. expected_behavior_source: AC-5 ("without a terminal it prints the hint and asks
    nothing") and the interface decision ("Without a terminal ... nothing is asked and the
    findings contain one INFO finding ORQ-I504 whose message says to run `orqlet resources
    add`")."""
    env = existing_env()
    prompter = LinkPrompter([link(ALPHA_URL, "alpha", "Alpha guide")], interactive=False)

    result = run(env, prompter, YES)

    assert result.status == "applied", result.findings
    assert prompter.attempts == []
    (hint,) = only(result, HINT)
    assert hint.severity is Severity.INFO
    assert "orqlet resources add" in hint.message
    assert registry_of(env).resources == ()


def test_with_yes_at_a_terminal_init_asks_nothing_about_links_and_gives_the_hint() -> None:
    """AC-5. expected_behavior_source: the interface decision (the prompt runs only when
    `options.assume_yes` is False; "Without a terminal, or with assume_yes, nothing is asked and
    the findings contain one INFO finding ORQ-I504")."""
    env = existing_env()
    prompter = LinkPrompter([link(ALPHA_URL, "alpha", "Alpha guide")], others=ANSWERS)

    result = run(env, prompter, YES)

    assert result.status == "applied", result.findings
    assert prompter.link_prompts == 0
    assert prompter.link_ids == []
    (hint,) = only(result, HINT)
    assert hint.severity is Severity.INFO
    assert "orqlet resources add" in hint.message
    assert registry_of(env).resources == ()


# --- a profile that is already on disk ------------------------------------------------------------


def _interrupted(env: Env) -> None:
    """The state of an `init` that stopped before it wrote the lock: the profile, no lock."""
    env.project.delete(CanonicalPath.parse(LOCK))


@pytest.mark.parametrize("on_disk", [None, TEAM_REGISTRY], ids=["empty-registry", "team-registry"])
def test_a_re_run_with_the_profile_on_disk_asks_nothing_and_keeps_the_registry_as_it_is(
    on_disk: bytes | None,
) -> None:
    """AC-5. expected_behavior_source: the interface decision ("a re-run with a profile on disk
    does not ask and keeps the registry on disk") and ADR-002 decision 6 ("a re-run after an
    interruption reads what is on disk, as `_load_existing_profile` does for the profile")."""
    env = existing_env()
    assert run(env, LinkPrompter(wants_links=False)).status == "applied"
    if on_disk is not None:
        env.project.write_atomic(REGISTRY_PATH, on_disk)
    _interrupted(env)
    kept = read(env, REGISTRY)
    prompter = LinkPrompter([link(ALPHA_URL, "alpha", "Alpha guide")])

    result = run(env, prompter)

    assert result.status == "applied", result.findings
    assert prompter.link_prompts == 0
    assert prompter.link_ids == []
    assert read(env, REGISTRY) == kept
    recorded = lock_entry(env, REGISTRY)
    assert recorded is not None
    assert recorded.seeded_sha256 == sha256_hex(kept)


def test_a_re_run_does_not_add_the_links_of_the_interrupted_run_again() -> None:
    """AC-5. expected_behavior_source: the interface decision (the registry that is on disk is
    kept and nothing is asked) with ADR-002 decision 6: the links of the first run are in the
    registry, so the re-run gives the same registry bytes."""
    env = existing_env()
    run(env, LinkPrompter([link(ALPHA_URL, "alpha", "Alpha guide")]))
    written = read(env, REGISTRY)
    _interrupted(env)

    result = run(env, LinkPrompter([link(BETA_URL, "beta", "Beta wiki")]))

    assert result.status == "applied", result.findings
    assert read(env, REGISTRY) == written
    assert ids_of(registry_of(env)) == ["alpha"]


# --- the plan: preview, approval and the next upgrade ---------------------------------------------


def test_a_dry_run_writes_nothing() -> None:
    """AC-5. expected_behavior_source: ORQLET-SAFE-001 (a plan can be previewed; nothing is
    written). Whether a dry run asks about links is not pinned; the registry that a dry run plans
    is valid in either case."""
    env = existing_env()
    before = tree(env.project)
    prompter = LinkPrompter([link(ALPHA_URL, "alpha", "Alpha guide")])

    result = run(env, prompter, InitOptions(dry_run=True, answers=ANSWERS))

    assert result.status == "previewed"
    assert result.plan is not None
    (write,) = [w for w in result.plan.writes if str(w.path) == REGISTRY]
    assert write.content is not None
    planned, findings = parse_resources(LOADER, write.content, "the planned registry")
    assert findings == ()
    assert planned is not None
    assert tree(env.project) == before


def test_links_typed_before_a_declined_plan_are_not_written() -> None:
    """AC-5. expected_behavior_source: ORQLET-SAFE-001 (every write goes through a plan that a
    person approves) and the interface decision (the registry is written in the one plan of
    `init`, so a plan that is not approved leaves nothing)."""
    env = existing_env()
    before = tree(env.project)
    prompter = LinkPrompter([link(ALPHA_URL, "alpha", "Alpha guide")], approves=False)

    result = run(env, prompter)

    assert result.status == "previewed"
    assert prompter.link_prompts == 1
    assert tree(env.project) == before


def test_links_typed_before_an_approved_plan_are_written() -> None:
    """AC-5. expected_behavior_source: the interface decision (the registry is written in the one
    plan of `init`) with an approval given at the terminal instead of `--yes`."""
    env = existing_env()
    prompter = LinkPrompter([link(ALPHA_URL, "alpha", "Alpha guide")], approves=True)

    result = run(env, prompter)

    assert result.status == "applied", result.findings
    assert ids_of(registry_of(env)) == ["alpha"]


def test_the_next_upgrade_makes_no_proposal_and_leaves_the_registry_alone() -> None:
    """AC-5. expected_behavior_source: ADR-002 decisions 5 and 6 (the registry is recorded in the
    lock with the hash of what `init` wrote, so it makes no proposal) and plan P-3 AC-2. The test
    does not say that the upgrade has nothing at all to do: from phase P-6 on it renders files from
    the registry."""
    env = existing_env()
    run(
        env,
        LinkPrompter(
            [
                link(ALPHA_URL, "alpha", "Alpha guide"),
                link(BETA_URL, "beta", "Beta", access="login"),
            ]
        ),
    )
    registry = read(env, REGISTRY)

    result = upgrade(env.services(), UpgradeOptions(check=True))

    planned = {str(w.path) for w in result.plan.writes} if result.plan is not None else set()
    assert result.status in {"up-to-date", "available"}, result.findings
    assert REGISTRY not in planned
    assert not any(name.startswith(".orqlet/proposals/") for name in tree(env.project))
    assert read(env, REGISTRY) == registry
