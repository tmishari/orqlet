# Security review of the design, round 4

Reviewer: `orqlet-security-reviewer`, a typed subagent with its own context, started 2026-11-20T13:00:04Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md` and the output of `orqlet standards for` for the scope. It was also allowed read-only access to source files and `.prompts/rules.yaml`, to verify design citations.

## Hashes when the reviewer started and when the note was saved (`orqlet evidence hash`)

The hashes at start (2026-11-20T13:00:04Z) and at save (2026-11-20T13:02:29Z) are identical: no design file changed while the reviewer ran. They are the hashes listed in `architecture-reviewer-design-r4.md` of the same round:

| File | sha256 |
|---|---|
| design/manifest.yaml | fc2a2d02f9c32b53723144c6ec18f428f77f6dd32a9c8203c63b2ba26e92576c |
| design/component.md | 0355ebce0a072ef32242fb281050e30e6daa19efb6bb88cd38b5c70bb2d3b86b |
| design/context.md | bc073e7aa91f01c3467cf882b7e378dcf1b72c20b8212bb7cdd30be06f2aa789 |
| design/container.md | a436c0a5c5c34989b476680d8962b949d3e0c41eedad5e23d926a506b1158f87 |
| design/data-flow.md | 12ca6e59332491343e8617b1511306eb81ccc6aeb802ab0c3791cba6680731bb |
| design/sequence.md | d820e0307a235331b5f57bd385e5bba94a84885d47ba3f36a23ba2043211e114 |
| design/adr-001 | 435abc5ad294cc019f47484a26d072d4b697208cc49c9e112586d68e1416e57c |
| design/adr-002 | d65fa9997c300022bf16df390ca2392e5c78db6dead580c35af7d3151fb9b1d2 |
| design/adr-003 | f763bb0985455103f43a8392e4fdd7e7212bb94b92814f6564dcc98be91d4144 |
| design/adr-004 | 87e015fe06a37f291fb50981c6b9d65619732448b7a285c786a9bd972ec9c453 |
| design/adr-005 | da4e25e94fd38b2b1df3607b02b42ffc24b8ed50117a200938abe4d9da9b7df4 |
| design/adr-006 | 5dd92b0ac6caf184acca108ea272501d2ea7f1a008053d61234b1bb8236b834d |
| design/adr-007 | aff768709d7b902eb25f95dc53b6a4e42713b409f4ce0ca03587cedbb2fb90dd |
| questions.yaml | 46fa60dd778fba34d92148f60569bec8caba5edc056380f0d686802357d4d688 |

The design files changed after this note (see "Author's responses"), and round 5 reviews the revised files.

## Reviewer output (unchanged)

**Verdict: changes required.** I found 1 blocking and 7 non-blocking findings. The blocking one is in the proposed SAFE-001 text that merges first as a MUST rule: it says every root must be "owned by the user", with no platform condition. The design checks ownership only on POSIX, and Q-41 allows a Windows data directory whose access is not checked, so on Windows the design breaks its own rule.

Every round-3 point I could check is answered. Status paths are now null with `path-not-representable`. A relative PATH element now withholds hook registration. The index report is scheme and host only, and no package config file is read. Retention is the last 3 changes, and status reads locks through the bounded reader. The Q-39 residual risk, SHA-256-only digests, strict YAML through the FileSystem port, hooks that start no process, and the fixed-template context are all in place.

What I did not check:
- The full AS-IS file. I read only the parts the design cites.
- The evidence pages (`client-integration-contracts.md`, `global-setup.md`), which are outside the allowed inputs.
- How Windows `CreateProcess` and the pinned uv and pipx versions search for programs and configuration. I did not look this up on the web.
- The citations at `pyproject.toml:105-127` and `common.py:27-28`.

I did open these files to verify citations: `local_fs.py`, `apply_plan.py`, `wiring.py:130-161`, `rules.yaml:66-72`, `ancestors.py`, `environment.py`, `subprocess_runner.py`, and line 50 of `git_runner.py`.

This review is an additional check, not a guarantee.

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 4, role: security-reviewer}
verdict: changes-required
findings:
  - id: F-1
    blocking: true
    rule: ORQLET-SAFE-001 (proposed amendment text, Q-32, K-1); TB-1 root validation
    statement: >-
      The exact amendment text (adr-002-user-scope-root-journal-and-manifest.md:88) lists
      the root checks with no condition: "under the real home (the data directory may be
      elsewhere), not a link, owned by the user, and not inside a Git work tree". The design
      that is meant to meet this text checks ownership only "(on POSIX)" (adr-002:48). Q-41
      (questions.yaml:800-818, adr-002:46) also allows a Windows data directory outside home
      whose access is not checked. So on Windows no root's owner is checked, and an
      implementation that follows the design breaks the MUST rule it adds. A reviewer
      applying the merged rule would either fail every Windows path or learn to ignore the
      clause. That makes the control unreliable on the platform where it is weakest.
    required_change: >-
      Make the amendment text and decision 1a agree. Either qualify the clause, for example
      "owned by the user (on POSIX)", and name the Windows exception allowed by Q-41, or
      specify a Windows owner check in decision 1a with a matching acceptance criterion.
      State the chosen wording exactly in ADR-002, because it merges first under K-1.
  - id: F-2
    blocking: false
    rule: ORQLET-SAFE-001 (proposed amendment, exemptions); ORQLET-SEC-001
    statement: >-
      The last exemption, "writes made by external tools that Orqlet starts through the
      ProcessRunner port" (adr-002:88), has no limit on which process, which arguments or
      where it writes, and it covers project scope too. Today the only writing tools are the
      fixed vectors of ADR-006 decision 4 (adr-006:44-49). But SEC-001 only requires the
      port, so any later change could start a process that writes anywhere and still satisfy
      SAFE-001. The design controls the current use; the rule text does not.
    required_change: >-
      Narrow the exemption, for example to "tool preparation by orqlet install through fixed
      argument vectors, whose writes go to the tool's own installation folders". Or state
      why a general exemption is wanted and leave that choice to the person.
  - id: F-3
    blocking: false
    rule: ORQLET-SAFE-001 (proposed amendment); TB-1 path confinement
    statement: >-
      The amendment confines writes to "the allow-listed client folders ... each limited to
      its listed sub-paths" (adr-002:88), but says the table that lists them "is not part of
      the rule" (adr-002:90). The rule never says where the allow-list lives or how it may
      grow. A later change that widens the table (a new root or a broader sub-path) cannot be
      judged against the rule's text.
    required_change: >-
      Name the source of the allow-list in the rule, or in a sentence the plan must keep.
      For example: the roots and sub-paths are those of the user-scope adapter, and adding
      one requires a reviewed design.
  - id: F-4
    blocking: false
    rule: ORQLET-SEC-001; TB-2
    statement: >-
      ADR-004 decision 7 (adr-004:77) treats looking up a bare command name through the
      current directory, or through relative PATH elements, as a way to hijack the
      executable. ADR-006 decision 4 (adr-006:44-49) starts bare `uv` and `pipx`, including
      `uv tool list` under --dry-run, and says nothing about how they are resolved. The
      person may run `orqlet install` inside an untrusted clone, and the existing runner
      passes the bare argv to Popen (subprocess_runner.py:34-43). On POSIX the child's
      working folder is the private tools-work folder, which limits the risk. On Windows the
      default program search may include the parent's current directory; I could not verify
      this here. The existing bare `git` (git_runner.py:50) is outside this change.
    required_change: >-
      Resolve `uv` and `pipx` to absolute paths through the ExecutableLocator, using only
      absolute PATH elements, before any ProcessRunner call. Report a host step when they
      cannot be resolved, and add a test that a relative or empty PATH element is never
      used for them.
  - id: F-5
    blocking: false
    rule: TB-3; ADR-004 decision 7
    statement: >-
      `install` and `status` inspect the PATH of the terminal that runs them (adr-004:77,
      component.md:57). The client launches the hook with its own environment, and a client
      started from a desktop launcher often has a different PATH. A relative element or an
      earlier `orqlet` in the client's PATH is not seen. K-12 requires a citation of how each
      client launches the command, but not of the environment it launches with. This
      leftover risk is not stated.
    required_change: >-
      Record the leftover risk in ADR-004's consequences and in the security consideration,
      or extend K-12 to cite each client's launch PATH and report a host step where it may
      differ.
  - id: F-6
    blocking: false
    rule: TB-2 credential redaction; ORQLET-SEC-003
    statement: >-
      Tool output summaries are redacted only of URL user-info and the literal values of the
      passed network variables (adr-006:53, component.md:198, BC-9). A credential carried in
      a URL path or query of an index address that uv reads from its own configuration is
      shown unredacted in a failure summary, in human and --json output. The preview's index
      line is already reduced to scheme and host (adr-006:57); the failure output is not.
    required_change: >-
      Apply the same reduction to every URL in tool output summaries (scheme and host only,
      or redact the path and query). Extend BC-9 with a URL that carries a token in its path.
  - id: F-7
    blocking: false
    rule: TB-1 shared-file ownership, uninstall, rollback and retention; ORQLET-SAFE-001
    statement: >-
      Two parts of ADR-002 do not fit together. First, after an interrupted apply the
      manifest is unwritten (adr-002:69). The next install then finds Orqlet-named files and
      Orqlet hook entries with no manifest record, which decisions 2 and 3 call conflicts
      (adr-002:59, 63). That breaks the claim that the re-plan converges (adr-002:69, BC-30).
      Second, retention prunes superseded changes on the next successful install
      (adr-002:71). The failure table still offers `rollback --user <id>` for the superseded
      change (component.md:203). If adoption is added so the re-plan converges, the first
      success deletes the only backup of the person's original shared file, which may hold
      credentials.
    required_change: >-
      State that a file or entry recorded as written in the superseded journal, whose hash
      matches that record, is adopted as owned. Also state whether a superseded change's
      backups are kept until it falls out of the last 3, or pruned with a preview warning
      that its rollback will no longer be possible. Align the failure-table row and BC-30.
  - id: F-8
    blocking: false
    rule: TB-3 hook path confinement; ORQLET-SEC-002
    statement: >-
      ADR-004 decision 5 says the hook reads only through a FileSystem port rooted at the
      home directory and "never reads above the home directory" (adr-004:62). Yet the Copilot
      AGENTS.md read uses "the starting directory itself when no root is found" (adr-004:65),
      and a starting directory outside home still yields the foundation (adr-004:62,
      BC-14). It is not stated whether the hook reads AGENTS.md from a directory outside home
      chosen by the payload, which would need a second port rooted there.
    required_change: >-
      State that outside home no repository file is read and the packaged foundation is
      always returned. Or name the bounded reader used there and its root.
```

