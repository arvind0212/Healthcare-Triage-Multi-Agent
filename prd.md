# Product Requirements Document: Simulated MDT Agent System

**Version:** 1.3
**Status:** Draft
**Date:** 2025-04-22
**Author:** Gemini (as 100000x Seasoned Product Manager)
**Stakeholders:** Project Evaluators, Developer (You)

## 1. Introduction

This document outlines the requirements for the "Simulated Multi-Disciplinary Team (MDT) Agent System." The primary goal is to design and implement an autonomous AI agent system that simulates a collaborative medical team reviewing a synthetic patient case to generate potential treatment considerations. The system aims to demonstrate a sophisticated understanding of agent architecture, incorporating capabilities such as advanced multi-agent collaboration, persistent memory, robust error handling, enhanced debugging/logging, self-evaluation, and a flexible tool interface. While set in a medical context, the primary evaluation criteria focus on the successful demonstration of core and advanced agent capabilities and system architecture, rather than the clinical accuracy of the simulation. The system will feature a minimalistic user interface for interaction, including a dynamic visualization of the agent workflow during execution.

**Note:** The scope defined herein is comprehensive. Prioritization or partial implementation of some features within the initial time constraint (estimated 4-6 hours) is acceptable, provided it's documented in the final README. The dynamic visualization adds complexity.

## 2. Goals

* **G1 (Core Functionality):** Simulate an MDT process where specialized AI agents analyze different facets of a synthetic patient case.
* **G2 (Agent Capabilities Demonstration - PRIMARY FOCUS):** Demonstrate core and advanced agent capabilities:
    * **Autonomy:** Agents independently process tasks using defined logic/prompts/planning.
    * **Tool Use:** Agents utilize a defined tool plugin interface to interact with simulated external tools.
    * **Memory:** Implement both short-term (within-run context) and persistent long-term memory (across sessions).
    * **Collaboration:** Implement collaboration patterns beyond simple orchestration.
    * **Robustness:** Incorporate retry/fallback logic for key operations.
    * **Observability:** Implement logging, state inspection mechanisms, **and live workflow visualization.**
    * **Self-Evaluation:** Include a mechanism for the system to assess its output.
* **G3 (Technical Demo):** Serve as a portfolio piece fulfilling the requirements of the technical assignment, showcasing system design, code quality, and agent architecture.
* **G4 (User Experience):** Provide an ultra-minimalistic, seamless UI for initiating simulations, viewing results, **and observing the agent workflow in real-time.**
* **G5 (Extensibility & Design):** Design the system with modularity, a clear separation of concerns, and defined interfaces (e.g., for tools, status updates).

## 3. Target Audience

* **Primary:** Evaluators of the technical assignment – Assessing system design, implementation quality, and fulfillment of all requirements.
* **Secondary:** The developer (You) – Guiding the development process.
* **Tertiary:** Future developers – Understanding the system for potential maintenance or extension.

## 4. Requirements

### 4.1. Functional Requirements (FR)

