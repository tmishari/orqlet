# ADR-002: Plain CLI results and the gate status verdict

## Context

With a task, `gate status` always adds ORQ-I393 and a not-run reason, so its verdict is NOT_RUN and it exits 5, the failed-check code (A-27, A-28, C-4, C-7). Three skills then explain that this NOT_RUN is not a failure (C-7), and how agents treat the exit status is unknown (U-14). Approval is never checked by this command: the input check confirms it from the merge commits the person names. The task argument is not checked against the task-name rule, so a mistyped name gives three "does not exist yet" notes. `explain` prints its limits twice (A-38, A-39, C-5). `models resolve` prints ten label lines with `none` for empty values and lists rejected models (A-40), while no policy model is approved (A-47, A-48). Findings carry no next action (A-41), and ORQ-W547 names internal fields (A-43). The person asked that people never see rules or standard ids (Q-17, Q-20).

Citations A-n in this ADR name facts of `as-is.md` at 86e07abc (sha256 3fe613104a96638cd6fbae1b862092f3df563ab1fcfd71ca438b8c78ae4bfd3f), the file this design was written against. The current file, bound at 16afd3c (sha256 3526c5beefbd6ab4f4d0e36be6a4f16bdb9214664f822c8987ee765f9e32f77a), holds A-85 to A-126 and describes the code after this task, so it does not restate the older facts. A-83 and A-84 are restated there as A-106, A-111 and A-112; A-27, the always-NOT_RUN verdict, now reads as A-110.

## Decision

1. `gate status` reports PASS and exits 0 when no artifact is stale, no error was found and no other check was skipped. ORQ-I393 stays as an info finding, worded as "approval is checked by the input check, not by this command". Stale input, a missing revision or an expected-change deviation keep NOT_RUN or FAIL and exit 5. A task name that breaks the existing task-name rule (lowercase words joined by hyphens) is a usage error with exit 2, raised in the CLI layer against the `Slug` contract, as `models resolve` does for `--task`.
2. The human text of `gate status` and of every validator ends with exactly one action line, rendered in the interface layer from the verdict and the finding counts, with no mapping per finding code. The first matching line applies:
   - FAIL: "Action needed: fix the N error(s) above, then run the command again."
   - NOT_RUN: "Action needed: resolve the not-run reason(s) above and run the command again, or have the person confirm them." A cause the person confirms under the stale-input matrix needs no rerun.
   - `gate status` with `--phase` and open manual expected changes: "Action needed: N expected change(s) need a reviewer's comparison."
   - `gate status` with no artifact of the task: "No artifact of task T exists yet; check the task name unless you are starting research."
   - PASS of `gate status` with a task: "No action needed from gate status; the input check still confirms approval."
   - Any other PASS: "No action needed."
   On PASS with warnings, "Read the N warning(s) above." follows.
   `evidence cite` and `evidence hash` render without an action line.
3. `models resolve` opens with one sentence: the suggested profile, whether a model is suggested and that nothing changes. It then prints only the fields that hold a value. Rejected models stay in `--json`.
4. `explain` lists its limits once and shows standards as counts per source; rule ids and levels stay in `--json`. `standards for` keeps ids, levels and rule text, because it is the agent's input for applying the rules, while `explain` is read by people.
5. ORQ-W547 says in plain words what the upgrade changes and that the person decides what to do with open designs and plans.
6. The fields of the JSON envelope and the exit codes of other commands do not change; finding messages change in both outputs.

## Consequences

- An agent no longer meets a "not run" that it must ignore, and three skill sentences go. From the second implement phase on, the task's own earlier commits still give ORQ-W390 and NOT_RUN, which the person confirms under the planned-work row once per phase (A-83, A-84, ADR-001 decision 4).
- A script that read exit 5 from `gate status` as "offline, fine" now sees 0; a script that treated 5 as failure stops seeing false failures. A script passing an invalid task name now gets exit 2. A well-formed task name with no artifact moves from exit 5 to exit 0 with the "No artifact of task T exists yet" line; the input check still stops on ORQ-I394.
- A PASS from `gate status` could be misread as approval; its action line, the info finding and the skills' input check, which still requires the merge commits, guard against that.
- The action line is generic; specific guidance stays in each finding's message.
- Diagnostics stay complete in `--json`; the human text is shorter.
- The architecture proposal describes the offline approval result of `gate status` as NOT_RUN; its passages on that result are updated in the final implementation commit.

## Rejected alternatives

- Keep NOT_RUN and exit 5 and explain it in every skill: today's cost, kept.
- A new exit code for NOT_RUN: it would merge "offline approval" with "stale input", which must stop the work.
- A `next_action` field in the JSON envelope: a contract and schema change that agents reading the human text do not need.
- A next step per finding code: about 256 codes to maintain (U-10) for little gain over the messages they already carry.
- Hide finding codes as well: the person limited the request to rules and standard ids (Q-20).
