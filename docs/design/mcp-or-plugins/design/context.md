# Context view: who and what the change touches

Scope: how an MCP server entry gets from this repository to each developer's client, and where the developer's own credential comes from. Orqlet never calls a model and never starts an agent (ORQLET-NOMODEL-001); it never reads a client's credential store and never stores a secret in Git, prompts, Markdown, indexes or logs (AS-IS A-53).

```mermaid
flowchart TB
  dev["Developer<br/>one account per integration<br/>signs in or sets an own variable"]
  maint["Maintainer<br/>declares servers<br/>reviews the pull request"]
  subgraph orq["Orqlet (command line)"]
    cli["orqlet init, upgrade, validate<br/>writes entries without any credential"]
  end
  repo["This repository on GitHub<br/>declaration and MCP files<br/>reviewed by a pull request"]
  clients["Claude Code, Codex, Cursor<br/>terminal, IDE, desktop, cloud, review contexts"]
  signin["Each vendor's sign-in and token service<br/>issues the user's own token"]
  servers["Remote MCP servers<br/>GitHub, Atlassian (Jira, Confluence)"]
  miro["Miro MCP server<br/>no entry from Orqlet"]

  maint -->|"declares, runs init and upgrade, opens the pull request"| cli
  cli -->|"entries: URL fixed, variable names only"| repo
  repo -->|"pull: the same entries for everyone"| clients
  dev -->|"opens the client"| clients
  dev -->|"signs in, or creates an own token"| signin
  signin -->|"the user's token reaches the client"| clients
  clients -.->|"cloud agent, review context, CI: the account of the one user who started or owns it (Q-12, to verify)"| servers
  clients -->|"every call carries the user's own token"| servers
  dev -.->|"own plugin or manual entry, outside Orqlet"| miro
```

## Trust boundaries

| Boundary | What crosses it | Who decides | What this design does about it |
|---|---|---|---|
| B-1 repository to client | A server address and the names of variables that a client expands | The pull request that changes the committed file (Q-11: reviewed by this repository's code owners; a changed file-and-declaration pair passes the offline check, so only review catches it) | The address is a literal on a closed table in the tool, in the declaration and in the file; `validate integrations` compares the file with the entry that the tool builds; a changed address with an unchanged variable name is an error (ADR-002) |
| B-2 user environment to client | The user's own token, read from a variable or obtained by sign-in | The user | Orqlet writes only the variable name or nothing and reads no credential store (AS-IS A-53); it reads the MCP files and the declaration as text |
| B-3 client to remote server | The user's token in an `Authorization` header or an OAuth exchange | The vendor and the user's account | The entry holds no credential or one reference, and the connection and the token belong to the client and the vendor; no shared identity can be named in the declaration (Q-9, ADR-002); an unattended surface uses the account of the one user who started or owns it (Q-12), which V-12 verifies |

The accepted facts behind the picture: project MCP files are shared through version control and each user supplies the credential (AS-IS A-55, A-58, A-61, A-108, A-110); a client stores an OAuth sign-in for the user who signed in (Claude Code per endpoint, A-69; Codex in a keyring or a file, A-98; where Cursor stores it is not stated), and an unattended surface is to use the account of the one user who started or owns it (the person's answer to Q-12; no vendor text says whether the surfaces can do that, V-12); the design's own rule is that credentials are never copied between clients (A-37).
