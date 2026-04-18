- Since it's a greenfield project, we add Data Models & API contracts in Spec.md file.
- Apart from that we add, Acceptance Criteria, Agent graph topology & problem statement.
- SPEC.md is only needed in two situations:

1. Situation 1 — Greenfield project like ours
   Nothing exists yet. No code, no models, no APIs. You need to define the architecture somewhere before Claude Code can build it. That's our current situation. We wrote SPEC.md once, at the start, to define the whole system. We won't keep updating it for every feature.

2. Situation 2 — Complex feature with many moving parts
   A feature so large and interconnected that a ticket description isn't enough context. You write a spec for that one feature, Claude Code implements from it. Done.
   For everything else — normal tickets, bug fixes, small features — you just paste the ticket directly.
