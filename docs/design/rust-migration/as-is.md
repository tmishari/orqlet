---
schema: orqlet.as-is/v1
header:
  schema: orqlet.artifact-header/v1
  task: rust-migration
  status: approved
  workflow_version: 0.5.2
  protected_set_digest: 6a25aa85a870cd58ec812890ea6dded9f0e83c3b15e8f7bbb79eacb17546c808
  bound:
    base_revision: 319691422e5825f79028b192463af0fdc617b873
    standards_lock_hash: 8b2d28e1d4894236e4b43e3c54766fcbdfaba0c89aab9fe39645dfa7c8e43713
    applicable_rules_hash: 15dad7d04fe2bec92f1ca2d922802d58b960e532316f3298496ebcee9e5b43bd
    profile_version: 1
base_revision: 319691422e5825f79028b192463af0fdc617b873
scope:
  paths: ["src/orqlet/**", "tools/**", "pyproject.toml", "uv.lock", ".prompts/**", ".orqlet/**", "README.md", "AGENTS.md"]
  request_ref: rust-migration
research_mode: parallel-subagents
size_budget: {max_words: 1400}
facts:
  - id: A-1
    kind: structure
    statement: The package orqlet is built by hatchling 1.32.4, requires Python 3.12 or later, pins six runtime dependencies (typer 0.27.3, pydantic 2.14.1, PyYAML 6.0.3, filelock 4.2.4, platformdirs 4.13.5, rich 15.0.0) and declares the console script orqlet as orqlet.interface.cli.app:main.
    evidence:
      - {path: pyproject.toml, lines: 1-20, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 0a54daccca203b863f2f16c92fc408d99b1863689d098ccb46e2100522be4de3}
  - id: A-2
    kind: dependency
    statement: The dev group pins pytest, pytest-socket, hypothesis, import-linter, ruff, mypy and types-PyYAML.
    evidence:
      - {path: pyproject.toml, lines: 22-31, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 33bd486d8a753afe97cdb3d3758805b6dc3255fe2b899c8ef0639d325941aa27}
  - id: A-3
    kind: operation
    statement: The package version is read from the literal __version__ "0.5.2" in src/orqlet/__init__.py, and the wheel packages src/orqlet.
    evidence:
      - {path: pyproject.toml, lines: 33-37, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 7909c9c79a63dca0964ebc7e0d1741a94d9365389834fd4c40dbc420197968ea}
      - {path: src/orqlet/__init__.py, lines: '3', revision: 319691422e5825f79028b192463af0fdc617b873, sha256: c25981179035815b29b2464ea6a35ed178b5018e59458177f12315ddf45dfcb0}
  - id: A-4
    kind: structure
    statement: import-linter declares six contracts over Python module names, among them the layer order interface, adapters, application, domain and forbidden modules for domain and application.
    evidence:
      - {path: pyproject.toml, lines: 82-134, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 289e692f1ab3cb50b0dc13fc776d25d09d460b5f25ee32d2bc4458205808c31b}
  - id: A-5
    kind: interface
    statement: The Typer app registers nine commands (init, upgrade, rollback, sync, doctor, explain, release, status, hook) and ten groups (profile, resources, conventions, standards, validate, gate, evidence, knowledge, review, models), and python -m orqlet runs the same main.
    evidence:
      - {path: src/orqlet/interface/cli/app.py, lines: 32-57, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 795adc3e65fd2e4bebee8fd5fc29ae72a1efdbc22cc56c49905100c392b53730}
      - {path: src/orqlet/__main__.py, lines: 3-6, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 7b62fca1a2609ab004997e4379c591b1cb42f83b44df036a71ad44ffc2756ece}
  - id: A-6
    kind: interface
    statement: Every command result is an orqlet.cli-result/v1 envelope printed with --json as JSON with indent 2, sorted keys and ensure_ascii false, and otherwise as human text on stdout with each finding as one line of its code and message on stderr.
    evidence:
      - {path: src/orqlet/interface/cli/runner.py, lines: 28-51, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: f9df8dd75fc871ffbfdd5dd4c2aceef06974fd05c66a04adff84de41fc665397}
      - {path: src/orqlet/interface/cli/render_json.py, lines: 10-12, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 90cf4f941f76643b7f147373feefef7cb01ee468100593eb4fe5836990dd122a}
  - id: A-7
    kind: interface
    statement: Exit statuses are fixed (0 ok, 1 problems, 2 usage, 3 refused, 4 needs input, 5 check failed, 70 internal), and exception types map to ORQ-E1xx codes with ORQ-E900 for internal errors.
    evidence:
      - {path: src/orqlet/interface/cli/exit_codes.py, lines: 6-13, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 7791df275c1e871937147b962fc093a55d020c0d82a90d1526abdd0e1e48abe1}
      - {path: src/orqlet/interface/cli/errors.py, lines: 16-35, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 8130d3363293d6d0c2a56dcd47a72374ec3589f271c4f13023e06c095f331627}
  - id: A-8
    kind: interface
    statement: The CONTRACTS registry maps 35 schema ids, such as orqlet.as-is/v1 and orqlet.implementation-plan/v1, to Pydantic models.
    evidence:
      - {path: src/orqlet/application/contracts/__init__.py, lines: 39-75, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: ef7e18942215e337794a61e9c45363ab44bebeced92aaf824bfd1fbbde57d13a}
  - id: A-9
    kind: flow
    statement: digest_of is the lower-case hex SHA-256 of a subset of RFC 8785 canonical JSON in UTF-8, with keys sorted by UTF-16 code units, no whitespace, short escapes for a fixed set of characters, and floats, lone surrogates and integers beyond 2^53-1 refused.
    evidence:
      - {path: src/orqlet/domain/digest.py, lines: 1-8, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: e1cd660dd5732aa034c02ab72e2535eceb7f74bd19db9322f3d0fa49ec8f5068}
      - {path: src/orqlet/domain/digest.py, lines: 43-81, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 51cd496f3a70a8d5274e4ee6a9776a68fc6f87c974e2902b4a66a6b76ea6b31b}
  - id: A-10
    kind: flow
    statement: A line-range hash turns CRLF into LF, splits on LF, drops one trailing empty element and hashes the 1-based inclusive lines joined by LF without a final break.
    evidence:
      - {path: src/orqlet/domain/facts.py, lines: 19-33, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 813ef4c78e82c3fb2f2f00e4fa6e828f346f9c5187e70f337f1c36cb7ef9e768}
  - id: A-11
    kind: operation
    statement: The shipped JSON Schema text is Pydantic's model_json_schema with by_alias, dumped with indent 2, sorted keys, ensure_ascii false and one trailing newline, in a file named after the schema id.
    evidence:
      - {path: src/orqlet/application/contracts/schemas.py, lines: 10-18, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 6ebe78c40d6b52d4c457e3a2bec5efa3fc079cd4148f56b25a4c1ba17a26de74}
  - id: A-12
    kind: flow
    statement: Every contract is a frozen model that forbids extra keys, and a validation error is reported as "source, dotted location, Pydantic message" joined with "; " without the input value.
    evidence:
      - {path: src/orqlet/application/contracts/common.py, lines: 74-77, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 19836bc1ef2cc800af51b07c2c333dd7d70066500abb4d0e4157ae35a38737e6}
      - {path: src/orqlet/application/contracts/loading.py, lines: 11-27, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 8b4998b42e7e6fa75c3ff21e82f9a8e1ddd8b1ea72fa6fdbcf64005320a3a362}
  - id: A-13
    kind: flow
    statement: The strict YAML loader is built on PyYAML and limits input to 1 MiB, depth 32 and 50,000 nodes.
    evidence:
      - {path: src/orqlet/adapters/fs/yaml_loader.py, lines: 104-131, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: da7c122561753ba72167784a2c66bc6bf65e0acd00d467ec358287e64f2f56dc}
  - id: A-14
    kind: flow
    statement: Strict JSON refuses non-UTF-8 input, duplicate keys, NaN and Infinity, a non-object top level, oversized integers and deep nesting.
    evidence:
      - {path: src/orqlet/domain/strict_json.py, lines: 21-52, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 1e82edad8c16b62fb3cd7324936a1883af7bef5138e5062d5b83abdc3d8278a3}
  - id: A-15
    kind: structure
    statement: CanonicalPath normalises repository paths to NFC, compares them by casefold and NFC, and refuses empty, dot, control, backslash, colon, device-name and .git components.
    evidence:
      - {path: src/orqlet/domain/paths.py, lines: 17-48, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 534e2ae2d7e63be5ac75ce242433ff2a866601fa1de15d07b06879d49d4fc91b}
  - id: A-16
    kind: interface
    statement: The ProcessRunner port takes argv, a working folder, an exact environment, a timeout, an output limit and optional stdin, with no shell.
    evidence:
      - {path: src/orqlet/application/ports/process.py, lines: 32-44, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: a81b39cb03d90fb33618be0339368b7654e1ab214033fe2410669ca1864c6c42}
  - id: A-17
    kind: flow
    statement: GitRunner prefixes fixed config overrides, allows a fixed list of subcommands, and applies a 30 second timeout and a 16 MiB output cap by default.
    evidence:
      - {path: src/orqlet/adapters/git/git_runner.py, lines: 18-50, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: d17b43b2115241c8c6151c9d388e56a3e07af7d9ac51d384dd3092323c5d84f9}
  - id: A-18
    kind: flow
    statement: A child process keeps only an allow-listed set of environment variables.
    evidence:
      - {path: src/orqlet/adapters/process/environment.py, lines: 7-32, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 3113d772f2f5a7b9773dd855a0035f55b549192c853cbd1673fce8a16606c724}
  - id: A-19
    kind: flow
    statement: A file write goes to a temporary file in the same folder, is synced, replaced into place and followed by a folder sync.
    evidence:
      - {path: src/orqlet/adapters/fs/local_fs.py, lines: 126-149, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 03552e333a85c23176e6d43064452dc5e51f644cba58b29d798496757cf61a6b}
  - id: A-20
    kind: interface
    statement: A managed project stores per-file input and rendered hashes in .orqlet/generated.lock.yaml, and each managed block in AGENTS.md carries the hash of its normalised body in its begin marker.
    evidence:
      - {path: .orqlet/generated.lock.yaml, lines: 1-13, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 1360281e0f8a73ddaf9f4285a1439740d34b405ae529ebec0d4a02d599ae0ea2}
      - {path: src/orqlet/adapters/render/instructions.py, lines: 40-52, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 603121f555c0f722357b1c474e3e59a5030d990ef640d60a20422362a0199322}
  - id: A-21
    kind: flow
    statement: The workflow manifest records each bundled file's SHA-256 with CRLF read as LF, and identity.json sets workflow_version 0.5.2.
    evidence:
      - {path: src/orqlet/application/usecases/workflow_manifest.py, lines: 28-30, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: b372f48ed501d690817e81483187a80ac9f3ba76bc041419abbf44206e81c889}
      - {path: src/orqlet/workflow/identity.json, lines: 1-5, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 08401b074a07ffde7b0fad07d8e26807c340c9fbffc344e8968a37077f0f12fb}
  - id: A-22
    kind: operation
    statement: tools/build_manifest.py writes or checks src/orqlet/workflow/MANIFEST.json by importing orqlet application and adapter modules.
    evidence:
      - {path: tools/build_manifest.py, lines: 1-22, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 10001f64deaf7202ad71bff0f95baaf162dd19e23a231fe79cf924f88a878a5f}
  - id: A-23
    kind: structure
    statement: The bundled workflow files are read at run time through importlib.resources and served only when the manifest lists them.
    evidence:
      - {path: src/orqlet/adapters/workflow_package.py, lines: 24-45, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: c804fc7a5627cce4995f892caf50e4bcc64d5878e157a9490659dde111364e46}
  - id: A-24
    kind: flow
    statement: python_api reads a Python module's public API with Python's ast parser without running it.
    evidence:
      - {path: src/orqlet/domain/python_api.py, lines: 1-14, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 2f9f646f24675989ae582ec9e1ad54fc2c2dd4d02961599fab395cfae963acbd}
  - id: A-25
    kind: flow
    statement: apply_plan holds the apply lock, refuses a stale plan, backs up existing targets and journals each write, and the lock file is planned last with the standards lock hash.
    evidence:
      - {path: src/orqlet/application/usecases/apply_plan.py, lines: 49-65, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 882be86404d54626856d7c161128cb6821706ee20775ce49be413b5a24c3204e}
      - {path: src/orqlet/application/usecases/render_all.py, lines: 414-423, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: cb2911f05671e5bca4139a3c4bf16f28d2e4b9c63f43461c00c57cf3a43d4398}
  - id: A-26
    kind: dependency
    statement: The data directory is ORQLET_DATA_DIR or the platformdirs user data folder, and the apply lock is a filelock lock with a 10 second timeout.
    evidence:
      - {path: src/orqlet/interface/cli/wiring.py, lines: 83-93, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: c82afee17bf4a7a4616fb92682c8321b92e5710d4b4c36f402e7a7e77f6e60b7}
      - {path: src/orqlet/adapters/fs/apply_lock.py, lines: 14-33, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 49f9393203318edf183f3a6684fe54b724cc6ca02b3bcfe3a98ac2499a6957e8}
  - id: A-27
    kind: operation
    statement: The team standard for quality requires ruff, strict mypy and import-linter before a pull request is ready and says the project writes no tests until the person says otherwise.
    evidence:
      - {path: .prompts/rules.yaml, lines: 103-128, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: b8d3c9b0e8644f5ea3c5bde8e8ece0acb5a110b3aa097ca0694df61b5263b310}
  - id: A-28
    kind: operation
    statement: README.md requires Python 3.12 and uv and installs Orqlet with uv tool install or uvx.
    evidence:
      - {path: README.md, lines: 76-97, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 5760b45240582a52eb229eafe6b5453ee2e9f48278cfebff752bc01a87d1b5ae}
  - id: A-29
    kind: structure
    statement: The project profile records project kind python-cli, Python 3.12 and the package manager uv.
    evidence:
      - {path: .orqlet/project-profile.yaml, lines: 1-34, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: e68fb82f7e53475e950bdc1e37bc00a0077b11c1a556367872c922ccad549b0e}
  - id: A-30
    kind: test
    statement: AGENTS.md records the person's instruction of 2026-11-25 to write and run no tests until the person says otherwise.
    evidence:
      - {path: AGENTS.md, lines: 100-106, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 415faa662b38fdb40a53d85437f3622562c3e9e3b7ed24afb5cfb7cb05ec6112}
  - id: A-31
    kind: operation
    statement: The work status rests on the person's instruction of 2026-11-23 to freeze unfinished work.
    evidence:
      - {path: docs/design/work-status.md, lines: 1-20, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: b1e29c08be9bdfce19f7933cfed053e44ad66d664cae30901b7288310bfef220}
  - id: A-32
    kind: flow
    statement: gate status binds HEAD, the CRLF-normalised hash of the standards lock, its stored applicable rules hash and a canonical digest of the protected files.
    evidence:
      - {path: src/orqlet/application/usecases/gate_status.py, lines: 71-94, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 33755d0d66dcfd7085f72752da09cf6eb61899519f8d616dd6ae9818a95a5d25}
  - id: A-33
    kind: flow
    statement: Glob matching is done by fnmatch.fnmatchcase per path segment, and the diffs printed for changed files come from difflib.unified_diff with three lines of context.
    evidence:
      - {path: src/orqlet/domain/globs.py, lines: 8-21, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 6b617ce49447255dbe470de8ca745fc5e667707811a3abf76637d96f45061075}
      - {path: src/orqlet/domain/changeplan.py, lines: 443-452, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 25b0522d28837c372c76a0f0d6ecd0df1ce5082b9a6106dec1cf3c9e5a0ffdf4}
  - id: A-34
    kind: flow
    statement: An artifact file is refused above 512 KiB and is decoded as UTF-8 with its BOM stripped and CRLF read as LF before its front matter is parsed.
    evidence:
      - {path: src/orqlet/application/usecases/validation.py, lines: 94-104, revision: 319691422e5825f79028b192463af0fdc617b873, sha256: 9e2664785fc2199cb39a5a0ca08445159129ff57ed855d3968ca8f021ff07005}
