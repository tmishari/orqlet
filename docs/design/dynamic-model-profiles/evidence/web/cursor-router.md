# Cursor Router

URL: https://cursor.com/docs/cursor-router.md
Retrieved: 2026-11-04, between 14:00 and 16:15 (UTC+2); the tool returns no time for each page
Tool: WebFetch (Cursor)
Processed: unknown (the tool returns the page as Markdown and does not say whether a model processed it)
Data class: public

Excerpts are verbatim from the text the tool returned.

1. Availability - "Cursor Router is currently only available on Teams and Enterprise plans."
2. Modes - "Cost: Uses the previous Auto routing logic. It optimizes token spend." and "Balance: Optimizes for intelligence, speed, and cost." and "Intelligence: Routes to the most capable models for harder tasks, at a lower cost than running a single frontier model."
3. Not hand-picked - "Cursor Router is data-driven and managed by Cursor. You can't hand-pick which model handles a request, and the model pool changes over time as new models ship. You steer routing by choosing an optimization mode."
4. Access controls - "On Enterprise plans, Cursor Router respects your team's model access controls. If a model is blocked for your team, the router routes to an allowed model instead."
5. Router requirement - "Blocking too many models reduces routing quality and can disable the router." and "enabling Grok 4.6 is a requirement for the router to work."
6. Underlying model - "Underlying model: Display which model Auto routed to at the start of each response, or keep it hidden. Hidden is the default and recommended, so results are judged on their own merit rather than by model name. Applies to Balance and Intelligence modes."
7. Impose Auto - "Impose Auto: Make Auto the default model for everyone on the team. Soft defaults each new chat to Auto; members can still switch models. Hard locks the model picker to Auto."
8. Pricing - "Balance and Intelligence bill at the list price of the model each request is routed to."
9. SDK - "The TypeScript SDK and Python SDK expose Cursor Router as model id `auto-smart` with parameter `optimize_for` (`cost`, `balanced`, or `intelligence`)."
10. Enterprise default - "Enterprise teams must enable the router manually as it's off by default."
