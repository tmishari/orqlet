# Security review of the design, round 3

Reviewer: `orqlet-security-reviewer`, a typed subagent with its own context, started 2026-11-20T12:52:18Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md` and the output of `orqlet standards for` for the scope. It was also allowed read-only access to source files, to verify design citations.

## Hashes when the reviewer started and when the note was saved (`orqlet evidence hash`)

The hashes at start (2026-11-20T12:52:18Z) and at save (2026-11-20T12:54:18Z) are identical: no design file changed while the reviewer ran. They are the hashes listed in `architecture-reviewer-design-r3.md` of the same round:

| File | sha256 |
|---|---|
| design/manifest.yaml | 05d1515697e6f4f962e001a5b4ccdbca5303eb2c874cf21e5fcc8770164bfd6a |
| design/component.md | 18b2cf5609e3f78594b774915d4bf94a8bd58f4b2eb17da81e861072119a9148 |
| design/context.md | bc073e7aa91f01c3467cf882b7e378dcf1b72c20b8212bb7cdd30be06f2aa789 |
| design/container.md | c66bf043e949384421ac711fd782d426ddf38b6a2f4c0394ed36033b37b9fae8 |
| design/data-flow.md | 12ca6e59332491343e8617b1511306eb81ccc6aeb802ab0c3791cba6680731bb |
| design/sequence.md | d820e0307a235331b5f57bd385e5bba94a84885d47ba3f36a23ba2043211e114 |
| design/adr-001 | 22a5adc6f263bdd07161fffdcb33d621ff8723d0fc5d6d358f898563246903c7 |
| design/adr-002 | b486b2b6718a1f4edf8ea4da9b1388527befe4f8135ff6f09ab71150679e7739 |
| design/adr-003 | f763bb0985455103f43a8392e4fdd7e7212bb94b92814f6564dcc98be91d4144 |
| design/adr-004 | 1b6bc1c72da155c6935a20b7fb7684f649dc048d0075f8eca35192cd897873bf |
| design/adr-005 | da4e25e94fd38b2b1df3607b02b42ffc24b8ed50117a200938abe4d9da9b7df4 |
| design/adr-006 | 7e5f4b619876954955d008d91d5d7003f5f1f92db1e4afc5fd69a51b1da96172 |
| design/adr-007 | aff768709d7b902eb25f95dc53b6a4e42713b409f4ce0ca03587cedbb2fb90dd |
| questions.yaml | b5437190c7ba63d7bcb8f6a55d604210d781d82174763dbdc8c6629f40b3402b |

The design files changed after this note (see "Author's responses"), and round 4 reviews the revised files.

## Reviewer output (unchanged)

**Verdict: approve.** 0 blocking and 5 non-blocking findings. The round-2 points are answered in the design, with controls at each trust boundary:

- **TB-1, user client folders:** root validation covers roots that do not exist yet and the data directory (ADR-002:46-56). Each root has a table of writable sub-paths and folder boundaries that uninstall never removes (ADR-002:27-44). Shared JSON files are parsed strictly and Orqlet replaces an entry only when the manifest holds its matching hash (ADR-002:62-67). Backups and journals are 0600, and no preview, conflict or `--json` output prints a shared file's content (ADR-002:72-73).
- **TB-2, package index:** processes start only through `ProcessRunner`, with fixed argument vectors, a scrubbed environment and redaction of tool output (ADR-006:42-56). The residual supply-chain risk is recorded as accepted (ledger Q-39).
- **TB-3, hook payloads and repository content:** hooks run under size caps and a strict parser, start no process, and fill fixed templates with validated fields only (ADR-004:37-75). On Windows, a client that resolves a bare command through the working directory gets no registration (ADR-004:77).
- **Hashes and repository files:** SHA-256 only, including provenance (ADR-006:34). Repository files are read only through the FileSystem port with the strict YAML loader.

I checked these code citations and they hold: `local_fs.py:74-77`, `wiring.py:145-149`, `apply_plan.py:39-93`, `ancestors.py:8-11`, `common.py:27-28` and `pyproject.toml:115-127`. `SubprocessRunner` uses no shell and passes exactly the environment it is given. `write_atomic` keeps the mode of an existing file, so a rewritten 0600 `settings.json` stays 0600.

I could not check:

- `.prompts/rules.yaml:66-72`, which is outside the allowed inputs.
- The web evidence files and the round 1 and round 2 review notes, which I did not open.
- Any native client behaviour, since nothing was run.

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 3, role: security-reviewer}
verdict: approve
findings:
  - id: F-1
    blocking: false
    rule: TB-3 / ORQLET-SEC-002 (status output reaching agent context)
    statement: >-
      The status JSON field `top_level` has control and bidirectional characters
      removed and is capped at 200 characters
      (adr-001-install-command-entry-skill-and-status.md:31). The entry skill then
      passes that value back as `orqlet init --root <top>` and `orqlet upgrade --root
      <top>`, first with `--dry-run` and then with `--yes`
      (adr-001-install-command-entry-skill-and-status.md:24-25; sequence.md:28-33).
      When sanitizing changes a real path (a long path cut short, or a stripped
      character), the agent targets a directory that was never checked. A cut-short
      path can name a parent directory, and a stripped name can collide with another
      directory. The dry-run preview and the person's yes reduce the risk, but the
      design does not say what happens when the sanitized value differs from the real
      one.
    required_change: >-
      When sanitizing would change `top_level` (or any path), emit null plus a closed
      reason such as `path-not-representable`, never a changed path. Make the entry
      skill stop on null instead of passing a value to `--root`. Add a hostile-path
      case to BC-11 that asserts null rather than a truncated path.
  - id: F-2
    blocking: false
    rule: TB-3 (hook command resolution), ADR-004 decision 7
    statement: >-
      Decision 7 withholds a registration only where the client resolves a bare
      command through the working directory before PATH (cmd.exe-style lookup)
      (adr-004-advisory-native-hooks.md:77; component.md:194, K-12 at 316). On POSIX,
      a PATH that contains `.`, an empty element or a relative directory has the same
      effect: hooks run in any repository the client opens, including untrusted
      clones (adr-004-advisory-native-hooks.md:30), so an `orqlet` file inside the
      clone could run instead. `install` and `status` report only which `orqlet` PATH
      resolves to from their own working directory (component.md:56), which does not
      reveal relative entries.
    required_change: >-
      Make `install` and `status` inspect PATH for empty, `.` or relative elements
      and report a `host step` naming the risk. Withhold hook registration while such
      an element comes before the folder of the resolved `orqlet`. Add a test case
      for it.
  - id: F-3
    blocking: false
    rule: TB-2 / ADR-006 credential redaction, K-3
    statement: >-
      If the plan cannot show that the pinned uv and pipx ignore user-level
      configuration, "the preview reports the index that is configured"
      (adr-006-bundled-skills-and-tool-preparation.md:56; component.md:307). Index
      URLs in uv or pip configuration often carry `user:token@` credentials. The
      redaction rule covers only "a tool's output summary"
      (adr-006-bundled-skills-and-tool-preparation.md:53), not this preview line. The
      design also does not say how the index is found: reading `uv.toml`, `pip.conf`
      or `pip.ini` would mean reading credential-bearing files, against the security
      consideration "Orqlet reads no credential" (manifest.yaml:127).
    required_change: >-
      State that the index report shows only scheme and host and passes through the
      same redaction, in human and `--json` output. State that the index is obtained
      only from a fixed `ProcessRunner` vector, never by Orqlet reading user package
      configuration files. Extend BC-9 to cover the preview line.
  - id: F-4
    blocking: false
    rule: TB-1 (backups of shared files), ORQLET-SEC-003 data exposure
    statement: >-
      Before rewriting a shared file, Orqlet backs up the full original into
      `user/backups/<change-id>/` (adr-002-user-scope-root-journal-and-manifest.md:69,72,94).
      `~/.claude/settings.json` can hold credentials, such as `env` values or an API
      key helper. The design sets no retention or pruning for these copies, so they
      add up across installs. The data directory may lie outside home through
      `ORQLET_DATA_DIR` (adr-002-user-scope-root-journal-and-manifest.md:50), for
      example in a synced or shared folder. The owner check and the 0700 tightening
      are POSIX-only (adr-002-user-scope-root-journal-and-manifest.md:51,54); on
      Windows, nothing checks the access control list of a data directory outside
      home. This is a consequential data-exposure trade-off with no ledger question.
    required_change: >-
      Either decide a retention rule for user-scope backups (for example, keep only
      the backups that rollback can still use, or prune on a successful uninstall
      and on superseded changes) and state the Windows behaviour (refuse, or warn
      about, a data directory outside home whose permissions Orqlet cannot check), or
      raise a ledger question so the person accepts the residual risk. Say in the
      security consideration that backups may contain credentials.
  - id: F-5
    blocking: false
    rule: ORQLET-SEC-002 (bounds on reading repository files in status full mode)
    statement: >-
      ADR-004 limits the hook's repository reads: one regular file, never a link, at
      most 1 MiB, size checked before reading (adr-004-advisory-native-hooks.md:63-71).
      The `status` command in full mode reads the same `.orqlet/` locks from a
      directory that an agent passes in, and its output also reaches agent context
      (adr-001-install-command-entry-skill-and-status.md:29-31). The design gives only
      output sanitization for that mode. It states no size cap or rule against links
      for these reads, and does not say whether status reuses the hook's bounded
      reader.
    required_change: >-
      State that the full mode reads `.orqlet/` locks through the same bounded,
      link-refusing FileSystem reader with the strict loader as the hook mode, or
      give its own limits. Add an oversized-lock case to BC-11.
```

