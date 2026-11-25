# ADR-003: Libraries

## Context

The Python release uses Typer, Pydantic, PyYAML, filelock, platformdirs and Rich (A-1), plus standard-library parts that Rust lacks: SHA-256, Unicode normalisation, `fnmatch`, `difflib` and TOML (A-9, A-15, A-33). The strict YAML loader is a security control (ORQLET-SEC-002, A-13). Each dependency is a cost; the standard library is used where it suffices.

## Decision

| Need | Choice | Replaces |
|---|---|---|
| Command line | `clap` (derive); usage errors exit 2 (`clap-exit-status.md`) | Typer |
| Contracts and JSON | `serde`, `serde_json` (sorted map, pretty print) | Pydantic, `json` |
| Strict YAML read and write | `serde-saphyr`: its parser's events build the generic tree of ADR-007 decision 3, and its serializer writes YAML (`serde-saphyr-options.md`) | PyYAML loader and emitter |
| JSON Schema | `schemars` (`schemars-generation.md`) | Pydantic schema export |
| TOML (every input of ADR-007 decision 5) | `toml`, in the documents module | `tomllib` |
| SHA-256 | `sha2` | `hashlib` |
| NFC | `unicode-normalization` | `unicodedata.normalize` |
| Unicode categories for paths and output filters | a pinned no_std category crate (ADR-007 decisions 14 and 15) | `unicodedata.category` |
| Project and change ids | `uuid` with only the `v4` feature, in the adapters behind the existing id port, printed in the lowercase hyphenated form that `str(uuid.uuid4())` gives (`src/orqlet/adapters/system.py` lines 14-16); the randomness comes from the operating system | `uuid.uuid4` |
| Clock and timestamps | `std::time::SystemTime` read in the adapters behind the existing clock port; a domain function turns seconds and microseconds since the Unix epoch into the UTC date and the ISO 8601 text that `datetime.now(UTC).isoformat()` gives, with microseconds and `+00:00` (lines 9-11); no crate | `datetime` |
| `O_NOFOLLOW` | `libc`, Unix only, constants only | `os.O_NOFOLLOW` |
| Unified diff | `similar` (three lines of context), in the application crate | `difflib` |
| Globs | a per-segment matcher in the domain crate (`*`, `?`, `[...]`, `[!...]`), case-sensitive; no crate | `fnmatch.fnmatchcase` |
| Strict JSON | a checking reader over `serde_json` in the documents module (ADR-007 decision 4) | `domain/strict_json.py` |
| Regular expressions | `regex`; ASCII classes written as `[0-9]`; end of text written as `\z`. The engine behind 0.5.2's Pydantic patterns stays unknown (U-9), and the parity corpus covers the patterns in use (BC-4). Used only in the application crate; the adapters write their pattern checks by hand (the revision form, the `ls-files` short-option cluster and `rust-version`) | `re` and Pydantic patterns |
| Toolchain | `rust-toolchain.toml` pins 1.100.0 and lists the targets `x86_64-unknown-linux-gnu` and `x86_64-pc-windows-msvc` besides the macOS host `aarch64-apple-darwin`; the workspace sets `rust-version = "1.100"`. That this toolchain exists and has a stable `File::try_lock` was not looked up beyond `rust-std-file-lock.md`; the plan confirms both | Python 3.12 |
| Embedded workflow data | `include_dir` | `importlib.resources` |
| Data directory | `dirs::data_local_dir()` joined with `orqlet` | platformdirs |
| Apply lock | `std::fs::File::try_lock` on a file opened for reading and writing, not append-only, which Windows cannot lock (`rust-std-file-lock.md` item 4); polled for 10 s | filelock |
| Processes | `std::process::Command` with reader threads, kill on timeout or cap | `subprocess` |
| Rich output | none; the unwired presenter is not ported (Q-8) | Rich |

Where serde-saphyr's options apply to the read path, they are set to `max_documents: 1`, `max_aliases: 0`, `max_anchors: 0`, merge keys as errors, `reject_unsupported_tags`, duplicate keys as errors, `max_depth: 32` and `max_nodes: 50,000` (`serde-saphyr-options.md`), as a first barrier. `strict_booleans` is not used, because the generic tree applies 0.5.2's own boolean forms. The full rule set, and the strict JSON rules, are in ADR-007.

`digest_of` takes the domain type `CanonicalValue` (null, bool, integer within ±(2^53−1), string, array, object with string keys).

Exact versions are pinned in `Cargo.lock` and listed with `=` requirements in `[workspace.dependencies]`, as `pyproject.toml` pins today (A-1).

## Consequences

- Validation messages are Orqlet's own `location: rule` texts, never library text that could quote a value (ADR-007 decision 8; Q-6).
- `isoformat` drops the microseconds when they are zero; the domain function does the same, and its unit tests cover that case, a leap day and the end of a year.
- Every YAML document goes through the generic tree before serde turns it into a contract type (ADR-007 decision 3).
- The data directory may differ from the platformdirs location (U-10); 0.x journals under another data directory are not seen (ADR-004).
- Only serde-saphyr, schemars, clap, Clippy and `File::try_lock` were checked against their documentation here. The behaviour of the other crates in the table, including the exact folders of `dirs`, was not looked up; the plan confirms each from its documentation at the pinned version, and the parity corpus covers the globs and paths in use (BC-4).
- The glob matcher is about forty lines of domain code with its own tests instead of a dependency, which keeps the domain allow-list at three crates.

## Rejected alternatives

- `serde_yaml`, `yaml-rust2` or `saphyr` under the generic tree: the tree is Orqlet's either way, but serde-saphyr also documents budgets for documents, aliases, anchors, depth and nodes as a first barrier, and writes YAML (`serde-saphyr-options.md`).
- `chrono` or `time` for timestamps: one formatting function in the domain covers the single format in use. `getrandom` without `uuid`: the same randomness, plus code to format the id.
- `fs4` or `fd-lock` for the lock: the standard library provides `File::try_lock` on Unix and Windows (`rust-std-file-lock.md`), so no crate is needed.
- A `build.rs` table instead of `include_dir`: about the same size of code, but custom build logic to review and keep correct.
