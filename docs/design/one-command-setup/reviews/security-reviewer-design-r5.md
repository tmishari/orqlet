# Security review of the design, round 5

Reviewer: `orqlet-security-reviewer`, a typed subagent with its own context, started 2026-11-20T13:03:58Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md` and the output of `orqlet standards for` for the scope. It was also allowed read-only access to source files and `.prompts/rules.yaml`, to verify design citations.

## Hashes when the reviewer started and when the note was saved (`orqlet evidence hash`)

The hashes at start (2026-11-20T13:03:58Z) and at save (2026-11-20T13:05:50Z) are identical: no design file changed while the reviewer ran. They are the hashes listed in `architecture-reviewer-design-r5.md` of the same round:

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

The design files changed after this note (see "Author's responses"), and round 6 reviews the revised files.

## Reviewer output (unchanged)

**Verdict: approve.** 0 blocking and 6 non-blocking findings. TB-1 to TB-3 each have a stated control, and every round-4 point is now in the design. Those points are: the "owned by the user on POSIX" wording with the Windows/Q-41 exception, the adapter-declared allow-list, absolute paths for uv and pipx, the accepted launch-PATH risk, URLs reduced to scheme and host, adoption with the rollback window, and the hook's home-rooted reads. Every code and rule citation I checked matches the source: `local_fs.py:74-77`, `apply_plan.py:39-93`, `.prompts/rules.yaml:66-72`. `LocalFileSystem.write_atomic` keeps an existing file's mode (`local_fs.py:113-124`), so a credential-bearing `settings.json` is not widened when it is rewritten. SEC-001, SEC-002 and SEC-003 are kept. Q-39, Q-40 and Q-41 record the residual risks the person accepted. What remains are a few gaps that the plan or the separate SAFE-001 standards change can close.

Not examined:
- The stored evidence pages (`evidence/web/*.md`), so the client contracts and the K-12 citations are unverified.
- The earlier review notes.
- `container.md` only against its rules list.
- `pyproject.toml:105-127` and `ancestors.py:8-11`; I did not open either.
- Any runtime behaviour, because no code exists yet.

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 5, role: security-reviewer}
verdict: approve
findings:
  - id: F-1
    blocking: false
    rule: ORQLET-SAFE-001 (proposed amendment text)
    statement: >-
      The amendment text (adr-002:91) says user-scope writes "stay inside the allow-listed client
      folders and the data directory's user folder, each limited to its listed sub-paths". It then
      exempts some writes only "from the journal". Read literally, the confinement sentence still
      covers those exempt writes. First, tool preparation writes to the tools' own installation
      folders, which are outside every allow-listed root. Second, the apply lock, journal, backups
      and tools-work sit under user/ but are not among the data/ root's declared sub-paths
      (adr-002:35, only manifest.json and cursor-user-rules.md). Third, creating a missing data
      directory above user/, or missing parents of a CODEX_HOME or COPILOT_HOME under home, is
      exempted by neither sentence. A reviewer applying the rule word for word could find the
      design non-compliant, or read the exemption more widely than intended.
    required_change: >-
      In the K-1 standards change, say which exemptions also lift the sub-path limit. Either
      declare user/apply.lock, user/journal/, user/backups/ and user/tools-work/ as data-directory
      sub-paths, or state that the listed exempt writes are excepted from both the journal and the
      sub-path limit. State that tool preparation writes are made by the external tools, outside
      Orqlet's write roots. Either cover or forbid creating missing parent folders of a root.
  - id: F-2
    blocking: false
    rule: TB-1 / ADR-002 decision 1a
    statement: >-
      adr-002:50 says the adapter "creates a missing root with mode 0700 before the plan is made".
      In the same line the preview "lists every root it will create". component.md section 3
      item 6 and BC-7 say --dry-run writes nothing. If roots are created before the plan, they are
      written before the person consents and during a dry run. A root created for a run the person
      declines then stays behind as a client folder, and the detection rules of component.md
      section 3 item 1 count such a folder as an indicator.
    required_change: >-
      State that missing roots are created only at apply time, after the person's yes or --yes,
      and never under --dry-run, followed by a fresh root validation. Add a criterion that a
      declined or dry-run install creates no root.
  - id: F-3
    blocking: false
    rule: ORQLET-SEC-001 / TB-2
    statement: >-
      adr-006:48 locates uv on the pipx route from the output of `pipx environment --value
      PIPX_BIN_DIR`, and "uv is then called by its full path". The absolute-path rule of adr-006:54
      covers only resolution through PATH elements. Nothing says this tool-supplied value must be
      an absolute path, free of control characters, or point to an existing executable, before it
      becomes argv[0] of a ProcessRunner call.
    required_change: >-
      Give the PIPX_BIN_DIR route the same check as the PATH route. The value must be one line, an
      absolute path with no control characters, and the uv found there must exist and be a file.
      Otherwise install reports a host step and starts no process. Add this case to BC-10.
  - id: F-4
    blocking: false
    rule: TB-1 / ADR-002 decisions 2, 4 and 5
    statement: >-
      Manifest records and journal entries are keyed by prefix (adr-002:37, 55), and each prefix
      resolves to a root from the current CODEX_HOME or COPILOT_HOME. Nothing records which real
      root a prefix meant when the change was written. If the variable changes between install and
      uninstall or rollback --user, the undo acts on a different folder. The hash checks limit
      deletions, but a matching file there could be replaced from a backup taken in the old root.
      Such a backup may hold that root's credential-bearing AGENTS.md or hooks.json.
    required_change: >-
      Record each prefix's resolved real root in the journal and in user/manifest.json. Have
      uninstall, rollback --user and the adoption step refuse with exit 3, naming the variable,
      when the current resolved root differs.
  - id: F-5
    blocking: false
    rule: ORQLET-SEC-002 / TB-3 (content reaching agent context)
    statement: >-
      The entry skill makes the agent run `orqlet install --dry-run` and `--yes`, and show their
      output (adr-001:22). Install output includes tool output summaries from uv and pipx, whose
      text can come from the package index (TB-2). ADR-004 decision 1a and ADR-001 decision 3
      bound what reaches context through the hooks and status. ADR-007 decision 8 makes terminal
      output inert. The design does not say whether the entry skill reads human or --json install
      output, or how tool output entering the agent's context is bounded and labelled as data.
    required_change: >-
      State in ADR-001 or ADR-006 that the entry skill reads install --json. State that the tool
      output summary there is capped, stripped of control characters and redacted as in human
      output, and placed in a field marked as tool output. State that the skill shows that field
      to the person and never acts on its text.
  - id: F-6
    blocking: false
    rule: ORQLET-SEC-002 / ADR-002 decision 3
    statement: >-
      Shared client JSON files and hook payloads are read with "a strict JSON parser" using the
      standard-library json module (adr-002:60-61, adr-004:70). json.loads by default accepts
      duplicate keys, keeping the last, and accepts NaN and Infinity. A settings.json with a
      duplicate key would parse, and the rewrite would silently drop one value that the person or
      another tool set. The design does not define "strict".
    required_change: >-
      Define strict for shared files and payloads. Reject duplicate keys, through object_pairs_hook,
      and NaN or Infinity, through parse_constant, and require an object at the top level. For a
      shared file, such input is a conflict and the file is never rewritten. Add a duplicate-key
      settings.json case to BC-6.
```

## Author's responses

Every finding is accepted. Round 6 checks the changes.

| Finding | Response |
|---|---|
| F-1 | The amendment text now makes the listed writes exempt from both the journal and the sub-path limit. Those writes are: after consent, creating a missing root with its missing parents under home or under the data directory, and the `user` folder; tightening to 0700 after consent; the apply lock, the journal, the backups and their pruning under `user`; and the tools scratch folder. The text also says that tool preparation writes are made by the external tools in their own installation folders, outside Orqlet's write roots. |
| F-2 | ADR-002 decision 1a: nothing is created or changed before consent. Missing roots are created only after the person's yes or `--yes`, are validated again, and never under `--dry-run`. BC-7 covers a dry-run and a declined preview on a fresh home. |
| F-3 | ADR-006: the `PIPX_BIN_DIR` value is checked before use. It must be one line, an absolute path with no control characters, and the `uv` there must exist and be a regular file. Otherwise `install` reports a `host step` and starts no process. BC-10 covers this. |
| F-4 | ADR-002 decision 1a, "Roots are pinned": the journal and `user/manifest.json` record each prefix's resolved real root. `uninstall`, `rollback --user` and adoption refuse with exit 3, naming the variable, when it differs. BC-6 and EC-4 cover this. |
| F-5 | ADR-001 and ADR-006: the entry skill reads `install --json`. The tool output summary sits in a `tool_output` field, capped, stripped and redacted as in human output, and the skill shows it as data and never acts on it. BC-45 covers this. |
| F-6 | ADR-002 decision 3 defines strict parsing: an object at the top level, duplicate keys rejected through `object_pairs_hook`, and `NaN` and `Infinity` rejected through `parse_constant`. A shared file that fails this is a conflict and is never rewritten, and hook payloads use the same parser. BC-6 includes these cases. |
