# Orqlet

Orqlet is a small command-line tool that sets up and maintains the AI-assistant structure of a
repository, so that every developer's AI coding client starts from the same reviewed base. A client
is an AI coding tool (an agent harness) that can run in a terminal, in an IDE or both. Orqlet
supports three: **Claude Code**, **Codex** and **Cursor**.

Orqlet never takes a prompt, never starts an agent and never calls a language model. Developers keep
writing prompts in their own client. Orqlet writes the files that the client reads, checks that they have
not drifted, and validates the documents that an agent produces.

## Problems it fixes

- **Every client needs its own setup.** Instructions, skills, rules and specialist agents are written
  once and rendered for each client, so the three clients do not diverge.
- **The setup is not shared or reviewed.** The structure lives in the repository and arrives through
  an ordinary pull request. Edits the team made by hand are kept when the structure is upgraded.
- **The setup drifts unnoticed.** `orqlet doctor` and `orqlet sync` report files that are missing,
  edited, stale or unknown, and every change is journalled so `orqlet rollback` can undo it.
- **Agents skip steps.** A fixed workflow (research, design, plan, implement, review) is shipped as
  skills. Each skill stops at a person: an agent cannot approve its own design or plan.
- **Agent output is not checked.** Validators read the AS-IS facts, design, plan, review, test and
  knowledge-impact files an agent writes, and check evidence references, hashes and structure.

## Status

Version 0.1.0. What is built and tested in this repository:

- `init`, `upgrade`, `rollback`, `sync`, `doctor`, `explain`, `release` and `profile`;
- the workflow skills, role definitions and rules for the three clients;
- the validators and `gate status`, `evidence cite`, `evidence hash`, `knowledge impact` and
  `review prepare`;
- the registry of links to team resources (`resources add`, `update`, `remove`, `attach`, `list`,
  `validate resources`), the conventions of the profile and `conventions check`, and the rules,
  skills and `AGENTS.md` block that render them for the three clients.

What is **not** built yet: `orqlet ci check` and the merge-time gate, local Git hooks, the
knowledge index and module catalogue, and the MCP configuration. Approval cannot be verified by the
tool today: `orqlet gate status <task>` always ends `NOT_RUN` for approval, because approval is meant
to be a merge on the protected branch and that evidence comes from the code host. The generated files
follow each client's published documentation; the tests check the files, not the clients.

Orqlet itself opens no connection and reads no credential. A page is read by the client's own web
tool, as the developer, under the section "Looking things up" of the baseline. That text is advice
to the agent, not a control, and no check has shown that a client honours it: each client reports
the capability limit ORQ-L006 for it. A person records the checks of the design (V-1 to V-8, V-10 and V-11) with a
test account before a claim about a client is made.

The full design is in
[`docs/design/orqlet-architecture-proposal.md`](docs/design/orqlet-architecture-proposal.md); its
Section 22.0 says what is built.

## Requirements

