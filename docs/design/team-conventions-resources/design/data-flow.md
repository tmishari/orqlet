# Data flow

Scope: how the answers and the links travel, what an agent does with them, and how a convention is checked. Orqlet itself moves only files and Git objects. A page is read by the client's tool, in the developer's own session, and never by Orqlet (ADR-001).

## Flow 1: from an answer or a link to the files every developer receives

```mermaid
flowchart LR
  ans["Maintainer<br/>answers, link, note,<br/>applies-to, tool, access"] --> chk["Input checks<br/>(address grammar, text allow-list, id, glob rules)<br/>refused with a finding if wrong"]
  chk --> reg[".orqlet/resources.yaml<br/>seeded, team owned"]
  chk --> prof[".orqlet/project-profile.yaml<br/>repository conventions"]
  reg --> view["resources_view<br/>the one derivation of reach"]
  prof --> view
  view --> rules["rule files, PROTECTED<br/>.claude/rules and .cursor/rules<br/>one per resource with applies-to"]
  view --> skills["skills, PROTECTED<br/>orqlet-tool-id, orqlet-resources<br/>.claude/skills and .agents/skills"]
  view --> block["AGENTS.md block 'conventions', PROTECTED<br/>Codex, Cursor, Claude Code through the bridge"]
  rules --> pr["pull request<br/>reviewed by code owners"]
  skills --> pr
  block --> pr
  reg --> pr
  pr --> devs["every developer's client"]
```

What leaves the maintainer's terminal is text that passed the checks of the domain rules. A refused value is never written, and the finding names the rule and the field, not the rejected content when that content could hold a secret (ORQLET-SEC-003). A value that reaches a generated file is checked again at render, written as a quoted JSON string, and the generated files are `PROTECTED`, so a hand edit of a rule, a skill or the block is an error that `upgrade` undoes.

## Flow 2: an agent looks something up, with or without a login

```mermaid
flowchart TB
  task["Task in a phase<br/>research, design, implement, onboard"] --> need{"A library, framework or tool<br/>whose behaviour the repository<br/>does not document?"}
  need -- no --> done["Work on repository evidence"]
  need -- yes --> reg["Registered resource?<br/>orqlet resources list"]
  reg -- "stored copy" --> read["Read the stored copy first<br/>it names its form and retrieval date"]
  reg -- "link only" --> web
  reg -- "none" --> web["Official documentation by the client's web tool"]
  read --> more{"Enough?"}
  more -- yes --> done
  more -- no --> web
  web --> login{"Page behind a login?"}
  login -- no --> excerpt["Excerpt as the tool returned it, with address, time, tool and Data class public<br/>docs/design/task/evidence/web/*.md<br/>committed, then cited"]
  login -- yes --> signin["Agent stops and asks the developer to sign in<br/>in their own browser or MCP sign-in"]
  signin --> route{"Client can read<br/>the signed-in page?"}
  route -- yes --> summ["Summary in the agent's own words, Data class internal<br/>shown to the person; the agent commits it only after a yes (advice)"]
  summ --> done
  route -- no --> unk["Write an unknown with a question<br/>ask for a stored copy; never guess"]
  excerpt --> done
```

Data classes in this flow: the registry and the stored copies are team data in the repository (a page behind a login is `access: login`, which means internal; its stored copy is a summary that `attach` confirms at a terminal, and its evidence file is a summary that the person approves before it is committed, ADR-002 and ADR-004); the page text on its way to the agent is untrusted and is treated as evidence, and it also goes to the client's model vendor (ADR-001); Orqlet writes no session, cookie or token into the repository, a rendered file or a log, and the baseline asks the agent not to write one (advice; the scan of `credential_problems` includes the shape of a browser storage-state file at the two places where it runs). Git history cannot be cleaned afterwards, and Orqlet cannot see offline whether the repository is public.

## Flow 3: a convention is checked

```mermaid
flowchart LR
  pr["Pull request on the code host"] --> ci["CI step<br/>orqlet conventions check<br/>--branch name --base target"]
  prof[".orqlet/project-profile.yaml<br/>read at the base revision<br/>branch patterns, commit convention"] --> use["conventions_check"]
  ci --> use
  git["Git objects<br/>branch name, commit subjects<br/>through the hardened Git runner"] --> use
  use --> verdict{"Verdict"}
  verdict -- "PASS" --> ok["step passes"]
  verdict -- "FAIL" --> bad["findings: rule, commit id, bounded text<br/>exit code 5"]
  verdict -- "NOT_RUN" --> skip["nothing configured, free text, base not resolved (shallow clone),<br/>no merge base, branch unknown, or more than 200 commits<br/>reported as not run, never as passed"]
  bad --> host["required status check blocks the merge<br/>(set by a person on the code host)"]
```

Merge strategy, required checks, reviewers and the release flow are recorded and told to agents, but they are enforced by the code host's branch protection, which only a person with admin rights sets and which Orqlet cannot read offline (AS-IS A-87; ADR-003).