unknowns:
  - {id: U-1, what: "Whether hashes, emitted YAML and JSON and generated files must stay byte-identical for projects set up by the Python release", material: true, question_ref: Q-5}
  - {id: U-2, what: "Whether library-sourced message text (PyYAML, Pydantic, Click and Typer help) must stay word for word", material: true, question_ref: Q-6, merged_from: [rust-migration-flows/U-4, inventory-adapters-interface/U-3]}
  - {id: U-3, what: "Whether Python API extraction and the Python project kinds are kept", material: true, question_ref: Q-7}
  - {id: U-4, what: "Whether unwired code (install and uninstall presenter, user scope, Copilot adapter) is ported", material: true, question_ref: Q-8, merged_from: [inventory-adapters-interface/U-2]}
  - {id: U-5, what: "What builds MANIFEST.json and what is the source of the JSON Schemas once the Python tooling is removed", material: true, question_ref: Q-9, merged_from: [workflow-package-data/U-5]}
  - {id: U-6, what: "Who approves replacing the Python-named standards, profile and README text and in which task", material: true, question_ref: Q-10}
  - {id: U-7, what: "The exact bytes of the YAML and front-matter emitter in src/orqlet/adapters/render/emit.py were not traced", material: true, merged_from: [rust-migration-flows/U-2, workflow-package-data/U-6, rust-migration-domain-application/U-5]}
  - {id: U-8, what: "The Unicode database version behind casefold, NFC and character categories depends on the unpinned Python runtime", material: true, merged_from: [rust-migration-domain-application/U-6]}
  - {id: U-9, what: "Which regex engine Pydantic 2.14.1 uses for pattern constraints, which decides how digit classes and end anchors match", material: true, merged_from: [rust-migration-domain-application/U-3]}
  - {id: U-10, what: "The platformdirs user data folder on each operating system is not recorded in the repository", material: true, merged_from: [inventory-adapters-interface/U-4]}
  - {id: U-11, what: "The human-readable renderers and the use of stderr per command were not traced", material: true, merged_from: [rust-migration-flows/U-6]}
  - {id: U-12, what: "releases.json records only release 0.1.0 while the manifest is 0.5.2", material: false, merged_from: [workflow-package-data/U-3]}
  - {id: U-13, what: "The flags of each command beyond root and json were not listed", material: false, merged_from: [inventory-adapters-interface/U-5]}