- Python 3.12 or later (CI runs 3.12 to 3.15 on macOS, Linux and Windows)
- [uv](https://docs.astral.sh/uv/)
- Git

## Install

From a checkout of this repository:

```sh
uv tool install .
orqlet --version
```

To run it once without installing: `uvx --from /path/to/orqlet orqlet --version`.

## Use it in a project

Run these in the project you want to set up. Every command that writes first shows a preview, and
`--dry-run` writes nothing.

```sh
orqlet init --dry-run           # see every file that would be written
orqlet init --client cursor     # write them (repeat --client; the default is all three)
orqlet doctor                   # what is missing, edited, stale or unknown
orqlet profile answer repository.target_branch=main
orqlet profile approve --reviewer "Your Name"
```

`init` works for an existing project, a new one (`--git-init`, `--new-project`) or an empty
directory. It writes the skills, agent definitions, commands and rules of the chosen clients, an
`AGENTS.md` block, a pull request template, a seeded `.prompts/` folder for the team's standards and
a `.orqlet/` folder with the project profile, versions, role bindings and lock files. Review the
result in a normal pull request: merging it is the team's approval of the base.

Day to day:

```sh
orqlet sync        # check this checkout against the manifest; writes nothing
orqlet doctor      # report drift; writes nothing
orqlet upgrade     # re-render from a newer release, keeping the team's edits
orqlet rollback    # restore the files of one change, if nothing has touched them since
```

After an upgrade, start a new session in the client: a running session keeps the instructions it loaded.

## The workflow in the client

After `init`, the client offers these skills. Run them in order for a change that needs care:

| Skill | What it does | Writes |
|---|---|---|
| `orqlet-onboard` | Resolves what is still unknown in the project profile with you, from repository evidence | `.orqlet/project-profile.yaml` |
| `orqlet-research` | Records verified facts, unknowns and contradictions | `docs/design/<task>/as-is.md` |
| `orqlet-design` | Records the design and its decisions | `docs/design/<task>/design/` |
| `orqlet-plan` | Splits the design into phases with exact file operations | `docs/design/<task>/plan.yaml` |
| `orqlet-implement` | Builds one approved phase inside its file list, tests first, with the knowledge step | code, tests, records |
| `orqlet-review` | Starts the independent architecture and security reviews of the staged change on a read-only packet | review records |

Each skill stops at a person: you accept the AS-IS file, and you approve the design and the plan by
merging them. The skills start read-only subagents where the client has them (inventory, tracer,
tester, architecture reviewer, security reviewer).

You can run the checks yourself:

```sh
orqlet validate as-is docs/design/<task>/as-is.md
orqlet validate design docs/design/<task>/design/manifest.yaml
orqlet validate plan docs/design/<task>/plan.yaml
orqlet gate status <task>                 # are the artifacts still current?
orqlet standards for --path src --phase design --role architect
```

## Commands

| Command | Purpose |
|---|---|
| `init` | Set up the AI context of a project: existing, new or empty |
| `upgrade` | Re-render the setup from this release without overwriting the team's edits |
| `rollback` | Restore the files of one change |
| `sync` | Check this checkout against the manifest (writes nothing) |
| `doctor` | Report what is missing, edited, stale or unknown (writes nothing) |
| `explain` | Show what is declared, what is generated and what Orqlet cannot see |
| `release` | Take a file out of the manifest (protected files cannot be released) |
| `profile` | Answer open facts and approve the project profile |
| `standards` | Read the standards that apply to a path, phase and role |
| `validate` | Check an artifact an agent wrote, and the registry of links (`validate resources`) |
| `resources` | Register links to team resources (`add`, `update`, `remove`, `attach`, `list`) |
| `conventions` | Check the branch name and the commit subjects against the profile (`check`) |
| `gate` | Check what the workflow's gates would see |
| `evidence` | Print the hashes and citations an artifact must carry |
| `knowledge` | Knowledge that travels with the code |
| `review` | Independent review of a staged change |

Run `orqlet <command> --help` for the options.

## Checks for pull requests

Three offline commands can run in a CI job of your code host on every pull request. CI on the host
is the check that decides; Orqlet builds no local hook.

- `orqlet validate resources` checks `.orqlet/resources.yaml` and every stored copy under
  `docs/resources/`: hashes, the two header lines, hidden text and credential shapes, and any file
  that no entry names.
- `orqlet conventions check` checks the branch name against the branch patterns of the profile and,
  when the commit convention is `conventional-commits`, the subject of every commit of
  `base..head`. The rules are read from the profile at the base revision, not from the pull
  request, so a pull request cannot relax the rule that judges it; a change of the profile takes
  effect after it is merged.
- `orqlet upgrade --check` exits non-zero when a change of the registry or the profile has not been
  rendered, or when a protected generated file was edited by hand.

Add the step after the conventions are answered: `conventions check` is `NOT_RUN`, and exits 5,
when nothing is configured, when the base cannot be found (a shallow clone), or when a Git command
fails. Replace `<cli.pinned>` by the commit id (a tag can move) of the version that `cli.pinned` of
`.orqlet/versions.yaml` names, written into the workflow file itself and not read from the pull
request, and replace the action pins by the commits of releases you have reviewed. The runner must
be able to read the Orqlet repository without a secret. Always pass `--base` in CI: without it the
base comes from the target branch named in the working tree, which a pull request can change.

```yaml
name: orqlet-checks

on:
  pull_request:

permissions:
  contents: read

jobs:
  orqlet:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: astral-sh/setup-uv@1c37ad07a6a961277cf70c0d37d6f313000f5884 # v10.3.0
      - run: uv tool install "git+https://github.com/tmishari/orqlet@<cli.pinned>"
      - run: orqlet validate resources
      - run: orqlet conventions check --branch="$HEAD_REF" --base="origin/$BASE_REF"
        env:
          HEAD_REF: ${{ github.head_ref }}
          BASE_REF: ${{ github.base_ref }}
      - run: orqlet upgrade --check
```

The snippet uses `pull_request` and never `pull_request_target`, reads the contents only, keeps no
credentials, has a timeout, passes the branch names through `env:` and has no `if:` on the job,
because a skipped job counts as passed for a required status check. A pull request can still
remove the step or change the workflow file, so the workflow file needs a reviewer of its own
(for example a CODEOWNERS entry for `.github/workflows/`). Whether the step blocks a merge
depends on a person making it a required status check on the host; Orqlet cannot set or read that.
Do not pipe the output of `conventions check` into a job summary or another log command without
escaping it: it shows branch and subject text escaped and cut at 100 characters, which bounds the
size and is not a control.

What is checked, and what is not:

- Of the eight conventions in the profile (branch model, branch naming, commit convention,
  pull-request shape, merge strategy, required checks, reviewers, release flow), two of the eight
  conventions are checked by a tool: the branch name and, for `conventional-commits`, the commit
  subjects. The other six are recorded and told to agents. A host can enforce some of them through
  branch protection, which Orqlet cannot read, so confirm those settings there.
- A subject that starts with `Merge ` is not checked, and a `Revert` subject has to have the shape
  too. Under a squash merge the commit that lands has the pull-request title, and a squash-merge
  title is outside the check, because the check never sees it.
- Stored copies and registered links reach the instructions of three clients, so the pull request
  that changes them must be reviewed. Reviewers read the raw diff of `docs/resources`: rendered
  Markdown can hide text in HTML and in link definitions. Keep copies of pages behind a login, and
  browser storage-state files, cookies and tokens, out of Git; `validate resources` refuses a copy
  that has such a shape, but its scan is a list of known shapes and not a guarantee.
- A path glob of a link cannot hold a space, `@`, a backtick or angle brackets, and a convention
  answer cannot hold `@`, a link, markup or a backtick.

### Finding codes of the registry, the conventions and the check

| Code | Meaning |
|---|---|
| ORQ-E500, E501, E502 | The registry cannot be read safely, fails its contract (a file that the strict loader refuses is reported here too), or is above 256 KiB |
| ORQ-E503 | `init` (run again) or `upgrade` refuses an invalid registry, or one that is missing while the lock records it |
| ORQ-E504 | A stored copy is missing, or is not a regular file that can be read |
| ORQ-E505 | A stored copy differs from the SHA-256 recorded for it |
| ORQ-E506 | A stored copy fails its header, hidden-text or credential check, is not valid UTF-8 or is above 64 KiB |
| ORQ-E507 | Reserved: a login copy that is not a summary is reported as ORQ-E501, because the contract refuses it |
| ORQ-E508 | An item under `docs/resources` is not a regular `<id>.md` named by an entry that records a copy |
| ORQ-E509 | An edit command is refused (also a skipped link at `init`, as a warning) |
| ORQ-E510 | `resources attach` for an entry behind a login needs a terminal |
| ORQ-E511 | `evidence cite` refuses a file under `docs/design/*/evidence/web/` with a credential shape, a hidden character or more than 256 KiB; the file is already in a local commit, so amend it before a push |
| ORQ-E520, E521 | A branch name is not allowed by the patterns; a commit subject has the wrong shape |
| ORQ-W500 | A stored copy is past its time-to-live (advice: a hand edit of the record can hide it) |
| ORQ-I500 | An entry behind a login: its page text goes to the client's model vendor |
| ORQ-I501 | A copy whose entry is gone (Orqlet never deletes a copy) |
| ORQ-I502, I503 | Conventions that are not recorded; conventions that only the host can enforce |
| ORQ-I504 | `init` registered no links and says how to add them |
| ORQ-I520 | The branch check was skipped because the branch is the target branch |
| ORQ-L006 | Lookups on the web are requested by the baseline; how to opt out; documented and not observed |

What stays with the team:

- A stored copy and a link are text that three clients read as guidance. The scans catch known
  shapes (token prefixes, a JWT, a private-key block, user information in an address, an
  authorization value, a `key=value` pair, the shape of a browser storage-state file) and not every
  secret: a PGP armor header, a cookie value and a short password are outside them. Review is the
  control.
- The freshness of a copy is advice. The hash and the time are bookkeeping: one pull request can
  change both the file and its record.
- The `access` of an entry and the `form` of a copy are labels that the team declares. A login
  site registered as `public` escapes the summary-only rule, and nothing tells a summary from a
  pasted page.
- A client that has no web tool, or whose tool is off, gets only what a stored copy holds.
- Taking a managed block out of `AGENTS.md` leaves one blank line behind.
- The guard of `evidence cite` runs when a file is cited and not before: a file under
  `evidence/web/` that is never cited is never scanned, `evidence hash` is not guarded, no CI step
  walks the folder, and a design cites its evidence as `path:lines` strings. A file with invalid
  UTF-8 and nothing else wrong is cited.
- A stored copy has a licence and a permission of its own; the registry does not record either. A
  convention answer such as the reviewers reaches `AGENTS.md`, so do not put a personal name in it
  that the team does not want in the repository.
- Keep a browser profile that agents use signed in only to the team's sites, and keep profile
  folders out of Git.

## Development

```sh
uv sync --locked --all-groups
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run lint-imports
uv run python tools/export_schemas.py --check
uv run python tools/build_manifest.py --check
```

These are the checks that CI runs. The code follows layered boundaries enforced by `import-linter`,
and all output is deterministic: the same inputs give the same bytes on every platform.

## License

No license is declared in this repository yet.