| ID     | Requirement                                                                    | Details                                                                                                                                                                                                                                         | Alignment                          |
| :----- | :----------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :--------------------------------- |
| FR01   | **Accept Synthetic Patient Case Input:** | Input via UI (JSON `PatientCase` schema).                                                                                                                                                                                       | G1, G4                             |
| FR02   | **Agent Orchestration & Collaboration:** | Coordinator Agent manages baseline workflow. Allow for potential direct agent interaction or more dynamic task delegation. **Coordinator must emit status updates** indicating current agent and task.                       | G1, G2 (Collaboration), G3, FR15 |
| FR03   | **Specialized Agent Analysis:** | Implement core agents (**EHR, Imaging, Pathology, Guideline, Specialist**). Focus on distinct roles and inputs/outputs.                                                                                                       | G1, G2, G3                         |
| FR04   | **Agent Autonomy & Reasoning:** | Agents perform tasks autonomously. Explore slightly more advanced reasoning if feasible.                                                                                                                                        | G2 (Autonomy), G3                  |
| FR05   | **Agent Tool Use via Interface:** | Agents utilize tools via a defined Tool Interface/Registry. Tools are simulated but accessed through a standardized mechanism.                                                                                                    | G2 (Tool Use), G3, G5              |
| FR06   | **Short-Term & Long-Term Memory:** | Implement short-term context passing. Implement persistent long-term memory influencing future runs.                                                                                                                       | G2 (Memory), G3                    |
| FR07   | **Generate MDT Summary Report:** | Structured report (`MDTReport`) summarizing findings.                                                                                                                                                                         | G1, G3                             |
| FR08   | **Minimalistic UI:** | Single-page UI for input/output and visualization.                                                                                                                                                            | G4                                 |
| FR09   | **Clear Simulation Status & Observability Views:** | UI indicates running/complete/failed states. UI includes workflow visualization (FR15). Optionally include views for logs/agent state (FR12).                                                                  | G4, G2 (Observability), FR15, FR12 |
| FR10   | **Implement Retry/Fallback Logic:** | Key operations (LLM calls, critical simulated tool calls) include basic retry logic or fallback behavior.                                                                                                                | G2 (Robustness), G3                |
| FR11   | **Implement Structured Logging:** | Implement system-wide structured logging capturing key events, agent actions, errors, and timings.                                                                                                                    | G2 (Observability), G3             |
| FR12   | **Implement Agent State/Memory Inspection:** | Provide a mechanism (e.g., API endpoint, log analysis, optional UI view) to inspect agent state or memory contents.                                                                                                 | G2 (Observability), G3             |
| FR13   | **Implement Custom Tool Plugin Interface:** | Define a clear interface for adding new simulated tools that agents can discover and use. Refactor existing tool simulations.                                                                                         | G2 (Tool Use), G3, G5              |
| FR14   | **Implement Self-Evaluation Mechanism:** | Add a step or agent that assesses the final `MDTReport` based on predefined heuristics or an LLM prompt.                                                                                                       | G2 (Self-Evaluation), G3         |
| FR15   | **Implement Dynamic Workflow Visualization:** | The UI must display a real-time representation (e.g., flowchart) of the agent workflow during simulation. This visualization must highlight the active agent and display status updates (current task, handover, return). | G2 (Observability), G4             |
| FR16   | **Backend Status Updates for UI:** | The backend system (likely Coordinator/API) must push status updates (active agent, task description, status) to the frontend in real-time during simulation to power the visualization (FR15).                               | G2 (Observability), G4, FR15       |

### 4.2. Non-Functional Requirements (NFR)

| ID     | Requirement                          | Details                                                                                                                            | Alignment              |
| :----- | :----------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------- | :--------------------- |
| NFR01  | **Code-Only Implementation:** | Backend logic purely in code (Python).                                                                                             | G3                     |
| NFR02  | **Modularity & Architecture:** | Clear separation of concerns (UI, Backend, Agents, Tools, Memory, Status Updates).                                                     | G3, G5                 |
| NFR03  | **Code Quality:** | Readable, maintainable, well-structured code.                                                                                        | G3                     |
| NFR04  | **Documentation:** | Comprehensive `README.md` covering all features including visualization, architecture, setup, usage, AI reflection.              | G3                     |
| NFR05  | **Performance:** | Simulation completion time TBD. Status updates (FR16) should be pushed with minimal delay for smooth visualization.                   | G1, G4                 |
| NFR06  | **Ethical Considerations:** | Strictly synthetic data; clear disclaimers required.                                                                               | G1, G3                 |
| NFR07  | **Testability:** | Core logic, interfaces (Tool, Status Update), memory components should be testable.                                                  | G3, G5                 |
| NFR08  | **UI Responsiveness:** | UI functional on standard desktop screens. Visualization should update smoothly.                                                 | G4                     |
| NFR09  | **LLM Choice:** | Google Gemini API (Tier 1, targeting Flash-like models).                                                                             | G2, G3                 |
| NFR10  | **Log Format & Accessibility:** | Structured, parseable/accessible logs.                                                                                             | G2 (Observability)     |
| NFR11  | **Tool Interface Standard:** | Clear, consistently applied tool interface.                                                                                        | G2 (Tool Use), G5      |
| NFR12  | **Memory Persistence Method:** | Simple, appropriate persistence method (file, SQLite).                                                                            | G2 (Memory)            |
| NFR13  | **Status Update Mechanism:** | Mechanism for backend-to-frontend updates (e.g., WebSockets, SSE) needs definition, should be reasonably efficient.             | G2 (Observability), G4 |

### 4.3. User Interface (UI) Requirements

