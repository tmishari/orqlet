---
description: Read the standards that apply to the files you are about to change
---
Read the standards that apply before you change code.

1. List the files or folders you are going to change. If you do not know yet, ask the user.
2. For each one, run `orqlet standards for --path <path>` from the repository root. Add `--phase <research|design|plan|implementation>` and `--role <role>` when you know them.
3. Follow every MUST rule. Rules marked `deterministic` are checked by a tool and rules marked `review` are checked by a person on the pull request.
4. If a rule does not fit this change, tell the user. Do not skip it on your own.
5. Name the rule ids you applied in your plan and in your summary.
