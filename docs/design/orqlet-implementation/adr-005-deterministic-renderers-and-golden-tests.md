# ADR-005: Pure renderers without a template engine, verified by golden files

Status: proposed (needs approval with `design.md`).

## Context

One canonical definition is rendered into files for Claude Code, Codex and Cursor: skills, role definitions, rules, instruction blocks, the PR-template blocks and the `.prompts/` seed (proposal §12.3). Generated files must be byte-identical on every platform (goal G-2), and CI compares protected files byte for byte with the render of the pinned release (§17.12.4). No IDE was opened, so client behaviour is documentation-based (U-7). M1 needs TOML only for `.codex/agents/orqlet-*.toml`, which Orqlet writes whole, so no TOML round-trip library is required in M1 and M2 (U-10).

## Decision

1. **A renderer is a pure function** `render(definition, client, client_version) -> tuple[RenderedFile, ...]`. A `RenderedFile` holds a `CanonicalPath`, the bytes, the owner mode (`orqlet`, `shared-block`, `shared-entry` or `seeded`) and the class (`protected`, `generated` or `optional`).
2. **No template engine.** Output is built by small explicit functions. Text is UTF-8 with LF line endings and exactly one final newline, whatever the host operating system.
3. **Front matter and TOML are written by explicit emitters** that put fields in a fixed order and write every string value with `json.dumps(value, ensure_ascii=False)`, which is a valid YAML and TOML basic string. There is no dependency on a dumper's formatting.
4. **Client adapters** (`adapters/clients/{claude_code,codex,cursor}.py`) implement the `InstructionAdapter` port, declare the client versions they support, and return a capability limit instead of files for an unknown version.
5. **Golden files** live in `tests/golden/<client>/<min-version>/`. A test renders every definition and compares bytes. `pytest --update-golden` rewrites them locally; CI refuses that flag, so every change appears as a reviewed diff.
6. **Model pins** are an input to the renderer, taken from the approved policy (proposal §14.9). With no policy the file carries no pin.

## Consequences

- A change to a skill text, an adapter or a client version shows up as a golden-file diff that reviewers read.
- Protected-file comparison in CI is a plain byte comparison against the render of the baseline-pinned release.
- Adding a client or a client version means a new adapter or golden directory, never an edit of another client's output.
- The emitters are small but must be tested with awkward strings (quotes, colons, Unicode, leading dashes).

## Rejected alternatives

| Alternative | Why not |
|---|---|
| Jinja2 | An extra dependency, whitespace behaviour that varies with settings, and a template language inside files that agents load |
| Concatenating strings inside each adapter | Duplicates quoting and ordering rules three times |
| `yaml.safe_dump` for front matter | Output formatting can change between PyYAML releases, which would change a protected file without a source change |
| Generating files at install time | Output would depend on the installer's environment, and CI could not compare it with a render |
