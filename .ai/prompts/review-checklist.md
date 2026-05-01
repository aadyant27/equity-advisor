# Claude Code Output Review Checklist

## Before approving any file

### Types

- [ ] Types match state.py exactly
- [ ] No plain `str` where `Literal` should be used
- [ ] Optional fields use `| None` not `Optional[]`

### Imports

- [ ] Only imports what it uses
- [ ] Imports from correct local modules
- [ ] No missing imports

### Agent specific

- [ ] Returns complete AgentState not partial dict
- [ ] Appends to agent_log
- [ ] Loads env vars via python-dotenv
- [ ] Has error handling with clear exception messages

### General

- [ ] No placeholder comments like "implement this later"
- [ ] No hardcoded API keys
- [ ] Docstrings on every class and function
