# ADR-001: One distribution, `src` layout, enforced layers

Status: proposed (needs approval with `design.md`).

## Context

The proposal fixes Clean Architecture with ports and adapters, `import-linter` and Ruff `TID251` as the enforcement tools, and five extension points plus six test seams to build first (§6.2, §6.8; facts A-16, A-18). The team is small. M1 and M2 hold about forty use-case and validator modules.

## Decision

1. One installable distribution named `orqlet`, with the `src/orqlet/` layout of `design.md` section 5.1.
2. Four code packages with a one-way dependency: `interface` to `application` to `domain`, and `adapters` implementing the ports of `application`. The workflow package (`src/orqlet/workflow/`) is read-only data.
3. The contracts of `design.md` section 5.2 are written as `import-linter` contracts in `pyproject.toml` and run in CI on every pull request. Ruff `TID251` bans `subprocess`, `socket`, `sqlite3`, `http` and `urllib` in `domain` and `application`.
4. Use cases receive their ports through the constructor. The only composition roots are `interface/cli/app.py` and `interface/hooks/*`. There is no dependency-injection framework.
5. Every module has one reason to change. A use case does one user-visible operation.

## Consequences

- Domain and application code runs in tests with fake ports and no I/O (goal G-3).
- A new client or host adapter is added without touching `domain` or `application`.
- The contracts fail the build when someone imports across a layer, so the rule does not depend on review.
- The cost is more files and an explicit wiring step in the two composition roots.

## Rejected alternatives

| Alternative | Why not |
|---|---|
| Several distributions (core, clients, CI) | Three release lines and three pins for a small team. The proposal's pin and `workflow_digest` model assumes one package |
| Flat layout without `src/` | Tests could import the working tree instead of the built package, which hides packaging errors |
| A dependency-injection framework | Extra dependency and indirection. Constructor injection covers the two composition roots |
| Ports defined in `domain` | The proposal puts ports in the application layer (§6.2), and `domain` stays free of I/O vocabulary |
