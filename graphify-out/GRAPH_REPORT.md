# Graph Report - src  (2026-11-20)

## Corpus Check
- 269 files · ~137,578 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 1 file(s) not represented in the graph (top: .typed 1)

## Summary
- 3174 nodes · 11061 edges · 125 communities (89 shown, 36 thin omitted)
- Extraction: 82% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 2028 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Python API & Dependency AST
- Client Instruction Adapters
- Binding Inputs & Plans
- Design Set Contracts
- Standards Pack Resolver
- Diagnose & Personal Items
- Policy Validation & Hashing
- Init Files & Generated Lock
- Validate CLI Commands
- Technology Scanners
- Role Bindings & Render All
- Lifecycle CLI & Doctor
- Review Identity & Independence
- Artifact Header & Review Result
- Resources Contract & View
- Profile Facts & Init Questions
- Upgrade & Rollback
- Contract Loading & Pin Staleness
- Plan & Question Ledger Validation
- Model Effort Assignment
- Models Resolve & Capabilities
- Model Policy Selection
- Resources Editing
- Model Identity Catalog
- Workflow Sources & Seeds
- Ancestor Finder & Wiring
- Scoped FS & Backups
- VCS Port & Staleness
- Init Project & Prompter
- Change Class & Design Scope
- Model Policy YAML Seed
- Knowledge Impact
- Managed Blocks & Drift
- Change Journal & Apply Plan
- Packaged Workflow
- Local File System
- Python Scanner & Known Tech
- Resource Credential Checks
- Conventions Check
- Git VCS Adapter
- Scanner Port & Discover
- Render Request Model
- Init Command & CLI Result
- PR Template Rendering
- Gate Status & Workflow Lock
- Plan Tree Projection
- AS-IS Validation
- Change Plan Builder
- YAML Loader
- Integrations Validation
- FS Journal & Schemas
- Models CLI Command
- Evidence Citation
- Process Runner Support
- Design & Research Skills
- Model Policy Contract
- Resources CLI Command
- Front Matter Emitter
- Workflow Rules & Doctor Doc
- Review Skill & Reviewer Roles
- Tester & Inventory Roles
- Ancestor & ID Ports
- System Clock & UUIDs
- Design Format Reference
- Drift Findings & Explain
- Git Runner & Objects
- Git Commit Parsing
- Integrations Source Loader
- Resources Validation
- Orqlet Baseline Rules
- Design Phase Contract
- Exempt Change Classes
- MCP Credential Detection
- Profile CLI Command
- Standards & Foundations Docs
- AS-IS Format Reference
- MCP Server Contract
- Model Policy Loading
- Implement Phase Contract
- Canonical Digest
- MCP File Rendering
- Evidence CLI Command
- Gate CLI Command
- Security Reviewer Role
- Environment Scrubbing
- Front Matter Diff
- Knowledge CLI Command
- Plan Format Reference
- Onboard Skill
- TTY Prompter
- Plan Phase Contract
- Integrations Registry
- PR Workflow Section
- Personal Names Scanner
- Policy Credential Scan
- Skill & Rule Templates
- Workflow Manifest
- Workflow Rule Metadata
- Repo State
- Tree Diff
- Duplicate Key Error
- Prompts Rules YAML
- Human Summary Counts

## God Nodes (most connected - your core abstractions)
1. `CanonicalPath` - 231 edges
2. `Contract` - 200 edges
3. `Finding` - 146 edges
4. `Collector` - 131 edges
5. `FileSystem` - 126 edges
6. `ValidateServices` - 113 edges
7. `Severity` - 96 edges
8. `FileKind` - 95 edges
9. `Services` - 82 edges
10. `FileSystemError` - 70 edges

## Surprising Connections (you probably didn't know these)
- `A check reported NOT RUN is not passed` --semantically_similar_to--> `Verify with evidence; a check not run is never reported as passed`  [INFERRED] [semantically similar]
  orqlet/workflow/commands/doctor.md → orqlet/workflow/baseline/baseline.md
- `Workflow non-negotiables (no guessing, four phases, required roles, not run is not success)` --semantically_similar_to--> `Four-phase workflow (research, design, plan, implementation)`  [INFERRED] [semantically similar]
  orqlet/workflow/seeds/prompts/foundations.md → orqlet/workflow/baseline/baseline.md