| ID     | Requirement                             | Details                                                                                                                                                                                                                                                                                                                                                                | Alignment            |
| :----- | :-------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------- |
| UI01   | **Layout:** | Single-page application layout. Ultra-minimalistic design. Includes a dedicated area for the workflow visualization.                                                                                                                                                                                                 | G4                   |
| UI02   | **Core Workflow:** | Upload JSON -> Run -> View Report/Error & Observe Visualization.                                                                                                                                                                                                                                              | G4, FR01, FR08, FR09 |
| UI03   | **Components:** | - File Input Area - "Run Simulation" Button - **Workflow Visualization Area:** Displays dynamic flowchart/diagram (FR15). - Status Indicator (can be integrated into visualization). - Report Display Area - Disclaimer Banner - (Optional) Tab or section for logs/state info (FR09, FR12).                                           | G4, FR09, FR12, FR15 |
| UI04   | **Workflow Visualization Behavior:** | - Represents agents/steps visually (e.g., nodes in a flowchart). - Receives real-time updates from backend (FR16). - Highlights the **currently active agent** (e.g., green color). - Displays **current status text** (e.g., "Summarizing EHR", "Calling LLM for Imaging", "Handing over to Specialist", "Received output from Pathology"). - Updates dynamically as simulation progresses. | FR15                 |
| UI05   | **Color Palette:** | Minimalistic palette. Use distinct colors for states (e.g., green for active, grey for inactive/pending, red for error). - Primary Bg: `#FFFFFF` / `#F8F9FA` - Secondary Bg/Containers: `#E9ECEF` - Primary Text: `#212529` - Accent (Buttons/Headers): `#4b2981` - Active Agent Highlight: `#28a745` (Green) - Error Highlight: `#dc3545` (Red) - Other accents: `#43bbc2`, `#da3c72` | G4                   |
| UI06   | **Typography:** | Clean, readable sans-serif font. Consistent font sizes. Status text in visualization must be legible.                                                                                                                                                                                                             | G4                   |
| UI07   | **Error Handling Display:** | Display user-friendly error messages. Workflow visualization might also indicate where an error occurred.                                                                                                                                                                                                  | FR09                 |

## 5. Detailed Feature Breakdown (Modules -> Tasks -> Sub-Tasks)

### 5.1. Module: UI Frontend
* Task 1: Implement UI Structure
    * Sub-Task 1.1: Set up basic HTML structure, including area for workflow visualization.
    * Sub-Task 1.2: Apply CSS for layout, colors (UI05), typography (UI06).
* Task 2: Implement File Input Component (As before)
* Task 3: Implement Simulation Control (As before)
* Task 4: Implement Report Display (As before)
* Task 5: Implement Disclaimer (As before)
* **Task 6: Implement Workflow Visualization Component (FR15, UI04)**
    * Sub-Task 6.1: Choose visualization approach (e.g., using a JS library like Mermaid dynamically, SVG manipulation, or simple styled divs).
    * Sub-Task 6.2: Implement frontend logic to listen for status updates from the backend (via WebSocket, SSE, etc. - mechanism TBD).
    * Sub-Task 6.3: Update the visualization dynamically based on received status updates (highlight active agent, update status text).
* Task 7: Implement Log/State View (Optional) (FR09, FR12) (As before)

### 5.2. Module: Backend API / Main Application
* Task 1: Setup Backend Framework (As before)
* Task 2: Implement Simulation Endpoint (Enhanced for status updates)
    * Sub-Task 2.1: Handle file upload/JSON payload.
    * Sub-Task 2.2: Validate incoming JSON.
    * Sub-Task 2.3: **Establish mechanism for sending real-time status updates** to the connected client (e.g., setup WebSocket connection or SSE stream). (FR16)
    * Sub-Task 2.4: Instantiate and invoke the Coordinator Agent, passing the status update callback/channel.
    * Sub-Task 2.5: Handle potential errors during simulation, potentially sending error status update.
    * Sub-Task 2.6: Return final `MDTReport` or error response (can be sent via normal HTTP response after stream/connection closes).
* Task 3: Implement Log/State Access Endpoint (FR12) (As before)

