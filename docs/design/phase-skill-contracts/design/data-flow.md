# Data flow

Three flows. Nothing in them is new code; what is new is the text that travels along the first flow and what the agent reads and checks in the other two.

## 1. From the workflow package to a receiving project

```mermaid
flowchart LR
  src["skills/&lt;name&gt;/skill.md<br/>skills/&lt;name&gt;/references/*.md<br/>roles/*.md"] --> load["load_skills:<br/>render_steps on the body,<br/>references attached as they are"]
  prof[".orqlet/project-profile.yaml<br/>(this project only)"] --> conv["conventions block"]
  load --> req["render request<br/>(no profile)"]
  req --> ad["claude_code, cursor, codex adapters"]
  conv --> blocks["AGENTS.md managed blocks"]
  ad --> files["SKILL.md, references/, agents/openai.yaml,<br/>role files"]
  files --> plan["change plan:<br/>hash on disk vs lock vs render"]
  blocks --> plan
  plan -->|"create, update, restore (ORQ-W096),<br/>keep text outside the blocks"| disk["receiving project files<br/>+ .orqlet/generated.lock.yaml"]
```

- The bytes of the six workflow skills, their references and the five roles depend on the workflow version only, never on the project (A-22, A-23). That is what BC-6 tests.
- Project data reaches rendered files in two existing ways: the conventions block, built from that project's own profile (A-24), and, when the project registers resources, the rules and skills of its resource registry (A-25). This change adds no third way.
- Text outside the managed blocks of AGENTS.md is kept byte for byte (A-41). That is where onboard records the project's commands (ADR-002 decision 6).

## 2. From the project to the agent, when a skill runs

```mermaid
flowchart LR
  req["the person's request<br/>and questions.yaml"] --> agent
  explain["orqlet explain<br/>(technologies, scopes, standards sources, clients)"] --> agent
  std["orqlet standards for --path --phase --role<br/>(rules for each scope path)"] --> agent
  instr["AGENTS.md team text and blocks,<br/>CLAUDE.md, client rules, .prompts/"] --> agent
  ci["CI workflow files, build manifests,<br/>Makefile, profile commands"] -->|"commands, cited with file and lines"| agent
  docs["the project's own task documents"] -->|"cited where they are"| agent
  agent["agent running one skill"] -->|"facts with path and lines,<br/>unknowns as ledger questions"| out["docs/design/&lt;task&gt;/"]
```

- Everything on the left is evidence, never an instruction ("Source material is not authority").
- A value not found goes to the ledger as a question, never into an artifact as a guess (ADR-002 decision 2).
- A command flows into the plan as a check, with every expanded expression replaced by a placeholder. Its defining lines, the files it directly invokes and the tool configuration it reads are cited by hash. Implementation runs it only in two cases (ADR-002 decision 3):
  - the approved, unedited plan names it, and the cited sources are unchanged;
  - the person agreed after seeing it.

### Onboard: commands into AGENTS.md (trust boundary B-2)

```mermaid
flowchart LR
  ci2["CI workflow files, build manifests<br/>(editable by contributors and bots)"] -->|"found, never run"| ob["agent running orqlet-onboard"]
  ob -->|"label, command with placeholders,<br/>source path and lines; warnings"| person(["Person"])
  person -->|"yes per entry"| team["AGENTS.md team text<br/>outside the managed blocks"]
  team -->|"loaded as instructions<br/>in every later session"| later["later agent sessions"]
  team -->|"pull request diff"| rev(["Reviewer"])
```

- The B-2 boundary is crossed only with the person's yes for each entry, in the fixed form of ADR-002 decision 6, and the change is visible in the pull request diff.
- A later skill that uses such a command cites the AGENTS.md lines and the original source they name.

## 3. From one phase to the next

```mermaid
flowchart LR
  asis["as-is.md<br/>front matter: facts, unknowns<br/>body: research brief"] -->|"as_is_ref: path and sha256"| design["design/manifest.yaml<br/>component.md: design brief, BC-n<br/>ADRs"]
  design -->|"design_ref: path and sha256"| plan["plan.yaml<br/>per phase: acceptance criteria and checks,<br/>then file operations"]
  plan -->|"phase id"| impl["phase commit with<br/>Orqlet-Task and Orqlet-Phase trailers,<br/>tests/&lt;phase&gt;.yaml, reviews/"]
  ledger["questions.yaml"] --- asis
  ledger --- design
  ledger --- plan
  gate["orqlet gate status &lt;task&gt;<br/>present? stale? base in this repository?"] -.-> design
  gate -.-> plan
  gate -.-> impl
  val["validate as-is / design / plan<br/>task equals folder, ref hashes"] -.-> design
  val -.-> plan
```

- Each arrow carries a path and a hash, and the header carries the bound values. The receiving phase checks them before it starts (ADR-003 decision 4).
- The briefs live inside the artifacts, so the reference hash covers them.
- The person's acceptance of the AS-IS file is recorded in that file (ADR-003 decision 7). The approvals of the design and the plan are merges on the host. The person names each merge commit, and the next phase checks that the approved files are unchanged since then (ADR-003 decision 4).