- `Ask the user for each open fact; never invent a value` --semantically_similar_to--> `No-guessing principle (unknown becomes a question)`  [INFERRED] [semantically similar]
  orqlet/workflow/commands/profile.md → orqlet/workflow/baseline/baseline.md
- `Workflow non-negotiables (no guessing, four phases, required roles, not run is not success)` --semantically_similar_to--> `No-guessing principle (unknown becomes a question)`  [INFERRED] [semantically similar]
  orqlet/workflow/seeds/prompts/foundations.md → orqlet/workflow/baseline/baseline.md
- `Workflow non-negotiables (no guessing, four phases, required roles, not run is not success)` --semantically_similar_to--> `Verify with evidence; a check not run is never reported as passed`  [INFERRED] [semantically similar]
  orqlet/workflow/seeds/prompts/foundations.md → orqlet/workflow/baseline/baseline.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Orqlet delegated role definitions (inventory, tracer, tester, architecture reviewer, security reviewer)** — orqlet_workflow_roles_orqlet_inventory, orqlet_workflow_roles_orqlet_tracer, orqlet_workflow_roles_orqlet_tester, orqlet_workflow_roles_orqlet_arch_reviewer, orqlet_workflow_roles_orqlet_security_reviewer [INFERRED 0.85]
- **Design change class tiers (D1, D2, D3 and effective class rule)** — orqlet_workflow_skills_orqlet_design_references_design_format_d1_delta, orqlet_workflow_skills_orqlet_design_references_design_format_d2_standard, orqlet_workflow_skills_orqlet_design_references_design_format_d3_full, orqlet_workflow_skills_orqlet_design_references_design_format_effective_class [EXTRACTED 1.00]
- **Safe command execution controls (warning list, placeholders, secret files, quoted values, no run on a file's word)** — orqlet_workflow_skills_orqlet_design_references_phase_contract_warning_list, orqlet_workflow_skills_orqlet_design_references_phase_contract_no_credentials, orqlet_workflow_skills_orqlet_design_references_phase_contract_secret_files, orqlet_workflow_skills_orqlet_design_references_phase_contract_values_from_artifacts, orqlet_workflow_skills_orqlet_design_references_phase_contract_never_on_a_files_word, orqlet_workflow_roles_orqlet_tester_plan_named_test_command [INFERRED 0.85]
- **Identical phase contract installed per skill (research, plan, implement)** — orqlet_workflow_skills_orqlet_research_references_phase_contract, orqlet_workflow_skills_orqlet_plan_references_phase_contract, orqlet_workflow_skills_orqlet_implement_references_phase_contract [INFERRED 0.95]
- **Templates rendered with a lines placeholder** — orqlet_workflow_templates_catalogue_skill, orqlet_workflow_templates_conventions_block, orqlet_workflow_templates_resource_rule, orqlet_workflow_templates_tool_skill [EXTRACTED 1.00]
- **Research, design, plan, implement phase chain** — orqlet_workflow_skills_orqlet_research_skill, orqlet_workflow_skills_orqlet_design_skill, orqlet_workflow_skills_orqlet_plan_skill, orqlet_workflow_skills_orqlet_implement_skill [EXTRACTED 1.00]
- **Independent packet-only review of a staged phase** — orqlet_workflow_skills_orqlet_review_skill, orqlet_workflow_roles_orqlet_code_reviewer, orqlet_workflow_roles_orqlet_arch_reviewer, orqlet_workflow_skills_orqlet_review_skill_review_packet, orqlet_workflow_skills_orqlet_review_references_review_format_review_record [EXTRACTED 1.00]
- **Project command provenance from onboard to plan checks** — orqlet_workflow_skills_orqlet_onboard_skill_recorded_commands, orqlet_workflow_skills_orqlet_plan_skill, orqlet_workflow_skills_orqlet_plan_references_plan_format_completion_entry, orqlet_workflow_skills_orqlet_implement_skill_implementation_report [INFERRED 0.85]

## Communities (125 total, 36 thin omitted)

### Community 0 - "Python API & Dependency AST"
Cohesion: 0.05
Nodes (64): _dependencies(), evaluate_expected_changes(), ExpectedChangeReport, _lock_delta(), _merge(), _module_name(), _parse(), public_api_delta() (+56 more)

### Community 1 - "Client Instruction Adapters"
Cohesion: 0.07
Nodes (45): ClaudeCodeAdapter, _mcp_file(), _optional(), CodexAdapter, CursorAdapter, _optional(), normalise_text(), agents_block() (+37 more)

### Community 2 - "Binding Inputs & Plans"
Cohesion: 0.06
Nodes (51): KnowledgeImpact, ImplementationPlan, is_excluded(), BindingRequest, change_set(), _changed_file(), components_as_data(), compute_components() (+43 more)

### Community 3 - "Design Set Contracts"
Cohesion: 0.04
Nodes (60): Contract, Consideration, Considerations, DesignChangeClass, DesignReview, DesignScope, ExpectedAfter, ExtractorConfig (+52 more)

### Community 4 - "Standards Pack Resolver"
Cohesion: 0.05
Nodes (35): DirectoryPackSource, PackManifest, Rule, RuleFile, LoadedPack, PackError, StandardsSource, resolve_for() (+27 more)

### Community 5 - "Diagnose & Personal Items"
Cohesion: 0.07
Nodes (45): PersonalItem, PersonalNames, _answer_of(), _convention_findings(), _copies_without_an_entry(), _diagnose(), Diagnosis, doctor() (+37 more)

### Community 6 - "Policy Validation & Hashing"
Cohesion: 0.06
Nodes (38): _repository_path(), file_hashes(), _write(), _is_absent(), validate_integrations(), _with_printable_path(), _absent(), _agent_files() (+30 more)

### Community 7 - "Init Files & Generated Lock"
Cohesion: 0.07
Nodes (38): BlockMarkers, GeneratedLock, GeneratorInfo, LockedFile, LockInput, StandardsLock, Versions, Released (+30 more)

### Community 8 - "Validate CLI Commands"
Cohesion: 0.08
Nodes (20): AsIsOptions, RecordOptions, main(), root(), _show_version(), action(), as_is_command(), design_command() (+12 more)

### Community 9 - "Technology Scanners"
Cohesion: 0.07
Nodes (27): at(), evidence_at(), evidence_matching(), read_source(), scope_text(), Source, image_version(), Known (+19 more)

### Community 10 - "Role Bindings & Render All"
Cohesion: 0.07
Nodes (26): Binding, MinimumCapability, RoleBindings, LockedPack, CliVersions, WorkflowVersions, FileKind, to_desired() (+18 more)

### Community 11 - "Lifecycle CLI & Doctor"
Cohesion: 0.10
Nodes (38): UpgradeResult, _diagnose_command(), action(), doctor_command(), _entry_out(), explain_command(), action(), findings_out() (+30 more)

### Community 12 - "Review Identity & Independence"
Cohesion: 0.07
Nodes (31): AgentBinding, CoderBinding, PolicyAbsent, assess_identity(), closed_warning(), _codex_findings(), _differ(), _excluded_finding() (+23 more)

### Community 13 - "Artifact Header & Review Result"
Cohesion: 0.06
Nodes (22): ArtifactHeader, Bound, Specialist, Upstream, AsIsScope, Contradiction, Fact, FactEvidence (+14 more)

### Community 14 - "Resources Contract & View"
Cohesion: 0.07
Nodes (24): AppliesTo, Resource, Resources, _rules(), StoredCopy, _answer(), _capped(), _catalogue_line() (+16 more)

### Community 15 - "Profile Facts & Init Questions"
Cohesion: 0.09
Nodes (35): FactValue, Clients, Facts, OrqletPin, ProfileMeta, ProjectInfo, ProjectProfile, PullRequests (+27 more)

### Community 16 - "Upgrade & Rollback"
Cohesion: 0.08
Nodes (28): stale_review_finding(), Composition, plan_changes(), _confirmed(), _project_id(), _refused(), _reversals(), rollback() (+20 more)

### Community 17 - "Contract Loading & Pin Staleness"
Cohesion: 0.08
Nodes (17): load_contract(), DocumentError, DocumentLoader, ApplyBusy, _agent_file(), _names(), _read(), _review_records() (+9 more)

### Community 18 - "Plan & Question Ledger Validation"
Cohesion: 0.10
Nodes (33): Phase, Question, QuestionLedger, _check_ledger(), blocking_questions(), _check_ids(), _check_keys(), _check_references() (+25 more)

### Community 19 - "Model Effort Assignment"
Cohesion: 0.09
Nodes (10): _assignment(), AssignmentInput, Choice, _Evaluated, _Level, _outcome(), ProfileInput, Rejection (+2 more)

### Community 20 - "Models Resolve & Capabilities"
Cohesion: 0.08
Nodes (23): ModelEntry, _also_known_as(), _answer(), _choice(), _first_by_id(), _hint(), _listed(), _listed_choice() (+15 more)

### Community 21 - "Model Policy Selection"
Cohesion: 0.09
Nodes (28): ModelPolicy, _by_client(), _can_lack(), _duplicate_ids(), _exclusion_problems(), _Gap, _lacked(), _missing() (+20 more)

### Community 22 - "Resources Editing"
Cohesion: 0.11
Nodes (27): add_resource(), attach_copy(), _checked(), _commit(), _confirmed(), _copy_bytes(), _copy_refusal(), CopySpec (+19 more)

### Community 23 - "Model Identity Catalog"
Cohesion: 0.09
Nodes (25): _catalog(), CatalogEntry, CatalogRoute, _claimed(), ExclusionRule, family_of(), _folded(), _glob() (+17 more)

### Community 24 - "Workflow Sources & Seeds"
Cohesion: 0.09
Nodes (17): workflow_block(), model_policy_seed(), seed_files(), _file(), WorkflowSource, _workflow_names(), _commands(), _workflow_names() (+9 more)

### Community 25 - "Ancestor Finder & Wiring"
Cohesion: 0.06
Nodes (14): FsAncestorFinder, FileApplyLock, StrictYamlLoader, Stores, StandardsQuery, _data(), standards_for_command(), action() (+6 more)

### Community 26 - "Scoped FS & Backups"
Cohesion: 0.08
Nodes (5): FsBackupStore, ScopedFileSystem, _remove_emptied_folders(), _Redirected, CanonicalPath

### Community 27 - "VCS Port & Staleness"
Cohesion: 0.06
Nodes (4): TreeFile, Vcs, _by_path(), changed_in_scope()

### Community 28 - "Init Project & Prompter"
Cohesion: 0.11
Nodes (23): PullRequestTemplate, Prompter, Question, choose_pr_targets(), discover_pr_templates(), _answer(), _approved(), _draft_and_ask() (+15 more)

### Community 29 - "Change Class & Design Scope"
Cohesion: 0.11
Nodes (25): DesignArtifact, ExpectedChange, change_policy(), change_scope(), _check_artifact_text(), _check_artifacts(), _check_as_is_ref(), _check_class() (+17 more)

### Community 30 - "Model Policy YAML Seed"
Cohesion: 0.05
Nodes (41): approval_ref, approved_by, state, assignments, mode, profile, target, client (+33 more)

### Community 31 - "Knowledge Impact"
Cohesion: 0.11
Nodes (27): DesignSet, DocsMap, KnowledgeConfig, ModuleCard, ChangeSet, read_knowledge_config(), analyse(), add() (+19 more)

### Community 32 - "Managed Blocks & Drift"
Cohesion: 0.09
Nodes (20): _state_of(), Block, BlockError, BlockItem, decode_utf8(), detect_newline(), find_block(), _heading_end() (+12 more)

### Community 33 - "Change Journal & Apply Plan"
Cohesion: 0.08
Nodes (9): BackupStore, ChangeJournal, JournalEntry, ApplyLock, apply_plan(), ApplyResult, _entry(), PlanStale (+1 more)

### Community 34 - "Packaged Workflow"
Cohesion: 0.09
Nodes (13): PackagedWorkflow, ExemptClass, ExemptClasses, ManifestEntry, ReleaseHistory, ReleaseRecord, WorkflowIdentity, WorkflowManifest (+5 more)

### Community 35 - "Local File System"
Cohesion: 0.15
Nodes (8): _classify(), _is_link(), LocalFileSystem, _replace_with_retry(), FileSystemError, LinkRefused, NotARegularFile, PathNotFound

### Community 36 - "Python Scanner & Known Tech"
Cohesion: 0.17
Nodes (16): lookup(), normalize_name(), Technology, _evidence_at(), _evidence_matching(), _get(), _is_web(), PythonScanner (+8 more)

### Community 37 - "Resource Credential Checks"
Cohesion: 0.09
Nodes (22): _aws_key_id(), _credential_key(), credential_problems(), _decode(), _escapes_are_valid(), glob_problems(), _host_problems(), _is_hex_pair() (+14 more)

### Community 38 - "Conventions Check"
Cohesion: 0.12
Nodes (16): _base(), _check(), _check_branch(), check_conventions(), _check_subjects(), ConventionsRequest, _patterns(), _profile_at() (+8 more)

### Community 40 - "Scanner Port & Discover"
Cohesion: 0.09
Nodes (10): Technology, ProjectScanner, TechnologyScanner, _children(), _directories(), discover_technologies(), Discovery, _ordered() (+2 more)

### Community 41 - "Render Request Model"
Cohesion: 0.12
Nodes (17): WorkflowRuleMeta, ClientSkill, ConventionsView, ModelSetting, ScopedRule, ModelSelection, build_render_request(), _checked() (+9 more)

### Community 42 - "Init Command & CLI Result"
Cohesion: 0.12
Nodes (14): CliResult, FindingOut, _answers(), _clients(), _exit_code(), init_command(), action(), _inside() (+6 more)

### Community 43 - "PR Template Rendering"
Cohesion: 0.11
Nodes (7): markers(), provision(), team_block(), PackagedRenderers, BlockSpec, FileRenderers, TeamTemplate

### Community 44 - "Gate Status & Workflow Lock"
Cohesion: 0.14
Nodes (17): WorkflowLock, _design_digest(), _standards_digest(), _assess(), _base_moved(), BoundValues, _check_expected(), _check_task() (+9 more)

### Community 45 - "Plan Tree Projection"
Cohesion: 0.18
Nodes (25): _base_tree(), _blocked_by_link(), _check_against_projection(), _check_concurrent(), _check_create(), _check_existing(), _check_inside_phase(), _check_move() (+17 more)

### Community 46 - "AS-IS Validation"
Cohesion: 0.15
Nodes (18): AsIsArtifact, AsIsFragment, knowledge_impact(), _check_against(), _check_consistency(), _check_fragments(), _check_ids(), _check_language() (+10 more)

### Community 47 - "Change Plan Builder"
Cohesion: 0.16
Nodes (13): seeded(), _block_item(), build_plan(), _Builder, Desired, normalised_hash(), PlannedItem, PlannedWrite (+5 more)

### Community 48 - "YAML Loader"
Cohesion: 0.08
Nodes (3): _Constructor, _Loader, _Resolver

### Community 49 - "Integrations Validation"
Cohesion: 0.13
Nodes (17): _check_document(), _check_file(), _compare(), _encodable(), _entries(), _error(), _no_duplicates(), _parse() (+9 more)

### Community 50 - "FS Journal & Schemas"
Cohesion: 0.15
Nodes (9): _decode(), _encode(), FsChangeJournal, _project_dir(), schema_filename(), schema_text(), JournalError, JournalRecord (+1 more)

### Community 51 - "Models CLI Command"
Cohesion: 0.14
Nodes (14): TargetKind, _breach(), _check_usage(), _choices_line(), _output(), _profile_line(), _rejected_line(), _require() (+6 more)

### Community 52 - "Evidence Citation"
Cohesion: 0.16
Nodes (12): cite(), _web_evidence_refused(), _check_evidence(), _report_status(), _check_evidence(), _check_quotes(), check_reference(), EvidenceRef (+4 more)

### Community 53 - "Process Runner Support"
Cohesion: 0.17
Nodes (7): _drain(), _feed(), SubprocessRunner, OutputLimitExceeded, ProcessError, ProcessResult, ProcessTimeout

### Community 54 - "Design & Research Skills"
Cohesion: 0.13
Nodes (20): orqlet-pr-writer role, PR title and description rules, orqlet-design skill, ADR (Context, Decision, Consequences, Rejected alternatives), Design brief, Design manifest (manifest.yaml), expected_changes for watched surfaces, orqlet-implement skill (+12 more)

### Community 55 - "Model Policy Contract"
Cohesion: 0.11
Nodes (11): Approval, Assignment, ClientModels, Documented, Evaluated, Exclusion, ListPrice, _one_entry_per_client() (+3 more)

### Community 56 - "Resources CLI Command"
Cohesion: 0.19
Nodes (7): _add(), _attach(), _list(), _remove(), resources_group(), _services(), _update()

### Community 57 - "Front Matter Emitter"
Cohesion: 0.17
Nodes (15): Data, _document(), _emit_container(), front_matter(), _is_container(), _is_plain_safe(), quote(), Scalar (+7 more)

### Community 58 - "Workflow Rules & Doctor Doc"
Cohesion: 0.11
Nodes (21): Generated files policy (.orqlet/generated.lock.yaml), Command doc: orqlet doctor, Findings report (errors, warnings, notes with finding codes), orqlet doctor, Command doc: fill in project profile open facts, Ask the user for each open fact; never invent a value, Finding ORQ-W181 (open profile facts), orqlet profile answer (--dry-run / --yes) (+13 more)

### Community 59 - "Review Skill & Reviewer Roles"
Cohesion: 0.15
Nodes (20): orqlet-arch-reviewer role, Architecture review checks, Design review mode (no packet), orqlet-code-reviewer role, Design reviewer notes (D2+), Knowledge step (orqlet knowledge impact), Rework round (max three), review_evidence roles (+12 more)

### Community 60 - "Tester & Inventory Roles"
Cohesion: 0.13
Nodes (19): Role output contract and phase restriction win over baseline advice, Role: Repository inventory researcher (orqlet-inventory), Area mapping (structure, entry points, configuration, tests, dependencies, workflows), orqlet.as-is-fragment/v1 (facts, unknowns, contradictions), Role: Tester (orqlet-tester), Characterization tests derived from AS-IS facts (expected to pass at once), Coder role (receives handed-back checks), expected_behavior_source citation on every test (+11 more)

### Community 61 - "Ancestor & ID Ports"
Cohesion: 0.13
Nodes (3): AncestorFinder, Clock, IdGenerator

### Community 62 - "System Clock & UUIDs"
Cohesion: 0.12
Nodes (3): SystemClock, UuidGenerator, prepare_command()

### Community 63 - "Design Format Reference"
Cohesion: 0.15
Nodes (16): Design format reference: the design set, Acceptance criteria BC-n with sources (R-n, Q-n, A/U/C entries, ADR, standard id), ADR (Context, Decision, Consequences, Rejected alternatives), Change classes D1, D2, D3, Required artifacts per change class, D1 (Delta): single module, no public interface change, at most 10 files, D2 (Standard): neither D1 nor D3, D3 (Full): trust boundary, auth, crypto, secrets, data model, infrastructure, cross-service contract (+8 more)

### Community 64 - "Drift Findings & Explain"
Cohesion: 0.18
Nodes (8): Drift, measure_drift(), explain(), Explanation, resources_path(), combine(), is_success(), Verdict

### Community 65 - "Git Runner & Objects"
Cohesion: 0.23
Nodes (4): GitRunner, _parse_batch(), read_blobs(), VcsError

### Community 66 - "Git Commit Parsing"
Cohesion: 0.15
Nodes (5): _parse_commit_batch(), _subject_of(), check_exclusions(), check_ref_name(), CommitSummary

### Community 67 - "Integrations Source Loader"
Cohesion: 0.22
Nodes (7): _error(), load_integrations(), parse_integrations(), _problem(), _scan(), _table(), allowed_auth_modes()

### Community 68 - "Resources Validation"
Cohesion: 0.20
Nodes (8): _check_copy(), _is_missing(), _read_copy(), _report_unnamed(), _unnamed_items(), validate_resources(), _with_printable_path(), hidden_text_problems()

### Community 69 - "Orqlet Baseline Rules"
Cohesion: 0.13
Nodes (7): Orqlet baseline, Four-phase workflow (research, design, plan, implementation), Login-access address handling (ask before first use), Looking-things-up policy, Registered resources (orqlet resources list), orqlet profile approve --reviewer, Approval verified by person-named merge commit on the protected branch ref

### Community 70 - "Design Phase Contract"
Cohesion: 0.18
Nodes (11): Artifact header orqlet.artifact-header/v1 (task, status, workflow_version, protected_set_digest, bound values), Phase contract reference, orqlet gate status, Handoff table (task, scope, decisions, open questions, prerequisites) and header binding, Input check (present, validator, same task, same project, approved, current, questions), Ledger fail-closed rule (changed answered questions stop the skill), Finding ORQ-W390 (stale approved input), orqlet validate as-is / design / plan (+3 more)

### Community 71 - "Exempt Change Classes"
Cohesion: 0.13
Nodes (14): classes, documentation-only, maintenance, workflow-artifact, code_name_patterns, except_under, excludes_agent_configuration_surface, extensions (+6 more)

### Community 72 - "MCP Credential Detection"
Cohesion: 0.22
Nodes (9): _collect_references(), _decoded(), _has_credential_key(), _has_credential_query(), _has_literal_authorization(), _is_credential_pair(), _is_literal(), referenced_variables() (+1 more)

### Community 73 - "Profile CLI Command"
Cohesion: 0.21
Nodes (4): answer_command(), action(), approve_command(), _parse()

### Community 74 - "Standards & Foundations Docs"
Cohesion: 0.18
Nodes (12): Command doc: read applicable standards, MUST rules (deterministic or review checked), orqlet standards for --path --phase --role, Security design review mode (no packet), Foundations (seeded .prompts file), Workflow non-negotiables (no guessing, four phases, required roles, not run is not success), Required roles per phase (a different agent may fill a role), Team engineering practices section (Orqlet writes no company policy) (+4 more)

### Community 75 - "AS-IS Format Reference"
Cohesion: 0.21
Nodes (13): AS-IS format, Artifact header (orqlet.artifact-header/v1) and bound values, AS-IS file (as-is.md, orqlet.as-is/v1), Contradiction C-n, Evidence citation (path, lines, revision, sha256), Fact A-n with evidence, Inference I-n, Research brief (six sections) (+5 more)

### Community 77 - "Model Policy Loading"
Cohesion: 0.24
Nodes (7): _contract_message(), _finding(), _invalid(), _parse(), PolicyInvalid, PolicyLoaded, read_model_policy_at()

### Community 78 - "Implement Phase Contract"
Cohesion: 0.17
Nodes (12): orqlet-implement phase contract, Commands found in project files, Handoff table (AS-IS, Design, Plan, Phase report), Input check (seven checks), Project context sources, Stale input invalidation matrix, Words for orqlet standards for (phase and role), Warning list of risky commands (+4 more)

### Community 79 - "Canonical Digest"
Cohesion: 0.33
Nodes (6): canonical_json(), digest_of(), _encode(), _encode_string(), JsonValue, CanonicalJsonError

### Community 80 - "MCP File Rendering"
Cohesion: 0.24
Nodes (4): render_mcp_file(), _variable(), name_problems(), rendered_entry()

### Community 83 - "Security Reviewer Role"
Cohesion: 0.24
Nodes (10): Role: Security Reviewer (orqlet-security-reviewer), Knowledge drafts must disclose nothing private, No security-relevant change statement with absence record, Security risk categories (secrets, authn/authz, injection, file/process access, dependencies, data exposure), Considerations (security, compatibility, operations) with evidence refs, expected_changes entries (surface, action, identity, expected_after, verification), extractor_config (public_api, dependency_manifests, lockfiles, security_globs), Design manifest schema orqlet.design-set/v1 (+2 more)

### Community 85 - "Front Matter Diff"
Cohesion: 0.28
Nodes (4): _difference(), front_matter_differences(), simple_front_matter(), _string_form()

### Community 87 - "Plan Format Reference"
Cohesion: 0.22
Nodes (9): Code review checks (criteria, defects, tests, maintainability), Change class D1/D2/D3, Plan format reference, Acceptance criterion, Check completion entry, Implementation checklist, Plan validator rules, Projected tree (+1 more)

### Community 88 - "Onboard Skill"
Cohesion: 0.28
Nodes (9): orqlet-onboard skill, Profile approval by person, Project profile (.orqlet/project-profile.yaml), Commands recorded in AGENTS.md, Resource registration (orqlet resources add), Commands found in project files, Project context sources, Words for orqlet standards for (phase and role) (+1 more)

### Community 90 - "Plan Phase Contract"
Cohesion: 0.25
Nodes (8): orqlet-plan phase contract, Commands found in project files, Handoff table (AS-IS, Design, Plan, Phase report), Input check (seven checks), Project context sources, Stale input invalidation matrix, Words for orqlet standards for (phase and role), Warning list of risky commands

### Community 91 - "Integrations Registry"
Cohesion: 0.38
Nodes (3): Integrations, _registered_clients(), _with_declaration()

### Community 92 - "PR Workflow Section"
Cohesion: 0.38
Nodes (4): Pull request template: Orqlet workflow section, PR evidence list (design PR, plan PR, review record, test record, required checks), Knowledge impact and knowledge record, Orqlet-Task and Orqlet-Phase trailers

### Community 95 - "Skill & Rule Templates"
Cohesion: 0.47
Nodes (5): Team resources catalogue template, {{lines}} placeholder (registry data), Team conventions block template, Team resource rule template, Tool documentation skill template

### Community 96 - "Workflow Manifest"
Cohesion: 0.40
Nodes (4): controls_level, files, schema, workflow_version

### Community 97 - "Workflow Rule Metadata"
Cohesion: 0.40
Nodes (4): description, name, paths, schema

## Knowledge Gaps
- **46 isolated node(s):** `Registered resources (orqlet resources list)`, `Login-access address handling (ask before first use)`, `Findings report (errors, warnings, notes with finding codes)`, `Command doc: fill in project profile open facts`, `orqlet profile approve --reviewer` (+41 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1088 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **36 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `CanonicalPath` connect `Scoped FS & Backups` to `Client Instruction Adapters`, `Binding Inputs & Plans`, `Standards Pack Resolver`, `Diagnose & Personal Items`, `Policy Validation & Hashing`, `Init Files & Generated Lock`, `Technology Scanners`, `Role Bindings & Render All`, `Lifecycle CLI & Doctor`, `Artifact Header & Review Result`, `Resources Contract & View`, `Profile Facts & Init Questions`, `Upgrade & Rollback`, `Contract Loading & Pin Staleness`, `Plan & Question Ledger Validation`, `Resources Editing`, `Workflow Sources & Seeds`, `Ancestor Finder & Wiring`, `VCS Port & Staleness`, `Init Project & Prompter`, `Change Class & Design Scope`, `Managed Blocks & Drift`, `Change Journal & Apply Plan`, `Local File System`, `Python Scanner & Known Tech`, `Conventions Check`, `Scanner Port & Discover`, `Gate Status & Workflow Lock`, `Plan Tree Projection`, `AS-IS Validation`, `Change Plan Builder`, `Integrations Validation`, `FS Journal & Schemas`, `Evidence Citation`, `Drift Findings & Explain`, `Git Commit Parsing`, `Integrations Source Loader`, `Resources Validation`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Are the 115 inferred relationships involving `CanonicalPath` (e.g. with `_mcp_file()` and `FsBackupStore`) actually correct?**
  _`CanonicalPath` has 115 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Registered resources (orqlet resources list)`, `Login-access address handling (ask before first use)`, `Findings report (errors, warnings, notes with finding codes)` to the rest of the system?**
  _46 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Python API & Dependency AST` be split into smaller, more focused modules?**
  _Cohesion score 0.053289473684210525 - nodes in this community are weakly interconnected._
- **Why does `Contract` connect `Design Set Contracts` to `Binding Inputs & Plans`, `Standards Pack Resolver`, `Init Files & Generated Lock`, `Role Bindings & Render All`, `Review Identity & Independence`, `Artifact Header & Review Result`, `Resources Contract & View`, `Profile Facts & Init Questions`, `Contract Loading & Pin Staleness`, `Plan & Question Ledger Validation`, `Models Resolve & Capabilities`, `Model Policy Selection`, `Init Project & Prompter`, `Change Class & Design Scope`, `Knowledge Impact`, `Packaged Workflow`, `Python Scanner & Known Tech`, `Scanner Port & Discover`, `Render Request Model`, `Init Command & CLI Result`, `Gate Status & Workflow Lock`, `AS-IS Validation`, `Model Policy Contract`, `MCP Server Contract`, `Integrations Registry`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `Contract` (e.g. with `load_contract()` and `read_contract_at()`) actually correct?**
  _`Contract` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Should `Client Instruction Adapters` be split into smaller, more focused modules?**
  _Cohesion score 0.06788766788766788 - nodes in this community are weakly interconnected._