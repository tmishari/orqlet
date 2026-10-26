# Orqlet

Orqlet is a small command-line tool that sets up and maintains the AI-assistant structure of a
repository, so that every developer's IDE starts from the same reviewed base. It supports
**Claude Code**, **Codex** and **Cursor**.

Orqlet never takes a prompt, never starts an agent and never calls a language model. Developers keep
writing prompts in their own IDE. Orqlet writes the files that the IDE reads, checks that they have
not drifted, and validates the documents that an agent produces.

## Problems it fixes

- **Every IDE needs its own setup.** Instructions, skills, rules and specialist agents are written
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
  `review prepare`.

What is **not** built yet: `orqlet ci check` and the merge-time gate, local Git hooks, the
knowledge index and module catalogue, and the MCP configuration. Approval cannot be verified by the
tool today: `orqlet gate status <task>` always ends `NOT_RUN` for approval, because approval is meant
to be a merge on the protected branch and that evidence comes from the code host. The generated files
follow each client's published documentation; the tests check the files, not the IDEs.

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

After an upgrade, start a new session in the IDE: a running session keeps the instructions it loaded.

## The workflow in the IDE

After `init`, the IDE offers these skills. Run them in order for a change that needs care:

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
| `validate` | Check an artifact an agent wrote |
| `gate` | Check what the workflow's gates would see |
| `evidence` | Print the hashes and citations an artifact must carry |
| `knowledge` | Knowledge that travels with the code |
| `review` | Independent review of a staged change |

Run `orqlet <command> --help` for the options.

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
