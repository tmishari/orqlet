# Architecture review of the design, round 5

Reviewer: `orqlet-arch-reviewer`, a typed subagent with its own context, started 2026-11-20T13:03:58Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md` and the output of `orqlet standards for` for the scope. It was also allowed read-only access to source files and `.prompts/rules.yaml`, to verify design citations.

## Hashes when the reviewer started and when the note was saved (`orqlet evidence hash`)

The hashes at start (2026-11-20T13:03:58Z) and at save (2026-11-20T13:05:50Z) are identical: no design file changed while the reviewer ran.

| File | sha256 |
|---|---|
| design/manifest.yaml | 7c9bbf3c19658ca96da1e40757735eb9076d876419b54981cb1366ef37454f33 |
| design/component.md | 100dfcc355c2800d43ac9cdea48e10e4b507189060d923d795e6f842691f6580 |
| design/context.md | bc073e7aa91f01c3467cf882b7e378dcf1b72c20b8212bb7cdd30be06f2aa789 |
| design/container.md | dd4b08ff820c64761461c347bef18382985ddc915cd26b9ebf6301c98e3526aa |
| design/data-flow.md | 12ca6e59332491343e8617b1511306eb81ccc6aeb802ab0c3791cba6680731bb |
| design/sequence.md | d820e0307a235331b5f57bd385e5bba94a84885d47ba3f36a23ba2043211e114 |
| design/adr-001 | 435abc5ad294cc019f47484a26d072d4b697208cc49c9e112586d68e1416e57c |
| design/adr-002 | bb567b432e242be34707c98ed7c29f136ba5fda51cdc48fba062d668c7d6eea4 |
| design/adr-003 | f763bb0985455103f43a8392e4fdd7e7212bb94b92814f6564dcc98be91d4144 |
| design/adr-004 | 413bd5ce4aa5eb690712b5b0dbe003e230dd95bbd453c5e5a4fa2050710f9ed1 |
| design/adr-005 | da4e25e94fd38b2b1df3607b02b42ffc24b8ed50117a200938abe4d9da9b7df4 |
| design/adr-006 | df9075e7085073a91307a0e22706c301e7d4534df2372e049450f14d5da93427 |
| design/adr-007 | aff768709d7b902eb25f95dc53b6a4e42713b409f4ce0ca03587cedbb2fb90dd |
| questions.yaml | 46fa60dd778fba34d92148f60569bec8caba5edc056380f0d686802357d4d688 |

The design files changed after this note to answer the findings (see "Author's responses"). The reviewed content is therefore not what will merge, and round 6 reviews the revised files.

## Reviewer output (unchanged)

**Verdict: changes required.** I found 1 blocking and 3 non-blocking findings. The round-4 contradiction is resolved: ADR-002 decision 4, the failures row for an interrupted apply, BC-30, BC-31, BC-37 and Q-40 now agree. A superseded change can be rolled back only before the recovering install applies, and rollback of a change that wrote no manifest leaves `user/manifest.json` unchanged. That matches how `_reversals` skips entries that are not done (`rollback.py:125-126`). The amended texts of ORQLET-SAFE-001 and ORQLET-ARCH-003 are stated exactly and are applied consistently. The design also conforms to design-format for D3: the brief has its nine parts in order, every ADR has Context, Decision, Consequences and Rejected alternatives, and it has a context view, the reviewer notes and no phase order. Every ledger question from Q-1 to Q-41 is answered. The one blocking finding is that the dry-run guarantee contradicts the order in which ADR-002 creates and tightens folders.

Things I could not check:
- I did not recompute the artifact hashes in the manifest, because the read-only shell refused to run any command.
- I did not render the Mermaid diagrams.
- I did not read the evidence files under `evidence/web/`, which were outside my allowed inputs.
- I did not read the review notes from rounds 1 to 4, also outside my allowed inputs.
- I checked AS-IS entries only where I needed them (A-27, A-28, A-29, A-30, A-31).

I verified these code citations against source:
- `pyproject.toml:105-127`
- `.prompts/rules.yaml:66-72`
- `local_fs.py:74-77`
- `wiring.py:145-149`
- `ancestors.py:8-11`
- `common.py:27-28`
- `apply_plan.py:39-93`
- `instruction_adapter.py:94-139`

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 5, role: architecture-reviewer}
verdict: changes-required
findings:
  - id: F-1
    blocking: true
    rule: ORQLET-SAFE-001 (as amended); design-format "The design brief" (behaviour and acceptance criteria must be consistent and testable)
    statement: >-
      The design contradicts itself on writes before consent. ADR-002 decision 1a
      (adr-002...md:50) says "The user-scope adapter creates a missing root with mode 0700 before
      the plan is made", and in the same bullet that "The preview lists every root it will create".
      A root that exists before the plan cannot also be a root the preview "will create". Decision
      1a (adr-002...md:51) also tightens existing `user/`, `journal` and `backups` folders to 0700
      and "the preview reports it", which means it happens before the preview. ADR-006
      (adr-006...md:44,51) runs `uv tool list` under `--dry-run`, and its working folder is
      `user/tools-work/`, "created 0700 by the tools adapter". Against these,
      component.md:56 (section 3 item 6) and BC-7 (component.md:230) say that `--dry-run`
      "writes nothing, in the user scope, a project or the data directory". The interactive path
      has the same problem: a person who declines the preview still gets folders created. The
      contradiction is structural. The composite file system wraps one `LocalFileSystem` per root
      (container.md:79), and `LocalFileSystem.__init__` calls `root.resolve(strict=True)`
      (local_fs.py:74), so a root must exist before a plan can be read through it. On a fresh
      machine (no `~/.agents` or `~/.copilot`), BC-7 and decision 1a cannot both hold, and a
      dry-run test has no single correct expectation.
    required_change: >-
      State one rule in ADR-002 decision 1a, section 3 item 6, BC-7 and BC-29. For example: during
      planning (dry-run, preview, or a declined prompt), a missing root, a missing `user/` folder
      or a missing `tools-work/` folder is treated as empty and reported as "will create"; folder
      creation and the 0700 tightening happen only after consent, before the first journalled
      write. Also state which working folder `uv tool list` uses under `--dry-run` when
      `tools-work/` does not exist. Add or extend an acceptance criterion: a dry-run, and a
      declined interactive preview, on a home with missing roots and a data directory with 0755
      folders, leave every path and mode unchanged.
  - id: F-2
    blocking: false
    rule: ORQLET-SAFE-001 (as amended) — "the manifest is written last so a re-run converges"
    statement: >-
      Adoption of an interrupted change's done writes is defined only for `install`
      (adr-002...md:69-71; component.md:57 item 8; failures row component.md:203). `uninstall`
      also goes through `apply_plan`, which marks every open change superseded
      (apply_plan.py:55-56), and a successful `uninstall` "prunes older and superseded ones"
      (adr-002...md:74; Q-40). The design does not say what `uninstall` does with files that an
      interrupted install wrote but never recorded in `user/manifest.json`. As written, `uninstall`
      keeps them as unrecorded (BC-8) and then prunes the journal that could identify them or roll
      them back. The next `install` then meets "an unowned file holds the target name" on Orqlet's
      own files (component.md:193) and exits 3 instead of converging. Recovery by hand exists, so
      this does not make the design wrong. It is a gap in the recovery contract that round 4
      reworked.
    required_change: >-
      State in ADR-002 decision 4 or 5 how `uninstall` treats a pending superseded change. Either
      it adopts that change's done writes under the same rule as `install` and then removes them
      when no owner remains, or it does not prune a superseded change it has not adopted. Name the
      superseded id in the uninstall preview, and add an acceptance criterion for the sequence:
      interrupted install, then uninstall, then install, ending with exit 0.
  - id: F-3
    blocking: false
    rule: ORQLET-SAFE-001 (as amended); ADR-002 decision 3
    statement: >-
      ADR-002 (adr-002...md:70) says the superseded change's Orqlet entries in a shared JSON file
      "are adopted the same way", which reads as: only when the whole file's current SHA-256 equals
      the journal's after-hash. The journal records hashes per file, not per entry
      (apply_plan.py:111-119 `_entry`), and ownership of entries uses a canonical-JSON hash per
      entry (adr-002...md:62). A client or another tool that touches an unrelated key of
      `settings.json` or `hooks.json` between the interruption and the recovery defeats adoption.
      The recovering run then treats Orqlet's own entry as "an entry equal to Orqlet's command but
      without a manifest record" and reports a conflict with exit 3 (adr-002...md:63;
      component.md:195). The plan can settle this within decision 3, but the basis for entry-level
      adoption is not stated.
    required_change: >-
      State that entry adoption compares each entry's canonical-JSON hash with the entry that the
      superseded change rendered, and say where that hash comes from: recorded in the user journal
      record, or recomputed from the render of the recorded workflow version. Extend BC-30 with an
      unrelated key edited in `settings.json` between the interruption and the recovery.
  - id: F-4
    blocking: false
    rule: design-format "What each class requires" (consistent views); ORQLET-ARCH-002
    statement: >-
      The component diagram routes the status use case, and through it the hook use case, to P2
      "FileSystem: composite user scope" (component.md:117,145). The composite exposes only the
      allow-listed client roots and `data/` (adr-002...md:28-35). Status, however, reads a
      project's `.orqlet/` locks (component.md:162), and ADR-004 decision 5 (adr-004...md:62)
      reads through "a FileSystem port rooted at the injected UserHome", which is a different
      instance from the composite. The session-time data flow also feeds `user/manifest.json` into
      the status use case in hook mode (data-flow.md:33). A file system rooted at home cannot reach
      that file when `ORQLET_DATA_DIR` lies outside home, which ADR-002 decision 1a allows. The
      ports themselves are right; the views do not say which file system instance serves each read.
    required_change: >-
      Show in component.md section 4, and in the container view, the read-only file system
      instances that status and hook use: a home-rooted reader for the hook's upward search, a
      project-rooted reader for full status, and a data-directory reader for the user manifest.
      State the `global` result in hook mode when the data directory lies outside home.
```

