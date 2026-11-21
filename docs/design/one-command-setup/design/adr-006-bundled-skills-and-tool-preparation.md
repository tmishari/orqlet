# ADR-006: Bundled Ponytail skills

Status: proposed. Task: `one-command-setup`.

## Context

The person wants all six Ponytail skills in every project Orqlet initializes or upgrades (Q-3), and in the global folders (Q-38). Graphify and the preparation of its tools were part of this task (Q-1, Q-2, Q-35); the person moved both to a separate task with a security-first design (Q-60). Q-60 supersedes Q-2, Q-39, Q-46, Q-51, Q-52, Q-56, Q-58 and Q-59, and the Graphify part of Q-1 and the uv part of Q-35; those answers carry over to the separate task.

**Ponytail** 5.3.3 at revision 96608e0 (A-9, A-58):

- has six skills, under MIT, copyright DietrichGebert;
- its help skill describes plugin features outside the Markdown skills;
- its front matter uses folded and extra fields that the loader does not accept (A-3).

Git stays a prerequisite (Q-4), and Orqlet's Python floor is unchanged (Q-23).

## Decision

1. **Snapshots in the workflow package.**
   - `ponytail`, `ponytail-review`, `ponytail-audit`, `ponytail-debt`, `ponytail-gain` and `ponytail-help` are stored as reviewed snapshots.
   - Each is adapted to the loader's one-line `name` and `description` front matter (A-3).
   - Each carries `PROVENANCE.md` (source URL, revision, the SHA-256 of each file and the licence; the upstream Git revision only identifies the source, and integrity rests on the SHA-256 values) and the upstream licence file.
   - The package manifest lists them with hashes (A-11). DET-002 then requires a manifest rebuild and a version bump.
2. **Adaptations, stated in each provenance file.**
   - No model name the policy did not assign (ORQLET-MODEL-001).
   - Ponytail help: it describes only the six delivered skills. The band, plugin hooks and persistent configuration are named as upstream features that are not delivered.
   - Benchmark numbers stay attributed to the upstream.
3. **Invocation.** The bundled skills render as the other packaged skills do, for every client. Ponytail cannot remove a required test, approval, phase boundary or independent review. Its reports supplement the review records.
4. **Tool preparation.** Withdrawn; moved to a separate task (Q-60).

## Consequences

- Every project and every client gets the same reviewed copies, pinned and attributable. An upstream update is a reviewed snapshot refresh, never a silent fetch.
- No Orqlet command uses the network or prepares a tool. `install` writes only the user scope (ADR-002).
- Graphify is not delivered by this task; the separate task decides how it is delivered (Q-60).

## Rejected alternatives

- **Installing Ponytail's plugin runtime.** It brings executable hooks and configuration beyond the six skills (A-9). Q-3 asked for the skills.
- **Fetching the upstream skills at install time.** That is unreviewed content at run time, and not reproducible.
- **Keeping tool preparation without Graphify.** Tool preparation existed to install the Graphify CLI; uv was prepared only so that Graphify can be installed (Q-35). Without Graphify it would install nothing that this task uses (Q-60).
- **Bundling Graphify in this task.** Upstream graphify, run in a cloned repository, lets that repository run code. Every step runs `$(cat graphify-out/.graphify_python) -c ...` from the repository root, so a committed `.graphify_python` runs, and because Python puts the working folder first on `sys.path` for `-c`, so does a committed `json.py` or `graphify/__init__.py`. Its writes under `graphify-out` follow committed symbolic links. Hardening it amounts to a fork, which needs its own security-first design (Q-56, Q-59, Q-60).
