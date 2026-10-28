# Data-flow diagram

Three flows. Orqlet never reads a credential store and its own output never carries a credential value. It does read repository files that may hold a pasted credential, in order to scan them, and it reports only rule names and positions. The one route by which existing file text could be copied into a new file, a proposal, is closed by not copying it (flow 1).

## Flow 1: declaration to committed file

```mermaid
flowchart LR
  decl[".orqlet/integrations.yaml<br/>untrusted input, no secret"] --> read["load_integrations<br/>strict load, contract, closed table, scan"]
  read -->|invalid| refuse["upgrade refuses, exit 3<br/>rule id and closed field name only<br/>nothing written"]
  read -->|valid| compose["compose<br/>RenderRequest.integrations"]
  compose --> render["Claude Code adapter<br/>render_mcp_file -> rendered_entry<br/>scans the text it builds"]
  render -->|a finding is a defect: raise, exit 70, nothing written| plan["change-plan builder<br/>classify: new, up to date, or seeded-proposal"]
  existing[".mcp.json already in the repository<br/>untrusted input"] -->|compared by hash; _propose passes no existing bytes for an MCP path| plan
  plan -->|new file| apply["journalled write"]
  plan -->|differing file| prop["proposal under .orqlet/proposals<br/>wanted text only, none of the team's file"]
  apply --> lock[".orqlet/generated.lock.yaml<br/>owner seeded"]
  apply --> mcp[".mcp.json<br/>reviewed in the pull request"]
  prop --> info["information finding:<br/>merge the wanted text by hand"]
```

| Data | Where it is trusted | Check |
|---|---|---|
| The declaration | Not trusted | Strict YAML load, size cap, contract validators, closed table, scan |
| An existing `.mcp.json` | Not trusted | Compared by hash only; its text is never put into a proposal |
| The rendered file | Built from the table and the declaration | One function, `rendered_entry`; scanned before it is written |

## Flow 2: checking the files

```mermaid
flowchart LR
  trig["orqlet validate integrations<br/>orqlet doctor and sync<br/>the adopter's CI line"] --> findings["integration_findings"]
  findings --> d[".orqlet/integrations.yaml"]
  findings --> files[".mcp.json, .cursor/mcp.json, .codex/config.toml<br/>only those that exist"]
  d -->|absent| nr["validate: not run, exit 5<br/>doctor and sync: a warning if a file holds the text orqlet-<br/>otherwise nothing"]
  files --> scan["scan of each file's raw text"]
  files --> json["JSON files only: parse with duplicate keys rejected<br/>scan of every decoded key and string<br/>compare declared entries with rendered_entry<br/>undeclared orqlet-* entries, closed keys, the text ${<br/>counts of undeclared entries"]
  scan --> out["findings: rule names, line numbers,<br/>closed field names, never a value or a raw key"]
  json --> out
```

## Flow 3: the credential, outside Orqlet

```mermaid
flowchart LR
  user["Developer"] -->|signs in; in a later release also sets ORQLET_MCP_* in their own environment| store["Client's sign-in store<br/>or the user's environment"]
  file[".mcp.json from the repository<br/>holds an address and no credential field"] --> client["Claude Code"]
  store -->|B-2| client
  client -->|B-3, Authorization header| server["Atlassian Rovo MCP server<br/>address fixed by the closed table"]
  server --> perm["The user's own permissions apply"]
  orq["Orqlet"] -.->|never reads a credential store| store
  orq -.->|its output never carries a value| client
```

An unattended surface (a cloud agent, a review context, CI) is outside this flow: it uses the account of the one user who started or owns it (Q-12), which check V-10 asks about. Where that fails, ADR-002 decision 12 says the standard is not met there.
