# .prompts

This folder holds the standards that agents read on demand. It is not an always-on instruction.

- **Who owns it:** your team. Orqlet wrote these files once and will not change or remove them.
- **How it is loaded:** an agent runs `orqlet standards for` and reads the rules that apply to its path, role and phase.
- **How to add a standard:** add a rule to `rules.yaml` with an id, a level (MUST, SHOULD or MAY), a scope and the text. Put longer explanations in Markdown files here and name them from the rule.
- **What it cannot do:** nothing in this folder can remove or weaken the Orqlet workflow. A rule that tries to is a validation error.

Changes to this folder are reviewed like code, by the people who own the standards.
