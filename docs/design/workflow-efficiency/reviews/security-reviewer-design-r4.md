# Security review of the design, round 4

- Role: orqlet-security-reviewer, started as a typed Cursor subagent in a clean context (agent 5d970e0c-9f0b-47a2-a411-ab2effc7f615).
- Inputs given: the design folder, `as-is.md`, `questions.yaml`, `.agents/skills/orqlet-design/references/design-format.md` and the saved output of `orqlet standards for` (`/tmp/orqlet-workflow-efficiency-standards.txt`); nothing else.
- Model requested: none named, so the subagent inherits the parent session's model. Model observed: unknown; the client reports no identity to the agent. The reviewer reports Claude Opus 5.5 from its own system prompt, which is a claim, not an observation.
- Context freshness: fresh; the subagent received only the prompt above.
- Design bound at `86e07abc18e95eef98d11923fd1aff72451ad7c2`, after the rebase of `workflow-efficiency-design` onto main and the merge of the Q-21 research refresh (pull request 56). The main session confirmed HEAD at that commit; the reviewer could not.
- Hashes when the reviewer started and when this note was saved (unchanged between the two, and equal to the manifest's):
  - manifest.yaml cc6cb9673ff946212f65cac85ea0f40002b60ddcce2e77cdb41d2caba0404127
  - component.md ceea38809b420a4a21ac20b1d2c6f16008a463cf486763c5ae423c77c293818f
  - views.md d2074851ae068b42a6e9621ad29337043bd65236e9ee3da8b8f145f85d6a76eb
  - adr-001 61115867e69d0b6ba4cd4e54f64415f468912f904cf6cdbc07b9fe6b54a5442f
  - adr-002 c25d07e15d31bc9e1758f37322c2839e4374e818b6b34f2a8137d33e789a3f77
  - adr-003 eba0f31005e5f65a58033cda061aa544f1f02bb8caa7229d97c416a6bec60402
  - adr-004 6c1d8e9e1b63663f85dea1393866438161c1904e20a51f4f3382321372175bb8
- This is the fourth round, which the person chose at the round-3 cap. The quote digests in the findings were not computed by the reviewer and are left as it wrote them.

## Reviewer output (unchanged)

The design has no blocking security finding; I found five non-blocking ones. The squash-merge evidence exemption held up on every path, case, link and scan check I made. Shell commands were blocked in this session, so I could not compute quote digests or confirm HEAD; both need filling in before the note is saved.

# security-reviewer — design — round 4

- **Task / phase:** `workflow-efficiency` / design
- **Revision:** the design files and code were read in the working tree. You gave HEAD as `86e07abc18e95eef98d11923fd1aff72451ad7c2`; I could not confirm it.
- **Verdict:** PASS, advisory. It has no blocking finding and five non-blocking ones (SEC-R4-1 to SEC-R4-5), plus two observations.
- **Quote digests:** not computed. Each `quote_sha256` below needs `orqlet evidence cite <file> <lines> --revision <HEAD>` before saving. The design files are uncommitted, so their quotes are working-tree text.

## Findings

```yaml
- schema: orqlet.finding/v1
  id: SEC-R4-1
  kind: finding
  severity: non-blocking
  category: process-access
  evidence:
    - {kind: quote, path: docs/design/workflow-efficiency/design/adr-001-check-reuse-and-rechecking.md, lines: "10", revision: working-tree, quote: "The agent records HEAD and the output of `git status --porcelain` at each passing run", quote_sha256: not-computed}
    - {kind: quote, path: src/orqlet/adapters/git/git_runner.py, lines: 3-5, revision: 86e07abc (unverified), quote: "Anything that executes configured programs on a read (`status`, porcelain `diff`, `add`, `checkout`) is not on the list.", quote_sha256: not-computed}
    - {kind: quote, path: src/orqlet/adapters/git/git_runner.py, lines: 34-36, revision: 86e07abc (unverified), quote: "`diff-index HEAD` compares the working tree and so runs the `filter.*.clean` program on every modified file", quote_sha256: not-computed}
    - {kind: quote, path: docs/design/workflow-efficiency/design/manifest.yaml, lines: "118", revision: working-tree, quote: "No new process, network path, dependency, credential or trust boundary", quote_sha256: not-computed}
  claim: >
    ADR-001 decision 2 adds `git status --porcelain`, run by the agent at every passing run and
    before every reuse. Decision 1 keeps a working-tree `git diff --quiet`, now against the cited
    revision. Both run in the person's shell, outside the hardened Git runner. The project's own
    threat model says these forms run programs that the repository's configuration names (the
    clean filter, fsmonitor). Today's contract already has the working-tree diff, so the risk
    class is not new. The status call is new and repeated, though, and the security
    consideration says "no new process" without naming this residual risk.
  suggested_action: >
    Either record the residual risk in considerations.security and in ADR-001's consequences, or
    compare the cited and modified files with `orqlet evidence hash`, which reads through the
    FileSystem port, instead of git status/diff. The runner's `-c core.fsmonitor=false
    -c core.hooksPath=` prefix covers fsmonitor and hooks. By the runner's own comment, it does
    not stop clean filters on a working-tree comparison.
  confidence: medium

- schema: orqlet.finding/v1
  id: SEC-R4-2
  kind: finding
  severity: non-blocking
  category: review-integrity
  evidence:
    - {kind: quote, path: docs/design/workflow-efficiency/design/adr-001-check-reuse-and-rechecking.md, lines: "13", revision: working-tree, quote: "Design hashes its files once before starting the reviewers; the validator's hash check shows any later change, which starts a new round.", quote_sha256: not-computed}
    - {kind: quote, path: src/orqlet/workflow/skills/orqlet-design/skill.md, lines: "35", revision: 86e07abc (unverified), quote: "Run `orqlet evidence hash` on the design files when you start each reviewer and again when you save its note, and record the hashes in the note.", quote_sha256: not-computed}
    - {kind: quote, path: src/orqlet/application/usecases/validate_design.py, lines: 224-236, revision: 86e07abc (unverified), quote: "if read_file(services, review.note) is None:", quote_sha256: not-computed}
    - {kind: quote, path: src/orqlet/application/usecases/validate_design.py, lines: 119-126, revision: 86e07abc (unverified), quote: "if content_hash(data) != artifact.sha256:", quote_sha256: not-computed}
  claim: >
    The validator only compares each artifact with the manifest's hash (ORQ-E356) and checks
    that the review notes exist. It never compares the hashes a reviewer saw with the final
    files. Two kinds of edit would slip through: an edit made together with an updated manifest
    hash, and any edit to manifest.yaml itself, since no artifact entry carries its hash. That
    covers scope, security_globs, trust_boundaries and EC-8. Today a hash is also taken when each
    note is saved; dropping it leaves the review window uncovered. The design also does not say
    that notes keep recording hashes.
  suggested_action: >
    State that each note records the hashes the reviewer saw, manifest.yaml included, and that
    the skill compares them with the files before STOP: one `evidence hash` call. Otherwise,
    correct the claim and name the uncovered window.
  confidence: medium

- schema: orqlet.finding/v1
  id: SEC-R4-3
  kind: finding
  severity: non-blocking
  category: authorization
  evidence:
    - {kind: quote, path: docs/design/workflow-efficiency/design/adr-002-plain-cli-results.md, lines: "16", revision: working-tree, quote: "PASS: \"No action needed.\" and, when there are warnings, \"Read the N warning(s) above.\"", quote_sha256: not-computed}
    - {kind: quote, path: docs/design/workflow-efficiency/design/adr-002-plain-cli-results.md, lines: "25", revision: working-tree, quote: "A PASS from `gate status` could be misread as approval", quote_sha256: not-computed}
  claim: >
    With a task, gate status now reaches PASS. Its last line would be "No action needed.", while
    ORQ-I393, an info finding that the action line does not count, is the only place that says
    approval was not checked. An agent reading the human text gets a closing line that suggests
    the gate is done. The mitigation is the skills' input check, which is text only.
  suggested_action: >
    For gate status with a task, make the PASS line say that approval is still confirmed by the
    input check, for example "No action needed from gate status; the input check still confirms
    approval." Put the wording in ADR-002 decision 2, EC-3 and BC-9.
  confidence: medium

- schema: orqlet.finding/v1
  id: SEC-R4-4
  kind: finding
  severity: non-blocking
  category: command-provenance
  evidence:
    - {kind: quote, path: docs/design/workflow-efficiency/design/adr-001-check-reuse-and-rechecking.md, lines: "9", revision: working-tree, quote: "The tester's report lists the citations it made (path, lines, revision and sha256) so the coder can reuse them", quote_sha256: not-computed}
    - {kind: quote, path: src/orqlet/workflow/skills/orqlet-research/references/phase-contract.md, lines: "29", revision: 86e07abc (unverified), quote: "any other difference, a different hash or a plan text that differs from the cited lines beyond placeholders stops the work", quote_sha256: not-computed}
  claim: >
    The rule that a different hash stops the work keeps a changed CI or config source from
    running unreviewed. With reuse, that comparison against the plan rests on the tester's own
    report, which comes from a separate agent context. The coder's `git diff` only proves that
    nothing changed after the tester's cited revision. It does not prove that the tester's hash
    matched the plan.
  suggested_action: >
    State that the coder compares each reused citation's sha256 with the plan's recorded hash,
    and checks its revision and path against the "Values from artifacts" character rule, before
    relying on it. A batched `evidence cite` (EC-2) is the alternative, at one call per phase.
  confidence: medium

- schema: orqlet.finding/v1
  id: SEC-R4-5
  kind: finding
  severity: non-blocking
  category: injection
  evidence:
    - {kind: quote, path: docs/design/workflow-efficiency/design/adr-004-concise-documents-and-replies.md, lines: "10", revision: working-tree, quote: "one copyable block with only the task name, the next skill or action, artifact paths and the approvals still needed", quote_sha256: not-computed}
    - {kind: quote, path: src/orqlet/domain/paths.py, lines: 30-48, revision: 86e07abc (unverified), quote: "if char in {\"\\\\\", \":\"}:", quote_sha256: not-computed}
  claim: >
    The person pastes the next prompt into a new session with their own authority. The task name
    is safe because the Slug format constrains it. "Artifact paths", however, are not limited:
    canonical paths allow spaces and any printable text. A file name could therefore carry
    instruction text into that prompt.
  suggested_action: >
    Limit the paths to the workflow's fixed artifact paths under docs/design/<task>/, or apply
    the phase contract's character rule (letters, digits, `.`, `_`, `-`, `/`) to each path in
    the prompt.
  confidence: low
```

## Observations (no evidence that they block)

- **O-1:** `validate as-is` would read task-owned evidence at the literal `HEAD` (`objects.py:20-33`). I suggest resolving HEAD once per run to a full commit id and reporting it in `data`. The result would then name exactly what was read, and a HEAD that moves during the run cannot mix reads.
- **O-2:** `test_workflow_phase_contract_text.py:235-312` pins the security phrases of the phase contract. Two of the pinned phrases are the ones the design removes ("cite every source again" and "`git diff --quiet HEAD -- <cited files>`"). The plan should say that only these two pinned phrases change.

## Absence record: checked, no finding

The record covers the design at `86e07abc` (unverified) plus the working-tree design files, read with file tools only.

- **Task-owned evidence path (EC-5, ADR-003):**
  - The task is taken from the file's path, not from `header.task`. `_TASK_PATH` only accepts the lowercase task-name format.
  - `CanonicalPath` rejects `.`, `..`, control characters and `.git` (`paths.py:30-48`).
  - `read_blobs` reads Git objects through `cat-file --batch` and never follows a link in the work tree (`objects.py:20-33`).
  - The four-part prefix is case-sensitive and the Git read is exact, so a mismatch fails as ORQ-E333.
  - The scan covers the same bytes as the hash check.
  - `credential_problems` returns `rule:line` and never the text (`resources.py:407-424`).
- **Batched `evidence cite` (EC-2):** a refused pair carries no hash, and web pairs keep the cite-time scan (`evidence_cite.py:56-57, 89-113`).
- **`gate status` task argument:** checking it against the task-name format adds defence in depth. Today `read_file` already rejects path traversal (`gate_status.py:148-156`).
- **Code changes:** I found no new subprocess, network path or dependency in the code the design touches. Git stays behind the allow-listed runner.
- **Instruction text:**
  - The skills keep the paragraph that treats source text as evidence.
  - The next prompt excludes copied source text and project commands.
  - Approval is still checked only by the input check.

## Self-check

- **Model:** Claude Opus 5.5, per this session's system prompt. No client-observed identity was available.
- **Context:** fresh. I received only the paths you named, with no earlier review notes or conversation.
- **Read:**
  - The manifest, the brief, `views.md` and ADR-001 to ADR-004.
  - `as-is.md`, `questions.yaml`, `design-format.md` and the standards output.
  - To check citations: `validate_as_is.py`, `evidence_cite.py`, `validation.py` (`task_of`, `read_artifact`), `paths.py`, `vcs_git.py`, `objects.py`, `git_runner.py`, `gate_status.py`, `validate_design.py` (grep), `resources.py` (the scanners), `common.py` (Slug), phase contract lines 20–91, design skill lines 26–45, review skill lines 24–43, `review-format.md` and the phase-contract text tests (lines 225–312 and 530–555).
- **Not examined:**
  - The round 1–3 review notes.
  - The evidence files under `docs/design/workflow-efficiency/evidence/`.
  - The other skill and role sources, `MANIFEST.json`, the `.orqlet` locks, the CLI files `evidence.py` and `validate.py`, and `staleness.py`.
  - The credential rule set itself.
  - How Git behaves with configured filters, which needed a web lookup and was not done.
- **Not run:**
  - Every shell command, which ask mode blocked: HEAD and the clean tree are unconfirmed, and the quote digests are not computed.
  - No Orqlet command ran.

This review is an additional check, not a guarantee.

## Author's responses

The main session checked SEC-R4-1 against `git_runner.py:1-6` and `:34-36`, and SEC-R4-2 against `validate_design.py:224-236`; both claims hold. The design files were not changed after this round, because any edit changes the hashes the reviewers saw. The responses below are proposals that wait for the person's decision:

- SEC-R4-1, accepted. ADR-001 decisions 1 and 2 compare cited and modified files with `orqlet evidence hash`, which reads through the FileSystem port, instead of `git status --porcelain` and a working-tree `git diff`. HEAD is still recorded with `git rev-parse`. The security consideration names the residual risk of any Git command the agent runs in the person's shell.
- SEC-R4-2, accepted, as in AR4-1. Each note records the hashes the reviewer saw, `manifest.yaml` included, and the skill compares them with the files before it stops.
- SEC-R4-3, accepted. With a task, the PASS line of `gate status` reads "No action needed from gate status; the input check still confirms approval." ADR-002 decision 2, EC-3 and BC-9 follow.
- SEC-R4-4, accepted. Before relying on a reused citation, the coder compares its sha256 with the plan's recorded hash and checks its path and revision against the "Values from artifacts" character rule.
- SEC-R4-5, accepted. The next prompt names only the workflow's fixed artifact paths under `docs/design/<task>/`.
- O-1, noted for the plan: resolve HEAD once per `validate as-is` run and report the commit in `data`.
- O-2, noted for the plan: only the two pinned phrases named change in `test_workflow_phase_contract_text.py`.

## Decision after round 4

On 2026-11-23 the person chose to apply every proposed response above and to review the resulting changes themselves instead of a fifth subagent round. The changes are applied in the design files, so the hashes at the top of this note are those of the reviewed round-4 content, not of the design that goes to the pull request.
