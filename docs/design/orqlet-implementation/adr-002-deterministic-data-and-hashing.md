# ADR-002: Deterministic data, canonical JSON and strict YAML

Status: proposed (needs approval with `design.md`; decision D-2).

## Context

The proposal hashes structures with RFC 8785 canonical JSON and SHA-256 only (§6.14): `workflow_digest`, the review-input binding, the state digest and approval records. Records are YAML. YAML anchors, custom tags and unknown keys must be rejected in evidence records (§6.14.1). The only RFC 8785 package on PyPI, `rfc8785` 0.1.4, was last released on 2024-09-27 and its metadata carries no license text (U-9). `PyYAML` 6.0.3 is available (`as-is.md` section 3a). Python's `json.dumps(sort_keys=True)` is not RFC 8785: it orders keys by code point, not by UTF-16 code unit, and formats numbers its own way.

## Decision

1. **Canonical JSON subset, in-tree** (`src/orqlet/domain/digest.py`). It accepts objects, arrays, strings, booleans, null and **integers only**, within plus or minus 2^53 minus 1. Floats raise an error, so the hard part of RFC 8785 (number formatting) never arises.
   - Object keys are ordered by their UTF-16 code units (compare `key.encode("utf-16-be")`).
   - Strings use the ECMAScript escapes that RFC 8785 requires: `\b \t \n \f \r \" \\` and `\u00xx` in lower case for other control characters below U+0020. Other characters, including `/` and non-ASCII, are written as UTF-8 without escaping. Lone surrogates are rejected.
   - No whitespace. Duplicate keys cannot occur in Python mappings and are rejected at the YAML loader.
2. **Digests** are `hashlib.sha256` over those bytes, written as lower-case hex. No other algorithm is available through the module.
3. **Strict YAML loading** (`src/orqlet/adapters/fs/yaml_loader.py`): `yaml.SafeLoader` subclass that rejects anchors, aliases, merge keys, duplicate keys and any tag outside the YAML core schema, enforces a byte limit before parsing, and returns plain data that a frozen Pydantic model with `extra='forbid'` then validates (A-14). `ruamel.yaml` is not used in M1 and M2: Orqlet writes whole files or managed blocks, not round-trip edits.
4. **Paths**: `CanonicalPath` in `domain/paths.py` implements the key rules of the proposal's plan validator (§17.5): NFC, case-fold per component, reserved names and separators rejected.

## Consequences

- Digests are reproducible on every platform and do not depend on a third-party library's maintenance.
- The test suite carries the RFC 8785 vectors for ordering and string escaping, plus a property test that a digest is independent of input key order.
- Floats are forbidden in every hashed structure. Contracts that carry numbers use integers (counts, sizes, milliseconds).
- Writing the serializer is a small, reviewable piece of code (a few dozen lines) that this decision makes Orqlet's responsibility.

## Rejected alternatives

| Alternative | Why not |
|---|---|
| The `rfc8785` package | Last release in 2024, no license text in its metadata, and it handles the full number grammar that Orqlet never needs |
| `json.dumps(sort_keys=True, separators=(",", ":"))` | Not RFC 8785: different key order for characters outside the Basic Multilingual Plane, and different number text |
| Hashing the YAML text | A formatting change would change a digest |
| `ruamel.yaml` everywhere | Pre-1.0, single maintainer, and round-trip features are not needed for whole-file writes |
