# Considerations

This note is the text behind the `considerations` block of the manifest. It also covers the three considerations that design §17.4 (v0.5) adds and that the built `orqlet.design-set/v1` has no field for: constraints, failure behaviour, and validation and rollback.

## Security (state: affected)

- The front-matter functions and the test handle text that Orqlet's own renderers produce inside the test process. No untrusted repository file is newly read at run time, and `doctor` is not changed (ADR-001). The two domain functions never raise on any input, and they start no process, use no network and handle no secret. Messages name keys and never print values, following the convention of `src/orqlet/application/contracts/loading.py:16-17`.
- The unquoted form applies only to workflow-owned text of skills, agents and commands, through an allow-list: ASCII only, a letter first, no YAML-significant character, no reserved word. Rule files, which carry project text from standards packs (`src/orqlet/application/usecases/render_request.py:143-144`), keep the quoting and the escaping of `src/orqlet/adapters/render/emit.py:20-21` exactly as today. That choice came from the security review of round 2: a deny-list predicate over project text could let a line separator or a type-changing string through.
- The comparison covers every key, including `tools`, `readonly` and `disable-model-invocation`, which carry the read-only and no-auto-invocation controls (`src/orqlet/adapters/render/roles.py:26,36`, `src/orqlet/adapters/render/skills.py:48`). An emitter change cannot leave one of those keys read differently in a skill, agent or command without a test failing. The controls of Codex roles (TOML) and of the Codex sidecar are not front matter and stay pinned by the string assertions in `tests/unit/render/test_skills.py`.
- The packet rule (ADR-002) strengthens reviewer independence by a deterministic floor for valid review records, in the lists and in the diff, and refuses a malformed record at a record path. It is not a guarantee: the limits are listed in ADR-002 (a verdict inside any other file, a path that is not an exact match, reads outside the packet, and the built `review prepare` until the v0.5 plan).
- Digests stay SHA-256 (ORQLET-SEC-003). The SHA-1 fingerprint, the bypass flags and the key printing of Harness² are rejected (ADR-005).
- Residual: the line view models one class of reader. Claude Code and Codex may read the files differently, and Cursor's reading of skills and commands is unobserved (AS-IS U-9). Whether unquoting `model` fixes the subagent model fallback (AS-IS O-12) is not observed either.
- Trust boundary: none is added; the reasons are in `data-flow.md`. `security_globs` stays empty: this design does not touch the packet builder's code, which the v0.5 plan designs and classifies with its own globs.

## Compatibility (state: affected)

- Rendered bytes: 32 skill, agent and command Markdown files in the golden set change (quotes removed where plain-safe), and six more goldens change because their markers carry the workflow version (`AGENTS.md` for the three clients and three PR-template files). Rule files do not change. The golden files of the three clients are regenerated on purpose, once (ORQLET-DET-001), and the two tests that pin the quoted forms of a skill and a role (`tests/unit/render/test_skills.py:272-273,319`) are rewritten.
- Workflow package: the `description` of `orqlet-research` changes, so `MANIFEST.json` is rebuilt and the version is bumped (ORQLET-DET-002), because `doctor` reports an error when a digest changes at an unchanged version (ORQ-E161, `src/orqlet/application/usecases/diagnose.py:231-238`). `src/orqlet/workflow/releases.json` records only 0.1.0 while `identity.json` says 0.3.0, so 0.3.0 is not a recorded release and no adopter is known to run it; the plan chooses the number (a patch of 0.3.x under design §20.8, or the next minor release) and writes `releases.json` only at release.
- Adopters: after `orqlet upgrade`, the protected-set digest differs (`src/orqlet/application/usecases/gate_status.py:70-77`). Artifacts whose header carries the old workflow version or digest are reported stale (warning ORQ-W390 and a not-run reason that the artifact was written against other inputs; `gate_status.py:179-185,194-202`). I searched `src` for a refresh or re-bind step (`rebind`, `re-bind`, `refresh`, `re-approve`, `restamp`) and found none, so the plan must state how a person refreshes a stale artifact. This is the effect that every workflow release has; it is not new, and it is not painless.
- This repository uses Orqlet on itself. The plan puts the in-repo `orqlet upgrade` last, because it regenerates the skills, agents, `AGENTS.md`, the PR template and the lock files (their markers carry the workflow version), and it makes this task's own AS-IS, design and plan stale from then on. The plan states what is done about that.
- No contract schema, public command or finding code changes. `doctor` and `sync` behave as before. EC-3 changes the signature of `front_matter` by a defaulted keyword.
- The packet rule needs the v0.5 packet; until then the built `review prepare` exports the staged tree with no assertion.

## Operations (state: affected)

- The new tests render the workflow for three clients and parse 32 small blocks; no network. They join the existing suite (1,504 passed on Python 3.12 to 3.15 at the last run, before this design; I did not measure the added time).
- After an upgrade a client needs a new session to reload files (design §20.9); nothing new is needed.
- Rollback: the change adds no persisted state. Revert the commit for the code and text; an adopter rolls the generated files back with `orqlet upgrade` and its journal. Approvals refer to files in Git, but their headers' bound values go stale after an upgrade (see Compatibility).

## Constraints

- In scope: the keyword parameter and predicate in the emitter, the two domain functions, the release test, one description edit, the golden files, the generated files of this repository, and the proposal text for ADR-002 and ADR-004.
- Out of scope: any code from Harness², any command or configuration that runs it, the packet code (the v0.5 plan), a `doctor` check, a check of rule files, Codex TOML roles and the Codex sidecar, and the evaluation harness itself (M7).
- Orqlet starts no agent and calls no model (R-01). Domain code stays free of I/O and third-party imports (ORQLET-ARCH-002); the PyYAML oracle is used in a test only. The change works on macOS, Linux and Windows because it handles text only. No new dependency.
- Standards that apply: ORQLET-ARCH-001, -002 and -003, DET-001 and DET-002, NOMODEL-001, QA-001, SEC-003, TEST-001 and STYLE-001. Not applicable: SAFE-001 and TEST-002 (no new writer), DET-003 (no contract change), SEC-001 (no process), SEC-002 (no untrusted file newly read).

## Failure behaviour

- A rendered skill, agent or command with no front-matter block, with a block that does not parse, or with a value that is not a one-line scalar fails the test and names the file.
- A string that is not plain-safe stays quoted, and the test fails when the quote changes what a line reader sees; the fix is to reword the source text.
- `simple_front_matter` and `front_matter_differences` never raise: arbitrary text gives a view or a difference.
- A packet with a malformed record at a record path yields `NOT_RUN` naming the path and writes nothing (ADR-002, later).

## Validation and rollback

- Validation: unit tests for `simple_front_matter` (plain, quoted, single-quoted, folded, empty value, missing space, CRLF, very long input, binary-like text) and for `front_matter_differences` (equal, quote difference, key in one view, list or mapping value, boolean and integer forms); a property test that neither function raises on arbitrary text; unit tests for the predicate (each excluded character class, non-ASCII, line separators, a digit first, reserved words in any case) and a test that every accepted string reads as the same string in the strict loader and in PyYAML's default safe loader, using the awkward strings of `tests/unit/render/test_emit.py` and a property test; the release test over the three clients; golden files regenerated with `--update-golden` only on purpose. A real-client observation of skills, commands and the other clients is the evidence for client behaviour and is not claimed before it is run (proposal spike S-21, IDE load).
- Rollback: see Operations.
