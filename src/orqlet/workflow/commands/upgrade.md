---
description: Bring the Orqlet files of this repository up to date, after you approve the plan
---
Bring the Orqlet files of this repository up to date with the installed Orqlet.

1. Run `orqlet upgrade --dry-run` from the repository root and show the planned changes.
2. Explain every update or removal, and point out any file the team edited by hand.
3. Ask the user whether to continue. Change nothing until they say yes.
4. After a yes, run `orqlet upgrade --yes`. Show the change id it prints. It can be undone with `orqlet rollback <change id>`.
