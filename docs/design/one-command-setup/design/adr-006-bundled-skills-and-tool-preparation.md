# ADR-006: Bundled Graphify and Ponytail skills, and tool preparation

Status: proposed. Task: `one-command-setup`.

## Context

The person wants Graphify and all six Ponytail skills in every project Orqlet initializes or upgrades (Q-1, Q-3), and in the global folders (Q-38).

**Graphify** at revision 340268a (A-8, evidence `graphify.md`):

- declares graphifyy 0.9.112 and Python >=3.11,<3.15;
- uses platform-specific skill variants;
- has an unpinned dependency-install step with a system-pip fallback;
- has semantic extraction that can call a configured Gemini backend;
- is licensed Apache-2.0, with retained MIT terms.

**Ponytail** 5.3.3 at revision 96608e0 (A-9, A-58):

- has six skills, under MIT, copyright DietrichGebert;
- its help skill describes plugin features outside the Markdown skills;
- its front matter uses folded and extra fields that the loader does not accept (A-3).

uv installs a tool in an isolated, user-wide environment. A dependency's executables are not exposed (A-15), so Graphify must be its own tool installation. uv can download a managed Python (A-10).

On the pipx route, a missing uv is prepared and uv provides Python. There is no bootstrap script (Q-35). Git stays a prerequisite (Q-4), and Orqlet's Python floor is unchanged (Q-23).

Processes start only through `ProcessRunner` (ORQLET-SEC-001, A-12). Today the port is documented as used by the Git adapter only (A-29).

## Decision

1. **Snapshots in the workflow package.**
   - `graphify` and `ponytail`, `ponytail-review`, `ponytail-audit`, `ponytail-debt`, `ponytail-gain` and `ponytail-help` are stored as reviewed snapshots.
   - Each is adapted to the loader's one-line `name` and `description` front matter (A-3).
   - Each carries `PROVENANCE.md` (source URL, revision, the SHA-256 of each file, the licence, and Graphify's NOTICE; the upstream Git revision only identifies the source, and integrity rests on the SHA-256 values) and the upstream licence file.
   - The package manifest lists them with hashes (A-11). DET-002 then requires a manifest rebuild and a version bump.
2. **Adaptations, stated in each provenance file.**
   - Graphify: one skill whose client references are chosen per adapter; the dependency-install and system-pip steps are replaced by a check that `graphify` is on `PATH`; no Gemini or other model backend configuration is included; no model name the policy did not assign (ORQLET-MODEL-001).
   - Ponytail help: it describes only the six delivered skills. The band, plugin hooks and persistent configuration are named as upstream features that are not delivered.
   - Benchmark numbers stay attributed to the upstream.
3. **Invocation.** The bundled skills render as the other packaged skills do, for every client. Ponytail and Graphify cannot remove a required test, approval, phase boundary or independent review. Their reports supplement the review records.
4. **Tool preparation** happens in `install` only, never in `init`, `upgrade`, `status` or a hook. It uses fixed argument vectors through `ProcessRunner`:

   | Situation | Command | When |
   |---|---|---|
   | Check what uv manages | `uv tool list` | read-only; runs also under `--dry-run` |
   | Graphify | `uv tool install graphifyy==0.9.112 --python 3.12` | unless `uv tool list` shows graphifyy 0.9.112 |
   | pipx route, uv missing | `pipx install uv==<pinned version>` | before the Graphify step |
   | Locate uv after pipx | `pipx environment --value PIPX_BIN_DIR` | after the line above; uv is then called by its full path |
   | Neither uv nor pipx | none; exit 4 | — |

   - A `graphify` on `PATH` that uv does not manage is reported and never run.
   - The working folder is a scratch folder, `<data directory>/user/tools-work/`, created 0700 by the tools adapter after consent and kept out of the journal. It is never a project, so a project's package configuration is not read.
   - The environment is scrubbed (A-29) except `PATH`, `HOME` (or `USERPROFILE`), the platform's required variables, and the network variables the person controls: `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`, `ALL_PROXY`, `SSL_CERT_FILE` and `SSL_CERT_DIR`, upper- and lower-case. No value is printed. Before a tool's output summary is shown, every URL in it is reduced to scheme and host, so user-info, path and query are dropped, and every literal value of the passed network variables is replaced with `***`. This also applies to `--json`.
   - The `PIPX_BIN_DIR` value that `pipx environment` returns gets the same check before use: one line, an absolute path with no control characters, and a `uv` there that exists and is a regular file. Otherwise `install` reports a `host step` and starts no process for it.
   - Under `--dry-run`, when `tools-work/` does not exist yet, `uv tool list` is not run, so that nothing is created. The preview then reports the Graphify state as `not checked`.
   - The entry skill reads `install --json`. There, the tool output summary sits in a field named `tool_output`, capped, stripped of control characters and redacted as in human output. The skill shows that field to the person as data and never acts on its text.
   - `uv` and `pipx` are resolved to absolute paths through the `ExecutableLocator`, using only absolute `PATH` elements, before any `ProcessRunner` call, `uv tool list` included. When either cannot be resolved that way, `install` reports a `host step` and starts no process for it.
   - There is a timeout and an output cap (A-12).
   - The pins cover the top-level packages only. Transitive dependencies resolve at install time, and `--python 3.12` may download a managed Python (A-10), which is a second network source.
   - Under K-3, the plan verifies how the pinned uv and pipx versions ignore user-level configuration. Failing that, the preview reports the index that is configured, as scheme and host only, after the same redaction. Orqlet learns the index only from a fixed `ProcessRunner` vector cited under K-3, and never reads `uv.toml`, `pip.conf`, `pip.ini` or any other user package configuration file. Without such a vector, the preview says that the index configuration is not verified.

## Consequences

- Every project and every client gets the same reviewed copies, pinned and attributable. An upstream update is a reviewed snapshot refresh, never a silent fetch.
- `install` now fetches from the network, which makes it the only Orqlet command that does. `--dry-run` and every other command stay offline.
- The pins age. A new graphifyy release needs a snapshot refresh and a package release.
- An existing `graphify` on `PATH` at another version is reported and left alone. Two versions can coexist only where the person arranges it.
- Supply-chain trust rests on the package index, the exact top-level versions and uv's managed-Python source. Transitive dependencies and the Python build are not pinned by hash. The person accepted this residual risk for this release (Q-39). It is stated in the security consideration, and `install` output names it when it prepares a tool.

## Rejected alternatives

- **Running Graphify's own installer.** It defaults to Claude Code, writes instruction registrations and hooks itself, and installs dependencies unpinned (A-8).
- **Adding graphifyy as a dependency of Orqlet.** The Graphify executable would not be exposed (A-15), and its model and media extras would enter Orqlet's environment (A-8, ORQLET-NOMODEL-001).
- **Installing Ponytail's plugin runtime.** It brings executable hooks and configuration beyond the six skills (A-9). Q-3 asked for the skills.
- **Fetching the upstream skills at install time.** That is unreviewed content at run time, and not reproducible.
- **uv's standalone shell installer for the pipx route.** It pipes a download into a shell (evidence `uv.md`), which matches the warning list.