## Author's responses

Every finding is accepted. Round 6 checks the changes.

| Finding | Response |
|---|---|
| F-1 | ADR-002 decision 1a now has one rule: nothing is created or changed before consent. While planning (dry-run, preview or a declined prompt), a missing root, `user/` or `tools-work/` reads as empty and shows as `will create`, and wide modes show as `will tighten`. After consent and before the first journalled write, the adapter creates the missing roots and their parents with mode 0700, validates them again and opens their `LocalFileSystem`. Under `--dry-run`, `uv tool list` runs only when `tools-work/` already exists; otherwise Graphify shows `not checked` (ADR-006). The amendment text says the same. Section 3 item 6, BC-7 (a fresh home and 0755 folders, under both dry-run and a declined preview) and BC-29 match. |
| F-2 | ADR-002 decision 4: before it plans, `uninstall` applies the same adoption to a pending superseded change, removes the adopted entries once no owner remains, and names the superseded id in its preview. BC-44 tests an interrupted install, then uninstall, then install, ending with exit 0. |
| F-3 | ADR-002 decision 4: a shared JSON file is adopted per entry. When the superseded journal records the file as done, each Orqlet entry whose canonical-JSON hash equals the entry of the current render is adopted, even if another key changed since. An entry that differs, for example after a workflow version change, stays a conflict. BC-30 now covers an unrelated key edited between the interruption and the recovery. |
| F-4 | component.md section 4 adds a separate port node, "FileSystem readers: home, project, data dir", used by the status use case, and an interface note. The note names the three read-only instances and says the data-directory reader also covers an `ORQLET_DATA_DIR` outside home, so `global` is reported in both modes. container.md states the same. |
