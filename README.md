# Project Structure

- CLAUDE.md and SPEC.md — at root level, not in any folder. These are the two files that define the entire project before any code is written. CLAUDE.md is permanent project memory for Claude Code. SPEC.md is the blueprint for what we're building. Root level means they're the first thing anyone sees when they open the project.

- backend/ — everything that runs on the server. The user never touches this directly. It processes data, runs the AI agents, talks to the database, and exposes APIs. We separate backend from frontend because they're independent systems — the backend could serve a mobile app tomorrow without changing a line.

- backend/agents/ — the heart of the project. This is where all 5 LangGraph agents live, plus the shared state definition and the graph assembly. Every AI decision in the system happens inside this folder. Keeping agents isolated in their own folder means each one can be read, tested, and improved independently without touching anything else.

- backend/api/ — the door between the outside world and the agents. FastAPI lives here. It receives HTTP requests from the frontend, hands them to the agent graph, and streams responses back via SSE. It knows nothing about AI — it just routes traffic. That separation is intentional.

- backend/rag/ — RAG stands for Retrieval Augmented Generation. This folder handles the knowledge base — seeding pgvector with tax rules, IRC sections, and AMT thresholds. It's separate from agents because seeding the knowledge base is a one-time setup task, not something that runs on every request. Conceptually different responsibility, so different folder.

- frontend/ — everything the user sees and interacts with. Completely separate from backend. Talks to the backend only through the API contracts defined in SPEC.md. If you swap the backend from Python to Node tomorrow, the frontend doesn't change at all.

- frontend/src/components/ — React UI components. The graph visualiser that lights up as agents run, the human review modal that appears on interrupt, the report renderer. Each component does one visual thing and nothing else.

- frontend/src/hooks/ — React hooks. Custom logic that connects the UI to the backend. The useAgentStream hook lives here — it manages the SSE connection, receives agent events, and gives components the live data they need to render. Hooks are separate from components because logic and presentation should never be mixed.

- tests/ — one test file per agent. Lives at the root level, not inside backend, because tests are not part of the application — they verify it. In the interview, this folder signals that you built this properly. 92% coverage on your resume isn't a coincidence — it's a habit.

- .ai/ — supporting reference material. Research notes, saved prompts that worked well, architectural decisions you made and why. Claude Code doesn't read this automatically — it's for you. During the interview you can open this and say "here's where I documented my architectural decisions while building."

# Claude markdown file

- CLAUDE.md is essentially answering one question: "What does Claude Code need to know to work on this project without me explaining anything?"
- Claude Code reads this document at the start of every single session. I structured it in 6 sections, each solving a specific problem:

1. **What this project is**
2. **Tech stack**
3. **Domain glossary** : This is the most important section for this specific project. ISO, NSO, AMT, FMV, strike price — these are domain-specific terms that have very precise meanings in equity compensation. If Claude Code doesn't know that AMT means Alternative Minimum Tax triggered by ISO exercise, it will write vague, incorrect financial logic. The glossary makes Claude Code speak the same language as the domain.
4. **Architecture** : This tells Claude Code the exact shape of the system — 6 agents, in this order, doing these specific jobs. Without this, if you ask it to "implement the risk analyst", it has no idea where that fits in the bigger picture. With this, it knows the risk analyst comes after RAG research and before strategy, and it'll write code that fits that pipeline correctly.
5. **Shared state** : This is a hard constraint. In a LangGraph system, all agents communicate through a single shared AgentState object. If Claude Code doesn't know this rule, it might write an agent that returns a completely different shape — breaking the entire graph. This section prevents that by making the constraint explicit.
6. **Coding conventions** :
