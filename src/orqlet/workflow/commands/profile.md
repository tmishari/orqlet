---
description: Fill in the open facts of the project profile; a person approves it
---
Help the team answer the open facts of the project profile.

1. Run `orqlet doctor` and read finding ORQ-W181. It lists the facts that are still unknown.
2. Ask the user for the value of each one. Never guess a value. Do not invent a branch naming rule or a commit convention.
3. Preview the answers with `orqlet profile answer KEY=VALUE ... --dry-run` and show the user what would change.
4. When the user agrees, run the same command with `--yes` instead of `--dry-run` and show the change id it prints. It can be undone with `orqlet rollback <change id>`.
5. Approving the profile is a decision for a person. Never run `orqlet profile approve` yourself. Tell the user to run `orqlet profile approve --reviewer "<their name>"`.
