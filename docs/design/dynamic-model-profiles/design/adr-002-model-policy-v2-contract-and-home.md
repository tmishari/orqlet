# ADR-002: The model policy contract (v2) and where it lives

Status: proposed with the design.

## Context

- `orqlet.model-policy/v1` exists as a contract and a committed schema; only the registry references it, the project profile has no `model_policy` key and no command loads, validates or renders it (A-33, A-38, A-41, A-42, A-43). Its only instance is a draft test fixture (A-39).
- v1 has no discovered, approval, callable, evaluated, availability, fallback or escalation field, no validator, and `excluded` is a flat list of strings (A-36, A-37). The proposal's section 24.1 describes a v2 with those fields (A-84); its status is `[P]`, "not yet an existing API" (A-72). Q-15 asks that each element be decided here.
- Orqlet already has team-owned seeded files under `.orqlet/` (`role-bindings.yaml`, `project-profile.yaml`, `versions.yaml`) and a path for a changed seed: a pending diff, not a write (A-24, A-21, A-141).
- Approved capability categories do not exist, and price, brand or vendor does not establish one (AS-IS, "Model candidates"). No model is account-eligible, callable-verified or evaluated (U-19, U-24).
- The accounts: Cursor Enterprise, Claude Code Team or Enterprise, Codex desktop on Enterprise or Edu (Q-10); the Codex app lists GPT-6 Astra, GPT-6.1 Sol, GPT-6.1 Terra and GPT-6 Luna under Advanced (Q-26).

## Decision

1. **One file, `.orqlet/model-policy.yaml`, schema `orqlet.model-policy/v2`.** It is seeded once (owner `seeded`, like `role-bindings.yaml`), belongs to the team and changes only by a reviewed edit (ADR-004). There is no profile key: **an absent file means no policy**, and then the model setting of every existing role file is the one written today (`inherit` or no key).
2. **v2 replaces v1.** v1 has no reader and one fixture; its schema file and fixture are replaced in the same change.
3. **Content** (the plan fixes the field spellings):
   - header: `policy_version` and `reviewed_for_release` (the workflow version at which the catalog was last rechecked); approval is per entry, so there is no file-level status;
   - `models[]`: logical `id`, `family`, an `approval` state (`proposed`, `approved`, `disabled`, `retired`) with `approved_by` and `approval_ref`, a `documented` reference (an evidence file and its date), `callable` (`not-run` or `verified`), `evaluated` (`none` or an evidence reference), list prices (shown by `models resolve`, used for nothing else), and `routes[]`;
   - a route: `client`, `kind` (`id` or `alias`), `name` (the exact client identifier, or none while unknown), `resolves_to` for an alias, `also_known_as` (other spellings that clients report for the same model, such as a name with an effort suffix, A-66), `access` (`unknown`, `confirmed`, `blocked`) and `retires_on` (a date, used only for a warning);
   - `excluded[]` (ADR-005);
   - `profiles[]`: `quality`, `engineering` and `economy` with a capability statement, a mode, ordered candidates per client, fallbacks and an `escalation` profile that `models resolve` shows and nothing applies by itself (the request asks that escalation be explicit);
   - `assignments[]`: a target (a role name or a skill name; PR text is the role `orqlet-pr-writer`), an optional `task` and `client`, a profile or a model, a mode and an optional `effort`. The reviewer-diversity rule is fixed in code (ADR-007) and has no policy field, so a team edit cannot lower the I2 floor.
   **Types.** Policy fields that name a model (`id`, `family`, `name`, `resolves_to`, `also_known_as`) are a `ModelRef`: ASCII from `[A-Za-z0-9._:/@+-]`, at most 128 characters, refused and never truncated; seed free text (`reason`, `source`, the capability statement) is limited to printable ASCII and a length. A model string that a client reports and that a record holds (`model_requested`, `model_observed`) may be client display text (such as "Claude Fable 5.1"), so a record accepts exactly these characters, up to 128 of them, and refuses anything else: letters, digits, the space, and `. _ : / @ + - [ ] = ,`. `effort` and `kind` are closed enumerations; `retires_on` is a date. `approval_ref` is an attested pointer to evidence (a pull-request reference, a merge commit of an earlier change or an ADR); the validator checks presence and format only. v1's data-handling fields are not carried over: Q-6 answered that all four vendors are acceptable for this repository, so the design asks for no data-egress record. `callable: verified` and `access: confirmed` are attested labels that no tool checks. The type is implemented with constrained string types (a pattern and a maximum length) and no custom validator message, because a contract's own error text can repeat the offending value (`src/orqlet/application/contracts/loading.py:22-27`). **No finding prints a recorded model string:** it prints the catalog id the string matched, or `unmatched` with its length; `models resolve` prints catalog values that already passed the `ModelRef` check. The same type checks the CLI arguments `--override` and `--different-family-from` and any value read from an agent file. The credential scan is the integrations scan plus the key shapes of the vendors in the catalog (`sk-`, `xai-`, `AIza`); unkeyed free text outside those shapes is a stated limit.