contradictions:
  - {id: C-1, sources: ["src/orqlet/interface/cli/render_rich.py:1-5", "src/orqlet/interface/cli/app.py:39-57"], note: render_rich.py calls itself the presenter of install and uninstall but the app registers neither command, merged_from: [inventory-adapters-interface/C-1]}
  - {id: C-2, sources: ["src/orqlet/interface/cli/commands/hook.py:23-27", "src/orqlet/adapters/clients/copilot.py:1-4"], note: The hook accepts the client copilot while the Copilot adapter is empty and unwired, merged_from: [inventory-adapters-interface/C-3]}
  - {id: C-3, sources: ["README.md:78", "AGENTS.md:75-77"], note: README describes a CI workflow that AGENTS.md records as removed, merged_from: [build-and-tooling/BC-1]}
  - {id: C-4, sources: ["pyproject.toml:69-71", "tools/build_manifest.py:6-8"], note: pytest and a tool docstring name a tests folder that does not exist, merged_from: [build-and-tooling/BC-2, build-and-tooling/BC-3]}
  - {id: C-5, sources: [".prompts/rules.yaml:4-6", ".prompts/rules.yaml:122-128"], note: The standards header names CI while the quality rule says there is no CI workflow, merged_from: [build-and-tooling/BC-4]}
  - {id: C-6, sources: [".orqlet/project-profile.yaml:171-172", ".orqlet/versions.yaml:3-6"], note: The profile records Orqlet 0.1.0 while versions.yaml pins 0.5.2, merged_from: [build-and-tooling/BC-6]}
  - {id: C-7, sources: ["src/orqlet/application/usecases/render_all.py:419", "src/orqlet/application/usecases/gate_status.py:89"], note: The lock stores a plain SHA-256 of the standards lock while gate status hashes it with CRLF read as LF, merged_from: [rust-migration-flows/C-2]}
  - {id: C-8, sources: ["docs/design/rust-migration/questions.yaml:Q-3", "AGENTS.md:100-106"], note: The person lifted the no-tests rule for this task while AGENTS.md and the quality standard still say no tests are written}
