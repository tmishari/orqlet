# Security review of the design `team-conventions-resources`

Role: security-reviewer, run as a typed subagent (`orqlet-security-reviewer`) in a clean context, three times, each time with the design set, the AS-IS file, the ledger, the stored web excerpts, the standards in `.prompts/rules.yaml` and read access to the source. The reviewer had no shell: it ran no command, timed no pattern, tested no pseudo-terminal and no Git behaviour; where a claim needs a run it said so.

## Rounds

| Round | Verdict | Blocking | Major | What the blocking or most serious findings were |
|---|---|---|---|---|
| 1 | FAIL | 1 | 11 | Internal text of login pages could reach Git history through agent-written evidence files, outside the controls that covered stored copies; profile answers fed `AGENTS.md` with weaker bounds than registry text; "control characters" undefined; skill descriptions could carry injected text; `GENERATED` files could be hand-edited past every validator; a deny-list address parser; hostile stored copies; the browser route not tied to `access: login`; the lookup rules did not cover running commands; an exponential glob matcher called non-backtracking; the check passed or skipped where a person expects a failure; the CI snippet left open shell injection |
| 2 | PASS | 0 | 7 | Invisible characters passed the allow-list; the claimed `ensure_ascii` layer did not exist; `PROTECTED` is not a merge gate; the `attach` prompt does not hold against a pseudo-terminal; the `evidence cite` guard runs after commit; permission prompts called a control without evidence; no rule against sending text out |
| 3 | PASS | 0 | 2 | No pause for the signed-in route when a session is already live; web evidence files got a weaker scan than stored copies |

The author changed the design after every round. **The changes made after round 3 have not been seen by a fresh reviewer.** The person must treat the round 3 verdict as the last independent one.

## Round 3 findings and what was done

| Id | Severity | Finding | Disposition |
|---|---|---|---|
| SR-1 | major | An already signed-in browser shows no login page, so there is no pause | Fixed as advice: the baseline asks the agent to name the registered address and ask before the first use of the route in a session, tell the developer the host of a login page, and narrow "same host" to the registered path prefix; V-7 gains a hostile-page case; the limit text says "no pause guaranteed" until V-7 is done (ADR-001 decision 3, ADR-004 decision 1, ADR-005) |
| SR-2 | major | The evidence scan is weaker than the stored-copy scan and covers `cite` only | Fixed: `cite` scans the exact bytes it hashes with `credential_problems` and the new `hidden_text_problems`; `evidence hash` is not guarded and an uncited file is unscanned, and the design says so (ADR-004 decision 4, S-18) |
| SR-3 | minor | The gate depends on labels and a flat folder walk | Fixed: a recursive walk to depth three that fails on anything but a regular `<id>.md` named by an entry; `access` and `form` are stated to be self-declared (ADR-002 decision 9) |
| SR-4 | minor | Gaps in the address grammar | Fixed in part: values are decoded twice and refused when they hold `//` or a scheme; opaque values and host labels are refused; more closed-list names; the intranet and metadata names are accepted for `login` and host review is stated as the only control; each gap is a negative vector in phase 1 |
| SR-5 | minor | The catalogue description lists ids that are attacker-chosen words; `<` and `>` pass | Fixed: the description is fixed text and a count; ids appear only in the body; `<` and `>` are refused; the hostile golden includes word-like ids and pseudo-tags |
| SR-6 | minor | Agent-written notes persist before review | Fixed in part: the onboarding step shows the exact title, note and address and waits for a yes; the command echoes what it stored; that generated files act locally from `upgrade` before review is stated (S-1) |
| SR-7 | minor | The lookup rules contradict each other in four places | Fixed: queries carry only public names and versions; the host of a login page is told to the developer; "same host" narrows to the path prefix; the catalogue points to the baseline |
| SR-8 | minor | The check's "judged by the base" holds for the profile only; and other gaps | Fixed: `--base` is always passed in CI (the default is local only); the version is written in the workflow file; a skipped branch check is an explicit line and `NOT_RUN`; the squash-title limit is stated; the snippet has a timeout; S-8 says "size bound, not control" |
| SR-9 | minor | Contract helpers echo the rejected value | Fixed: the registry validators raise fixed-text errors and a test asserts that no credential-shaped value appears in any output |
| SR-10 | minor | The hidden-text table is by name and covers only `<!--` | Fixed: numeric ranges, each with a test; reviewers read the raw diff of `docs/resources/*.md` for hidden HTML and link-reference definitions |
| SR-11 | observation | No guard for storage-state files; a sentence reads as a guarantee | Fixed: a storage-state shape rule in `credential_problems`; the sentence is reworded as advice |
| SR-12 | observation | Four phrases stronger than their mechanism | Fixed |
| SR-13 | observation | An adopter cannot relax the baseline, and learns of the lookup at `upgrade` | Fixed: the plan summary and the limit texts say so and name the opt-out (disable the client's own web tool) |

## What the reviewer verified as correct (round 3)

Quoting and front matter cannot be broken by ASCII values that pass the allow-list and are written with `json.dumps` after a fixed label; block markers are line-anchored; the Git runner's allow-list, option checks and scrubbed environment are as described and `check_ref_name` refuses the dangerous forms; the `FileSystem` port refuses links and non-regular files; the strict YAML loader refuses aliases, anchors, merge keys and duplicates and bounds size, depth and nodes; the glob matcher's cost claim and the caps hold; the added `classify` branch weakens no control for seeded files; all five roles are covered; the limits that the design states as limits (advice, no `CODEOWNERS`, the `Merge ` exemption, advisory freshness, two of eight conventions checked) are stated honestly.

## Open points left to the person

Whether the owners accept the signed-in route for internal content (S-9; the same kind of decision as the approval of Context7, U-62); whether ASCII-only text is acceptable in this release; that the lookup rules are advice and that no control of the lookup has been observed (V-6, V-7, V-8); that Git history cannot be cleaned and that Orqlet cannot see offline whether the repository is public (S-4); and that this repository has no `CODEOWNERS` file and the host refused branch protection for it (S-11).