4. **The five states are separate fields.** Documented, approved, account access, callable-verified and evaluated: none implies another. `callable` and `evaluated` stay `not-run` and `none` until a check runs inside an approved scope and budget (Q-27: paid from the running developer's budget, at most 25 percent of that developer's monthly budget per client).
5. **A capability category is membership of a profile.** The profile's candidate list is the approved category; the coder and the code reviewer both draw from `engineering`. Price, vendor and brand never create a category.
6. **Starting assignments:** `quality` for design, plan, architecture review and security review; `engineering` for implement, test and code review; `economy` for inventory, trace and PR text (the role `orqlet-pr-writer`, ADR-006). The profiles are ordered `quality`, `engineering`, `economy`, from the highest.
7. **Starting candidates are proposals, not rankings.** They come from vendor positioning and list prices (vendor claims, A-111, A-117, A-125, A-134, A-136), and every entry ships `proposed` and unevaluated:

   | Client | quality | engineering | economy |
   |---|---|---|---|
   | codex | gpt-6-astra, gpt-6.1-sol | gpt-6.1-sol, gpt-6.1-terra | gpt-6-luna |
   | claude-code | claude-opus-5-5 | claude-sonnet-5-5 | claude-haiku-5-5 |
   | cursor | claude-opus-5-5, gemini-4-argon | claude-sonnet-5-5, grok-4.7, composer-2.5 | claude-haiku-5-5, composer-2.5 |

   The Cursor identifiers are unknown (U-25, Q-35), so those routes ship with no `name` and stay `missing-candidate`. `gpt-6.1-terra` needs Codex CLI 0.159.0 or later (A-112); its access is `confirmed` only as seen in the desktop app (Q-26), and the app version is not a CLI version. Fable models are not candidates (ADR-005). The Codex app also lists "GPT-6 Sol" (Q-26); the only documented use of that name is a Power preset (A-151), no model ID is documented, so it stays outside the starting catalog and a later release recheck may propose it. The shipped seed holds `access: unknown` for every route; a team records `confirmed` in its own file (the seed carries no account facts).

## Consequences

- Contract change: DET-003 requires the JSON schema to be regenerated with `tools/export_schemas.py` in the same change; the v1 schema file goes away.
- A new validator and loader are needed (ADR-004, component view). The loader follows `integrations_source.py`: through the `FileSystem` port, size limit, strict YAML, findings that never echo a value or a key of the file (ORQLET-SEC-002, ORQLET-SEC-003).
- Seeded `proposed` entries make nothing render: a pin needs `approved` (ADR-003). The code-review gate reports NOT_RUN until a reviewer reaches I2: a review run in a different client does so with no pin, and within one client it needs a pin or an observed model of a known different family, so the team must approve a qualifying model (ADR-006, ADR-007). This is deliberate and visible.
- The file is a second source of model facts next to `role-bindings.yaml`; ADR-007 removes the overlap (family comes from the policy when one exists).
- A project that somehow holds a v1 file at `.orqlet/model-policy.yaml` gets exit 3 from `upgrade` and `models resolve` ("a v1 file; migrate"): Orqlet never seeded one and no command read one, so none is expected.

## Rejected alternatives

- **Extend v1 in place.** `excluded` changes from a flat list to structured entries and every state field is new; reusing the schema id would hide a breaking change although no reader exists to protect.
- **Put the policy in `.orqlet/project-profile.yaml`.** The profile holds discovered facts and is edited through `orqlet profile`; team decisions about models with their own approvers do not belong beside it.
- **Put it in `.prompts/`.** That folder holds rules the standards resolver reads (`Source: prompts`); a policy is data, not a rule.
- **Merge it into `role-bindings.yaml`.** Bindings approve reviewer agents for gates; models have different approvers, a different life cycle and a different release recheck.
- **One file per client.** It repeats the catalog and the profiles three times and lets them drift.
