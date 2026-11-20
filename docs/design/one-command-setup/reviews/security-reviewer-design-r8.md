# Security review of the design, round 8

Reviewer: `orqlet-security-reviewer`, a typed subagent with its own context, started 2026-11-20T13:13:38Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md` and the output of `orqlet standards for` for the scope. It was also allowed read-only access to source files and `.prompts/rules.yaml`, to verify design citations.

## Hashes when the reviewer started and when the note was saved (`orqlet evidence hash`)

The hashes at start (2026-11-20T13:13:38Z) and at save (2026-11-20T13:15:33Z) are identical, and every design artifact hash equals the one recorded in `design/manifest.yaml`. The reviewed content is the content that will merge.

| File | sha256 |
|---|---|
| design/manifest.yaml | 80b3d2b47c5a577b833b4c93c1ee6051e8d0f3a76beffd579ca435bd14299d04 |
| design/adr-001 | c26cc24e7b47d241291da16766650edbda5f7529e3d4c81f94305ab51eac6972 |
| design/adr-002 | 4bfa17cdcef0d653f4ef9423cbfdbdb6d9a11fc1de7a4e782be667ebb8aef31b |
| design/adr-003 | f763bb0985455103f43a8392e4fdd7e7212bb94b92814f6564dcc98be91d4144 |
| design/adr-004 | 4325a150a453f18c1602ea2a1f702e0d6bbae376459f8c67fbd32e9bfccf90af |
| design/adr-005 | 9e5c51e9ce4b010dec0647a71ef326fb49369916d1d83583aaa1fb93c789119d |
| design/adr-006 | 5614e5ec2a3c0b09b08bbb51f8b6fd630496f21c61cb27e5639a82a3758ef949 |
| design/adr-007 | aff768709d7b902eb25f95dc53b6a4e42713b409f4ce0ca03587cedbb2fb90dd |
| design/component.md | b2467034ecdd0bc2d8434b65ab96b59a3ef1c96688ab4654e561c5c336e7161f |
| design/container.md | 6c56eeeb792bb270f9c1a0ce5ff54e0105ebe92a7be0a7477d43e8a4764f7102 |
| design/context.md | bc073e7aa91f01c3467cf882b7e378dcf1b72c20b8212bb7cdd30be06f2aa789 |
| design/data-flow.md | c2e15000e13b9c79302613897ffde516629019600b97dd4d9bb73b6caaf2d501 |
| design/sequence.md | d820e0307a235331b5f57bd385e5bba94a84885d47ba3f36a23ba2043211e114 |
| questions.yaml | b31b04e525d634ef09312149c0b26db2fd6bce6284e4f43cd02aefcbe8fe0255 |

## Reviewer output (unchanged)

**Verdict: approve.** The design now controls trust boundaries TB-1 to TB-3. The ORQLET-SAFE-001 amendment text at the end of ADR-002's Decision section matches decisions 1, 1a and 4. The person accepted every recorded residual risk in Q-39 to Q-44. I found nothing the design leaves uncontrolled or contradicts. There are 0 blocking and 4 non-blocking findings, each a detail the plan can settle within a stated control.

What I checked:
- Consent before any write, root validation and pinning, and path confinement.
- Shared JSON ownership and adoption of pending changes.
- Uninstall, rollback, retention and the 0600 backups.
- SEC-001 process starting, supply chain, and hook and repository-file bounds.
- Repository content that can reach agent context, terminal injection, credential redaction, SEC-002 and SEC-003.

I also verified these code citations against the source:
- `apply_plan.py:39-93`
- `local_fs.py:36` and `:74-77`
- `rules.yaml:66-72`
- `wiring.py:145-149`
- `change_journal.py:35`
- `ancestors.py:8-11`
- `upgrade.py:94` and `:353-380`
- `pyproject.toml:105-127`
- the strict YAML loader in `yaml_loader.py:87-114`. It rejects aliases and anchors and caps size, depth and node count, which supports the hook's lock-file bounds.

What I did not check:
- I could not confirm the revision or the artifact SHA-256 values, because the sandbox refused the git command I tried.
- I did not read the evidence files under `evidence/web`, because they are not among my allowed inputs. Client contracts were taken as the design states them.
- I did not read `as-is.md` in full. I read A-29 and spot-checked the citations of A-12, A-27 and A-29.
- I did no web lookup. So uv and pipx behaviour at the pinned versions is unknown to me, apart from what the design says.
- This review is an additional check, not a guarantee.

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 8, role: security-reviewer}
verdict: approve
findings:
  - id: F-1
    blocking: false
    rule: TB-2 (ADR-006 decision 4; constraint K-3)
    statement: >-
      ADR-006:52 says the scratch working folder "is never a project, so a project's package
      configuration is not read". K-3 (component.md:349-354) and ADR-006:60 only ask the plan
      to verify how the pinned uv and pipx ignore user-level configuration. Neither says whether
      uv finds project-level configuration (uv.toml or pyproject.toml) in the parent folders of
      the working folder. ADR-002:47 lets ORQLET_DATA_DIR lie outside home. ADR-002:50 rules out
      only a Git work tree there. So an ancestor of <data directory>/user/tools-work that is not
      a Git work tree, and that another account can write (for example under /tmp or a shared
      volume), could hold an index or source setting. That setting would redirect
      `uv tool install graphifyy==0.9.112`. I could not check from the repository whether the
      pinned uv reads such configuration for `uv tool` commands.
    required_change: >-
      Extend K-3: the plan cites, at the pinned uv and pipx versions, whether configuration is
      found in the working folder's parent folders. If it is, the plan either adds a cited fixed
      option or variable to the vectors that turns this off, or refuses or warns when such a
      file exists above tools-work. Add a fake-runner case to BC-9 that asserts the chosen
      vector or environment.
  - id: F-2
    blocking: false
    rule: TB-1 root validation (ADR-002 decision 1a; SAFE-001 amendment text)
    statement: >-
      On POSIX, a data directory outside home is allowed with no warning (ADR-002:47). The checks
      cover only the root and `user/`: not a link, owned by the user, and `user`, `journal` and
      `backups` tightened to 0700 (ADR-002:49, :52). The parent folders of the data directory are
      not checked for write access by other accounts. If such a parent is writable by group or
      others without the sticky bit, another account can rename `user/` away after validation
      and plant journals or backups. Adoption (ADR-002 decision 4) and `rollback --user` trust
      those files. This is the risk Q-41 accepts for Windows, but on POSIX it is checkable and
      neither controlled nor recorded. It needs a person-chosen shared location and a second
      local account.
    required_change: >-
      In the plan, have the user-root inspector also check each existing parent folder of a data
      directory outside home on POSIX. It should refuse with exit 3, or show the Q-41 warning,
      when a parent folder is writable by group or others without the sticky bit. Add a BC case.
      If the person prefers to accept the gap, record it as a ledger question instead.
  - id: F-3
    blocking: false
    rule: Consent before writes (component.md section 3 item 6; ADR-006 decision 4)
    statement: >-
      Under --dry-run, and before consent, `uv tool list` runs when tools-work exists
      (component.md:55, ADR-006:55). The design says --dry-run "writes nothing, in the user
      scope, a project or the data directory". It does not say whether the pinned uv creates
      lock, cache or tool-folder files outside those places when it lists tools. I could not
      verify that behaviour without the web. This may be a write made before consent, outside
      Orqlet's roots. It is not a contradiction of the amended SAFE-001, which covers only
      Orqlet's own writes.
    required_change: >-
      Under K-3, cite whether `uv tool list` at the pinned version writes anything. If it does,
      either state it in the --dry-run preview or skip the call until after consent. The
      preview would then show `not checked`, as it already does when tools-work is missing.
  - id: F-4
    blocking: false
    rule: Credential redaction (ADR-006 decision 4; BC-9)
    statement: >-
      ADR-006:53 says two things: URLs in tool output are reduced to scheme and host, and literal
      values of the passed network variables are replaced with `***`. It does not say in which
      order, or which encodings count. A proxy value without a scheme (`user:pass@proxy:8080`),
      or a percent-encoded or decoded form of the credential that a tool echoes, may escape both
      rules. BC-9 tests only `http://user:secret@proxy`, an index URL with a token in its path,
      and the literal proxy value.
    required_change: >-
      In the plan, replace the literal values first, in their raw, percent-encoded and
      percent-decoded forms, and then reduce URLs. Also reduce any `userinfo@host` pattern that
      has no scheme. Extend BC-9 with a scheme-less proxy value and a percent-encoded credential,
      in both human and --json output.
```

## Author's responses

Approved, no blocking finding. No design file changed after this note, so its hashes match the manifest. The non-blocking findings are carried into the plan, within the controls the design already states:

| Finding | Response |
|---|---|
| F-1 | Carried to the plan under K-3: cite whether the pinned uv and pipx find configuration in the parent folders of `tools-work`. If they do, use a cited option or variable that turns this off, or refuse or warn when such a file exists, and add a BC-9 fake-runner case. If no cited option exists, it becomes a ledger question. |
| F-2 | Carried to the plan. On POSIX, the user-root inspector checks each existing parent of a data directory outside home, and refuses or warns when a parent is writable by group or others without the sticky bit, with a BC. If the person prefers to accept the gap instead, it becomes a ledger question. |
| F-3 | Carried to the plan under K-3: cite whether `uv tool list` writes anything at the pinned version. If it does, skip it before consent and show `not checked`. |
| F-4 | Carried to the plan. Redaction replaces literal values first, in raw, percent-encoded and percent-decoded forms, then reduces URLs and any scheme-less `userinfo@host`. BC-9 is extended with those cases in human and `--json` output. |