self_check:
  schema: orqlet.self-check/v1
  checked_against:
    role: researcher
    phase: research
    confirmed_requirements: [Q-1, Q-2, Q-3, Q-4, Q-5, Q-6, Q-7, Q-8, Q-9, Q-10]
    applicable_standards:
      - "src/orqlet applicable_rules_hash 230f5f5872a9449d6cc62ed7a777f188df18223adb281809121bb83550a49a4f"
      - "pyproject.toml applicable_rules_hash 09024bca0bb6e4809695c1c5d93c61005339657137b0aa2f924fd7f9648f6931"
  checks:
    - {what: ledger is valid, how: "orqlet validate ledger docs/design/rust-migration/questions.yaml", result: pass}
    - {what: every fact cites the base revision with a hash, how: "orqlet evidence cite --revision 319691422e5825f79028b192463af0fdc617b873 (48 pairs)", result: pass}
    - {what: line ranges match the statements, how: "spot check of yaml_loader.py 104-112, rules.yaml 120-128, app.py 39-57", result: pass}
    - {what: AS-IS file is valid, how: "orqlet validate as-is docs/design/rust-migration/as-is.md", result: pass}
    - {what: the person accepted the AS-IS file, how: "tmishari at 2026-11-25T11:58:00+00:00 answered 'Yes, I accept it'", result: pass}
  unverified:
    - The five research subagents ran without a shell; their line ranges were cited by the main agent and spot-checked, not all re-read.
    - No web lookup was made for Rust, Cargo or Rust crates; the request names Rust and no registered resource covers it.
    - Fragments were merged in memory and not kept as files.
