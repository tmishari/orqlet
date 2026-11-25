# ADR-005: Schemas from the Rust types, and an xtask for the manifest and the schemas

## Context

The 35 shipped schemas are exported from the Pydantic contracts (A-8, A-11), and `MANIFEST.json` is built by `tools/build_manifest.py` (A-21, A-22). Both scripts are Python and are removed (Q-2). The person chose Rust replacements with schemas generated from the Rust types (Q-9). Two standards name the checks (ORQLET-DET-002, ORQLET-DET-003).

## Decision

1. Each contract type derives `schemars::JsonSchema` next to its serde derives; serde attributes such as `rename` and `deny_unknown_fields` shape the schema (`schemars-generation.md`). The registry of schema ids stays one list in `orqlet-application`.
2. A workspace member `xtask` (a binary not shipped) offers `cargo run -p xtask -- manifest [--check]`, `schemas [--check]` and `check` (both with `--check`). It writes the schema files to `workflow/schemas/` with sorted keys, two-space indent, raw UTF-8 and one trailing newline, and rebuilds `workflow/MANIFEST.json` from `workflow/identity.json` and the listed files.
3. A Rust test in `crates/orqlet-cli/tests/` runs the same comparison, so `cargo test` fails when a schema or the manifest is stale. The xtask writes `workflow/` directly as a developer tool; it is outside the shipped code that ORQLET-SAFE-001 and ORQLET-SEC-002 cover (ADR-006).

## Consequences

- The schema text changes once (2020-12 draft from schemars instead of Pydantic's output); consumers that pin the old text see a change in 1.0.0 (Q-5).
- Validation rules that serde cannot express (patterns, cross-field rules) are written in Rust and are added to the schema by `schemars` attributes only where they map to JSON Schema; the rest is documented in the schema `description`.
- The xtask depends on `orqlet-application` and is outside the shipped binary.

## Rejected alternatives

- Hand-kept schema files: no drift check between types and schemas, which ORQLET-DET-003 exists to prevent.
- A hidden `orqlet` subcommand: ships build tooling in the user binary.
- Generation in `build.rs`: runs on every build, writes into the source tree from a build script, and hides the change from review.