## Author's responses

Every finding is accepted. Round 5 checks the changes.

| Finding | Response |
|---|---|
| F-1 | The amendment text in ADR-002 now says "owned by the user on POSIX". It adds that on Windows ownership is not checked, and that a data directory outside home is allowed only with a warning that its access is not checked (Q-41). Decision 1a and the text agree. |
| F-2 | The exemption is narrowed to "tool preparation by `orqlet install` through the fixed argument vectors of its tools adapter, whose writes go to the tools' own installation folders". |
| F-3 | The amendment text names the source of the allow-list: the roots and sub-paths that the user-scope file-system adapter declares. Adding a root or widening a sub-path needs a reviewed design. |
| F-4 | ADR-006: `uv` and `pipx` are resolved to absolute paths through the `ExecutableLocator`, using only absolute `PATH` elements, before any `ProcessRunner` call, `uv tool list` included. Where they cannot be resolved that way, `install` reports a `host step` and starts no process. BC-9 and the failures table are extended. |
| F-5 | ADR-004's consequences and the manifest's security consideration record the leftover risk of a client launched with a different `PATH`. K-12 also asks for each client's launch `PATH` where its documentation states it. |
| F-6 | ADR-006: every URL in a tool output summary is reduced to scheme and host. BC-9 adds a URL with a token in its path. |
| F-7 | ADR-002 decision 4 adds adoption: a file or entry that the superseded journal records as done, with a current hash equal to its after-hash, is adopted as owned, so the re-plan meets no conflict. Q-40 stands as answered. The preview warns that applying prunes the superseded change, and its rollback is possible only before the recovering install applies. ADR-002's consequences, the failures row, BC-30 and BC-31 match. |
| F-8 | ADR-004 decision 5: outside home, the hook reads no file and always returns the packaged foundation under `copilot`. The `AGENTS.md` read happens only inside home. BC-14 is extended. |
