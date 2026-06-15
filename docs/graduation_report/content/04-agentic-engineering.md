# Chapter 4: Agentic Engineering

## 4.1 Motivation
Modern software development is often bottlenecked by the manual cycle of "hypothesis $\rightarrow$ implementation $\rightarrow$ testing". Agentic Engineering seeks to automate this loop by using LLM-based agents that can write code, run tests, and analyze results autonomously.

## 4.2 Multi-Agent Architecture
The project implemented the **Autolab** system, a five-agent orchestration layer:
1. **Autolab (Orchestrator)**: Delegates tasks to subagents.
2. **Researcher**: Scouts literature and suggests new hypotheses.
3. **Planner**: Manages the experiment queue and assigns IDs.
4. **Worker**: Implements the hypothesis in an isolated git worktree and runs the experiment.
5. **Reporter**: Summarizes the results and identifies the new "Best F1" score.

### 4.2.1 Delegation Map

| Role | Responsibility |
|------|---------------|
| **Researcher** | Performs literature research and paper synthesis to suggest hypotheses. |
| **Planner** | Coordinates the experiment queue and assigns IDs to workers. |
| **Worker** | Executes isolated experiments in git worktrees to prevent state corruption. |
| **Reporter** | Summarizes results and updates the staircase accuracy charts. |

## 4.3 Reducing Hallucinations
To ensure the AI agents produced reliable code, three guardrails were implemented:
- **Spec-Driven Development (SDD)**: Using `speckit` to create a "Living Spec". Agents must follow the spec, and any drift is detected and resolved.
- **Test-Driven Development (TDD)**: Agents are required to write a failing test before implementing a fix, ensuring that every change is verified.
- **Specialized Skills**: Instead of relying on general knowledge, agents are provided with "Skills" (e.g., `vercel-react-best-practices`) which act as bounded, high-quality instructions.

## 4.4 Overcoming Context Window Limits

As the codebase grew, managing the LLM's context window became critical:

### 4.4.1 Caveman Mode
A token-compression communication style that removes fluff and articles, reducing input size by approximately 75% without losing technical substance.

### 4.4.2 Subagents and Worktrees
Using isolated git worktrees and a routing layer to direct queries to the most appropriate subagent, ensuring each agent only receives context relevant to its specific task.

### 4.4.3 Reusable Skills
Encoding complex workflows (e.g., `vercel-react-best-practices`, `fastapi`) into bounded, high-quality skill definitions that constrain agent behavior to validated patterns.