### 5.3. Module: Core System & Shared Components
* Task 1: Implement Structured Logging (FR11) (As before)
* Task 2: Implement Tool Interface & Registry (FR13) (As before)
* Task 3: Implement Memory Management (FR06) (As before)
* Task 4: Implement Basic Retry/Fallback Logic (FR10) (As before)
* **Task 5: Define Status Update Structure & Mechanism Interface (FR16, NFR13)**
    * Sub-Task 5.1: Define the data structure for status updates (e.g., `{ "agent_id": "ImagingAgent", "status": "ACTIVE", "message": "Calling LLM..." }`).
    * Sub-Task 5.2: Define interface/callback mechanism for Coordinator/Agents to emit these statuses.

### 5.4. Module: Coordinator Agent
* Task 1: Implement Orchestration & Collaboration Logic (Enhanced for Status Updates)
    * Sub-Task 1.1: Manage workflow, agent calls, data passing (short-term memory).
    * Sub-Task 1.2: Integrate with `MemoryManager` (LTM access).
    * Sub-Task 1.3: Implement advanced collaboration logic.
    * Sub-Task 1.4: Integrate structured logging.
    * Sub-Task 1.5: **Emit status updates** via the defined mechanism before calling an agent, after receiving output, during key internal steps (FR02, FR16).
    * Sub-Task 1.6: Call Evaluation Agent/Logic.
    * Sub-Task 1.7: Store final agent states for inspection.
* Task 2: Implement Report Aggregation (FR07) (As before).

### 5.5 - 5.8. Modules: Specialized Agents (**EHR, Imaging, Pathology, Guideline, Specialist**)
* Task 1: Implement Agent Logic & System Integration (Enhanced for Status Updates)
    * Sub-Task 1.1: Implement core analysis logic.
    * Sub-Task 1.2: Integrate structured logging.
    * Sub-Task 1.3: (Tool Agents): Use the Tool Interface/Registry.
    * Sub-Task 1.4: (LLM/Tool Calls): Utilize retry/fallback wrappers.
    * Sub-Task 1.5: (Optional): Interact with `MemoryManager` (LTM).
    * Sub-Task 1.6: Structure internal state for inspection.
    * Sub-Task 1.7: **Emit status updates** for key internal milestones if applicable (e.g., "Starting LLM call", "Parsing tool response") via mechanism provided by Coordinator (FR16).

### 5.10. Module: Evaluation Agent / Logic
* Task 1: Implement Self-Evaluation (FR14) (As before)
    * Sub-Task 1.1: Define evaluation criteria.
    * Sub-Task 1.2: Implement evaluation logic (rules or LLM).
    * Sub-Task 1.3: Append evaluation results.
    * Sub-Task 1.4: (Optional) Emit status updates during evaluation.

## 6. Future Considerations & Extensions

* Refined Medical Logic & Knowledge Base Integration.
* Real Tool Integration (beyond simulation).
* More Sophisticated Reasoning/Planning/Collaboration models.
* Enhanced User Interface (visualizations, history, interaction).
* User Feedback Loop integration with Long-Term Memory.

## 7. Success Metrics

* **SM1 (Assignment Completion):** All mandatory and bonus requirements from the technical assignment `README.md` are clearly implemented and demonstrable.
* **SM2 (Functionality):** System successfully processes valid JSON, utilizes all agent mechanisms, handles errors, logs, generates report, **and provides accurate real-time workflow visualization.**
* **SM3 (UI Functionality):** UI allows core workflow; workflow visualization updates correctly and smoothly; optional log/state view (if implemented) is functional.
* **SM4 (Code Quality):** Codebase is modular, readable, testable, and demonstrates clear architecture incorporating the specified features.
* **SM5 (Documentation Quality):** `README.md` comprehensively covers the system, architecture, features (incl. visualization), setup, usage, and AI reflection.

## 8. Open Issues / Assumptions

* **OI1 (Color Palette):** (As before) Color palette requires verification.
* **OI2 (Tool Simulation Detail):** (As before) Mocked tools return simple data.
* **OI3 (LLM API Key:** (As before) Requires valid Google Gemini API key.
* **OI4 (Scope & Focus):** Focus is demonstrating agent capabilities. Medical accuracy is secondary.
* **OI5 (Complexity & Time):** Comprehensive scope including visualization significantly increases complexity. Implementation likely needs prioritization or simplification.
* **OI6 (Evaluation Detail):** (As before) Self-evaluation mechanism will be basic initially.
* **OI7 (Status Update Mechanism):** Specific technology for real-time backend-to-frontend updates (WebSockets, SSE, polling) needs selection and implementation. This impacts both backend and frontend significantly.

---