---

## Request

"Take all my current code base and migrate it to Rust, remove irrelevant files, and after migration remove all old data." The person chose a new gated task (Q-1), removal of only the Python code and tooling with git history kept (Q-2), Rust tests for this task (Q-3) and a cargo-built native binary (Q-4).

## Scope

Covered: the Python package under src/orqlet (domain, application, adapters, interface and the bundled workflow data), tools/, the build manifest and lock, the team standards, the project profile, README and AGENTS.md. Left out: docs/design records of other tasks, the generated client folders, the YAML emitter (U-7) and the human-readable renderers (U-11).

## Existing capabilities and behaviour

- One Python 3.12 CLI with nine commands and ten groups, built on Typer, Pydantic, PyYAML, filelock, platformdirs and Rich (A-1, A-5).
- Four layers checked by import-linter (A-4); ports isolate processes and Git (A-16, A-17, A-18).
- A fixed result envelope, JSON settings and exit statuses (A-6, A-7).
- 35 schema-checked artifact types with closed models and Pydantic-worded errors (A-8, A-12), read by a strict YAML loader and strict JSON (A-13, A-14, A-34).
- Stored hashes: canonical JSON digests, line-range hashes, manifest hashes, lock hashes and block markers (A-9, A-10, A-20, A-21, A-32).
- Journalled, atomic, locked writes under a data directory (A-19, A-25, A-26).
- Bundled workflow data located through importlib.resources, with a manifest built by a Python tool and schemas generated from the Pydantic models (A-11, A-22, A-23).
- Python-specific features: Python API extraction and Python standard-library matching and diffs (A-24, A-33).
- Python-named project context: the quality standard, README install steps, the project profile and the no-tests instruction (A-27, A-28, A-29, A-30).

## Inferences

- I-1 Projects set up by the Python release hold hashes that depend on byte-level details of four functions (A-9, A-10, A-20, A-21). Running the Python and the Rust digest on the same inputs would confirm which bytes differ.
- I-2 Three runtime dependencies define observable text: Pydantic error wording, PyYAML error wording and Typer help (A-1, A-12, A-13). A sample of validation failures from each would confirm the extent.
- I-3 The schema files and the manifest have no source left once the Python tooling is removed (A-11, A-22, Q-2). The file list of tools/ and the schema directory would confirm it.
- I-4 Removing the Python tooling leaves the quality standard, README, profile and AGENTS.md describing tools that no longer exist (A-27, A-28, A-29, A-30). A search for ruff, mypy and uv after removal would confirm it.

## Open questions

U-1 to U-6 wait for the person (Q-5 to Q-10). U-7 to U-13 are research gaps without a question. C-1 to C-8 are recorded contradictions.

## Inputs for design

Facts A-1 to A-34; unknowns U-1 to U-13; contradictions C-1 to C-8; the ledger answers Q-1 to Q-4 and the open Q-5 to Q-10.