## Author's responses

Every finding is accepted. Round 4 checks the changes.

| Finding | Response |
|---|---|
| F-1 | ADR-001 decision 3: a path is printed only as it really is. A path that holds a control, bidirectional or format character, or that is longer than 200 characters, becomes null with the closed reason `path-not-representable`. The entry skill stops on a null `top_level` and never passes an altered path to `--root`. Section 3's field table, the failures table and BC-11 match. |
| F-2 | ADR-004 decision 7: on every system, `install` and `status` inspect `PATH` for empty, `.` or relative elements. When such an element comes before the folder of the resolved `orqlet`, no hook is registered, and a `host step` names the risk. The `ExecutableLocator` port reports these elements. BC-38 tests this, and the failures table has the row. |
| F-3 | ADR-006: the index report shows scheme and host only, after the same redaction. The index is learned only from a fixed `ProcessRunner` vector cited under K-3. Orqlet never reads `uv.toml`, `pip.conf`, `pip.ini` or other user package configuration; without such a vector, the preview says the index configuration is not verified. BC-9 is extended. |
| F-4 | The person decided both points. Q-40: the backups and journals of the last 3 user-scope changes are kept, and a successful `install` or `uninstall` prunes older and superseded ones. Q-41: on Windows, a data directory outside home is allowed, with a warning in the preview. ADR-002 decisions 1a and 4 and its consequences state both, as do the security consideration (backups may contain credentials), the failures table, BC-37 and BC-39. |
| F-5 | ADR-001 decision 3: `status` reads the `.orqlet/` locks through the same bounded reader as the hooks: regular files only, never links, at most 1 MiB, with the strict YAML loader. BC-11 covers an oversized lock and a lock that is a link. |
