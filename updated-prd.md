# Product Requirements Document: Simulated MDT Agent System

**Version:** 1.5
**Status:** Updated Draft (LangChain Integration)
**Date:** 2025-04-25
**Author:** Gemini (as 100000x Seasoned Product Manager) with LangChain Integration
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
| FR07   | **Generate MDT Summary Report:** | Structured report (`MDTReport`) output JSON schema.                                                                                                                                                                         | G1, G3                             |
| FR08   | **Minimalistic UI:** | Single-page UI for input/output and visualization.                                                                                                                                                            | G4                                 |
| FR09   | **Clear Simulation Status & Observability Views:** | UI indicates running/complete/failed states. UI includes workflow visualization (FR15). Optionally include views for logs/agent state (FR12).                                                                  | G4, G2 (Observability), FR15, FR12 |
| FR10   | **Implement Retry/Fallback Logic:** | Key operations (LLM calls, critical simulated tool calls) include basic retry logic or fallback behavior.                                                                                                                | G2 (Robustness), G3                |
| FR11   | **Implement Structured Logging:** | Implement system-wide structured logging capturing key events, agent actions, errors, and timings.                                                                                                                    | G2 (Observability), G3             |
| FR12   | **Implement Agent State/Memory Inspection:** | Provide a mechanism (e.g., API endpoint, log analysis, optional UI view) to inspect agent state or memory contents.                                                                                                 | G2 (Observability), G3             |
| FR13   | **Implement Custom Tool Plugin Interface:** | Define a clear interface for adding new simulated tools that agents can discover and use. Refactor existing tool simulations.                                                                                         | G2 (Tool Use), G3, G5              |
| FR14   | **Implement Self-Evaluation Mechanism:** | Add a step or agent that assesses the final `MDTReport` based on predefined heuristics or an LLM prompt.                                                                                                       | G2 (Self-Evaluation), G3         |
| FR15   | **Implement Dynamic Workflow Visualization:** | The UI must display a real-time representation (e.g., flowchart) of the agent workflow during simulation. This visualization must highlight the active agent and display status updates (current task, handover, return). | G2 (Observability), G4             |
| FR16   | **Backend Status Updates for UI:** | The backend system (Coordinator/API) must push status updates (active agent, task description, status) to the frontend using **Server-Sent Events (SSE)** during simulation to power the visualization (FR15).                | G2 (Observability), G4, FR15       |
| FR17   | **Error Recovery & Reconnection:** | System must handle SSE connection drops and other common errors by implementing reconnection logic and preserving simulation state.                                                                                       | G2 (Robustness), G4                |

### 4.2. Non-Functional Requirements (NFR)

| ID     | Requirement                          | Details                                                                                                                            | Alignment              |
| :----- | :----------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------- | :--------------------- |
| NFR01  | **Code-Only Implementation:** | Backend logic purely in code (Python).                                                                                             | G3                     |
| NFR02  | **Modularity & Architecture:** | Clear separation of concerns (UI, Backend, Agents, Tools, Memory, Status Updates).                                                     | G3, G5                 |
| NFR03  | **Code Quality:** | Readable, maintainable, well-structured code.                                                                                        | G3                     |
| NFR04  | **Documentation:** | Comprehensive `README.md` covering all features including visualization, architecture, setup, usage, AI reflection.              | G3                     |
| NFR05  | **Performance:** | Simulation completion time < 2 minutes. Status updates (FR16) should be pushed with < 500ms delay for smooth visualization.                | G1, G4                 |
| NFR06  | **Ethical Considerations:** | Strictly synthetic data; clear disclaimers required.                                                                               | G1, G3                 |
| NFR07  | **Testability:** | Core logic, interfaces (Tool, Status Update), memory components should be testable.                                                  | G3, G5                 |
| NFR08  | **UI Responsiveness:** | UI functional on standard desktop screens (1024×768 minimum). Visualization should update smoothly.                                   | G4                     |
| NFR09  | **LLM Choice:** | Google Gemini API (Tier 1, targeting Flash-like models).                                                                             | G2, G3                 |
| NFR10  | **Log Format & Accessibility:** | Structured, parseable/accessible logs in JSON format.                                                                             | G2 (Observability)     |
| NFR11  | **Tool Interface Standard:** | Clear, consistently applied tool interface using LangChain's patterns.                                                             | G2 (Tool Use), G5      |
| NFR12  | **Memory Persistence Method:** | JSON file storage for simplicity and inspection.                                                                                  | G2 (Memory)            |
| NFR13  | **Status Update Mechanism:** | **Server-Sent Events (SSE)** for backend-to-frontend updates with reconnection capability.                                       | G2 (Observability), G4 |
| NFR14  | **Technology Stack:** | Backend: FastAPI, Pydantic. Frontend: HTML, CSS, JavaScript with Mermaid.js. LLM: Google Gemini API. LangChain for agents.                               | G3, G5                 |

### 4.3. User Interface (UI) Requirements

| ID     | Requirement                             | Details                                                                                                                                                                                                                                                                                                                                                                | Alignment            |
| :----- | :-------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------- |
| UI01   | **Layout:** | Single-page application layout. Ultra-minimalistic design. Includes a dedicated area for the workflow visualization.                                                                                                                                                                                                 | G4                   |
| UI02   | **Core Workflow:** | Upload JSON -> Run -> View Report/Error & Observe Visualization.                                                                                                                                                                                                                                              | G4, FR01, FR08, FR09 |
| UI03   | **Components:** | - File Input Area - "Run Simulation" Button - **Workflow Visualization Area:** Displays dynamic flowchart/diagram (FR15). - Status Indicator (can be integrated into visualization). - Report Display Area - Disclaimer Banner - (Optional) Tab or section for logs/state info (FR09, FR12).                                           | G4, FR09, FR12, FR15 |
| UI04   | **Workflow Visualization Behavior:** | - Represents agents/steps visually (e.g., nodes in a flowchart using Mermaid.js). - Receives real-time updates via SSE (FR16). - Highlights the **currently active agent** (e.g., green color). - Displays **current status text** (e.g., "Summarizing EHR", "Calling LLM for Imaging"). - Updates dynamically with smooth transitions (CSS transitions for state changes). - Shows connections between agents. | FR15                 |
| UI05   | **Color Palette:** | Minimalistic palette. Use distinct colors for states (e.g., green for active, grey for inactive/pending, red for error). - Primary Bg: `#FFFFFF` / `#F8F9FA` - Secondary Bg/Containers: `#E9ECEF` - Primary Text: `#212529` - Accent (Buttons/Headers): `#4b2981` - Active Agent Highlight: `#28a745` (Green) - Error Highlight: `#dc3545` (Red) - Other accents: `#43bbc2`, `#da3c72` | G4                   |
| UI06   | **Typography:** | Clean, readable sans-serif font (System UI stack). Consistent font sizes. Status text in visualization must be legible.                                                                                                                                                                                                             | G4                   |
| UI07   | **Error Handling Display:** | Display user-friendly error messages. Workflow visualization must indicate where an error occurred. Connection loss indicator with automatic reconnection status.                                                                                                                                                    | FR09, FR17           |
| UI08   | **Responsive Design:** | UI must adapt to desktop screens (1024×768 minimum). Visualization should scale appropriately.                                                                                                                                                                                                      | G4, NFR08            |

## 5. Technical Architecture & System Design

### 5.1. Technology Stack

| Component | Technology | Justification |
|-----------|------------|---------------|
| **Backend Framework** | FastAPI | High performance, built-in validation with Pydantic, async support for SSE |
| **Data Validation** | Pydantic | Type validation, schema definition, integration with FastAPI |
| **Frontend Core** | HTML5, CSS, JavaScript | Simple, lightweight implementation without complex frameworks |
| **Visualization** | Mermaid.js | Simple syntax, built for flow diagrams, easily updated via JavaScript |
| **Real-time Updates** | Server-Sent Events (SSE) | Native browser support, unidirectional updates ideal for visualization |
| **LLM Integration** | Google Gemini API | As specified in requirements |
| **Agent Framework** | LangChain | Ready-made components for agents, tools, chains, and memory systems |
| **Persistence** | JSON files | Simple, human-readable, easily inspectable |
| **Logging** | Python logging module with JSON formatter | Standard library, structured output |

### 5.2. Core Data Schemas

#### 5.2.1. PatientCase Schema
```python
class PatientCase(BaseModel):
    patient_id: str
    demographics: Dict[str, Any]  # age, gender, etc.
    medical_history: List[Dict[str, Any]]
    current_condition: Dict[str, Any]
    imaging_results: Optional[Dict[str, Any]]
    pathology_results: Optional[Dict[str, Any]]
    lab_results: Optional[List[Dict[str, Any]]]
```

#### 5.2.2. MDTReport Schema
```python
class MDTReport(BaseModel):
    patient_id: str
    summary: str
    ehr_analysis: Dict[str, Any]
    imaging_analysis: Optional[Dict[str, Any]]
    pathology_analysis: Optional[Dict[str, Any]]
    guideline_recommendations: List[Dict[str, Any]]
    specialist_assessment: Dict[str, Any]
    treatment_options: List[Dict[str, Any]]
    evaluation_score: Optional[float]
    evaluation_comments: Optional[str]
    timestamp: datetime
```

#### 5.2.3. AgentInput/Output Schema
```python
# Using LangChain's integrated agent message schemas
from langchain.schema import AgentAction, AgentFinish

# Custom wrapper for compatibility with existing systems
class AgentInput(BaseModel):
    agent_id: str
    task: str
    data: Dict[str, Any]
    context: Optional[Dict[str, Any]]

class AgentOutput(BaseModel):
    agent_id: str
    status: str  # "SUCCESS", "ERROR", "PARTIAL"
    data: Dict[str, Any]
    error: Optional[str]
    metadata: Optional[Dict[str, Any]]
    
    # Method to convert to LangChain's AgentFinish
    def to_agent_finish(self) -> AgentFinish:
        return AgentFinish(
            return_values={"output": self.data, "status": self.status},
            log=f"Agent {self.agent_id} finished with status {self.status}"
        )
```

#### 5.2.4. StatusUpdate Schema
```python
class StatusUpdate(BaseModel):
    agent_id: str  # The agent emitting the status or being acted upon
    status: str    # "ACTIVE", "DONE", "ERROR", "WAITING"
    message: str   # Human-readable status message
    timestamp: datetime
    details: Optional[Dict[str, Any]]  # Additional info if needed
    run_id: str    # To associate updates with a specific simulation run
```

#### 5.2.5. Tool Interface Schema
```python
# Using LangChain's Tool interface instead of custom implementation
from langchain.tools import BaseTool

class MDTTool(BaseTool):
    name: str
    description: str
    
    def _run(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with the given parameters."""
        # Implementation specific to each tool
        pass
        
    async def _arun(self, **kwargs) -> Dict[str, Any]:
        """Async implementation of tool execution."""
        # Default to sync implementation if not overridden
        return self._run(**kwargs)
```

#### 5.2.6. Memory Schema
```python
# Leveraging LangChain's memory abstractions
from langchain.memory import ConversationBufferMemory, FileChatMessageHistory

# Custom wrapper for compatibility with existing systems
class MemoryItem(BaseModel):
    id: str
    type: str  # "PATIENT_CASE", "MDT_REPORT", "AGENT_STATE"
    content: Dict[str, Any]
    timestamp: datetime
    metadata: Optional[Dict[str, Any]]

# Using LangChain's memory persistence with custom JSON store
class JSONFileMemoryStore:
    """Implementation that leverages LangChain's memory concepts with JSON storage"""
    # Implementation details...
```

## 6. Detailed Feature Breakdown (Modules -> Tasks -> Sub-Tasks)

### 6.1. Module: UI Frontend
* Task 1: Implement UI Structure
    * Sub-Task 1.1: Set up basic HTML structure, including area for workflow visualization.
    * Sub-Task 1.2: Apply CSS for layout, colors (UI05), typography (UI06).
* Task 2: Implement File Input Component
    * Sub-Task 2.1: Create file input with validation for JSON files.
    * Sub-Task 2.2: Add drag-and-drop support (optional).
* Task 3: Implement Simulation Control
    * Sub-Task 3.1: Create "Run Simulation" button.
    * Sub-Task 3.2: Implement AJAX call to backend simulation endpoint.
    * Sub-Task 3.3: Setup SSE connection handling with reconnection logic.
    * Sub-Task 3.4: Implement loading state display.
* Task 4: Implement Report Display
    * Sub-Task 4.1: Create area for report output.
    * Sub-Task 4.2: Implement JSON formatting/pretty-printing.
    * Sub-Task 4.3: Add copy-to-clipboard functionality (optional).
* Task 5: Implement Disclaimer
    * Sub-Task 5.1: Add disclaimer banner with appropriate text.
* Task 6: Implement Workflow Visualization Component
    * Sub-Task 6.1: Initialize Mermaid.js for diagram rendering.
    * Sub-Task 6.2: Define base diagram structure (nodes for each agent).
    * Sub-Task 6.3: Implement SSE event listener for status updates.
    * Sub-Task 6.4: Implement diagram update logic based on status updates.
    * Sub-Task 6.5: Add CSS transitions for smooth visual updates.
    * Sub-Task 6.6: Implement error state visualization.
    * Sub-Task 6.7: Add connection loss/reconnection indicator.
* Task 7: Implement Log/State View (Optional)
    * Sub-Task 7.1: Create tabbed interface for logs/state.
    * Sub-Task 7.2: Implement API call to fetch logs/state.
    * Sub-Task 7.3: Add auto-refresh capability.

### 6.2. Module: Backend API / Main Application
* Task 1: Setup Backend Framework
    * Sub-Task 1.1: Initialize FastAPI project structure.
    * Sub-Task 1.2: Configure CORS, logging, error handling.
    * Sub-Task 1.3: Define and implement the primary API endpoint (`/simulate`).
    * Sub-Task 1.4: Set up SSE endpoint and generator function (`/stream/<run_id>`).
* Task 2: Implement Simulation Endpoint
    * Sub-Task 2.1: Handle file upload/JSON payload.
    * Sub-Task 2.2: Validate incoming JSON against PatientCase schema.
    * Sub-Task 2.3: Generate unique run_id for the simulation.
    * Sub-Task 2.4: Create SSE generator for status updates.
    * Sub-Task 2.5: Start simulation in background task.
    * Sub-Task 2.6: Instantiate and invoke the Coordinator Agent with status update callback.
    * Sub-Task 2.7: Handle potential errors, sending error status updates.
    * Sub-Task 2.8: Store final MDTReport for retrieval.
* Task 3: Implement Log/State Access Endpoint
    * Sub-Task 3.1: Create endpoint for retrieving logs (`/logs/<run_id>`).
    * Sub-Task 3.2: Create endpoint for agent state inspection (`/state/<run_id>/<agent_id>`).
    * Sub-Task 3.3: Implement filtering and pagination (optional).

### 6.3. Module: Core System & Shared Components
* Task 1: Implement Configuration Management
    * Sub-Task 1.1: Create `.env` file structure.
    * Sub-Task 1.2: Implement configuration loading (using `python-dotenv`).
    * Sub-Task 1.3: Add validation for required configurations.
* Task 2: Implement Structured Logging
    * Sub-Task 2.1: Configure Python logging with JSON formatter.
    * Sub-Task 2.2: Create log file rotation setup.
    * Sub-Task 2.3: Add request ID/trace ID to logs for correlation.
    * Sub-Task 2.4: Implement log level configuration.
    * Sub-Task 2.5: Configure LangChain callbacks for logging agent actions.
* Task 3: Implement Tool Interface & Registry
    * Sub-Task 3.1: Use LangChain's `BaseTool`.
    * Sub-Task 3.2: Use LangChain's tool registration pattern.
    * Sub-Task 3.3: Create mock MDT tools by extending LangChain's `BaseTool`.
    * Sub-Task 3.4: Add tool execution error handling and retry logic.
    * Sub-Task 3.5: Configure tool registration with LangChain agents.
* Task 4: Implement Memory Management
    * Sub-Task 4.1: Use LangChain's `ConversationBufferMemory` for short-term.
    * Sub-Task 4.2: Use LangChain's memory systems with custom persistence.
    * Sub-Task 4.3: Create JSON file persistence adapter for LangChain memory.
    * Sub-Task 4.4: Implement write/read/query methods compatible with LangChain.
    * Sub-Task 4.5: Add transaction logging for memory operations.
* Task 5: Implement Basic Retry/Fallback Logic
    * Sub-Task 5.1: Create retry decorator with configurable attempts/backoff.
    * Sub-Task 5.2: Implement fallback strategies for critical operations.
    * Sub-Task 5.3: Add circuit breaker pattern for external services (optional).
    * Sub-Task 5.4: Configure LangChain retry handlers for LLM calls.
* Task 6: Define Status Update Structure & Mechanism
    * Sub-Task 6.1: Implement `StatusUpdate` Pydantic model.
    * Sub-Task 6.2: Create status update queue/channel implementation.
    * Sub-Task 6.3: Implement status update callback mechanism using LangChain callbacks.
    * Sub-Task 6.4: Add status update persistence for recovery.
* Task 7: Define Core Data Schemas
    * Sub-Task 7.1: Implement `PatientCase` Pydantic model.
    * Sub-Task 7.2: Implement `MDTReport` Pydantic model.
    * Sub-Task 7.3: Adapt LangChain's agent I/O patterns.
    * Sub-Task 7.4: Add JSON schema validation and generation.
* Task 8: Create Sample Data
    * Sub-Task 8.1: Create sample `PatientCase.json`.
    * Sub-Task 8.2: Create expected `MDTReport.json` for testing.

### 6.4. Module: Coordinator Agent
* Task 1: Implement Orchestration & Collaboration Logic
    * Sub-Task 1.1: Use LangChain's `AgentExecutor` with custom prompt.
    * Sub-Task 1.2: Implement sequential agent calling workflow using LangChain's `SequentialChain`.
    * Sub-Task 1.3: Add data passing between agents (short-term memory) using LangChain's memory systems.
    * Sub-Task 1.4: Integrate with LangChain memory systems for LTM access.
    * Sub-Task 1.5: Implement status update emission using LangChain callbacks.
    * Sub-Task 1.6: Add error handling and recovery logic.
    * Sub-Task 1.7: Implement agent state tracking using LangChain tracing.
* Task 2: Implement Report Aggregation
    * Sub-Task 2.1: Collect output from all agents using LangChain's chain output collection.
    * Sub-Task 2.2: Format data into `MDTReport` structure.
    * Sub-Task 2.3: Validate final report against schema.
    * Sub-Task 2.4: Store report in memory system.

### 6.5. - 6.9. Modules: Specialized Agents
* Task 1: Implement Agent Logic & System Integration
    * Sub-Task 1.1: Use LangChain's agent classes.
    * Sub-Task 1.2: Implement specific agents using LangChain's `Agent` framework:
        * EHR Agent: Parse/analyze patient history (LangChain Agent with specialized prompt)
        * Imaging Agent: Analyze imaging results (LangChain Agent with specialized prompt)
        * Pathology Agent: Analyze pathology results (LangChain Agent with specialized prompt)
        * Guideline Agent: Apply medical guidelines (LangChain Agent with Tool access)
        * Specialist Agent: Provide expert assessment (LangChain Agent with specialized prompt)
    * Sub-Task 1.3: Configure LangChain callbacks for structured logging.
    * Sub-Task 1.4: Add tool usage by registering tools with appropriate agents.
    * Sub-Task 1.5: Configure LLM integration with retry logic in LangChain.
    * Sub-Task 1.6: Configure memory access for applicable agents.
    * Sub-Task 1.7: Structure internal state for inspection using LangChain tracing.
    * Sub-Task 1.8: Implement status update emission through LangChain callbacks.

### 6.10. Module: Evaluation Agent / Logic
* Task 1: Implement Self-Evaluation
    * Sub-Task 1.1: Define evaluation criteria/rubric.
    * Sub-Task 1.2: Implement evaluation logic using LangChain's evaluation tools.
    * Sub-Task 1.3: Calculate evaluation score.
    * Sub-Task 1.4: Generate evaluation comments.
    * Sub-Task 1.5: Append evaluation results to MDTReport.
    * Sub-Task 1.6: Emit status updates during evaluation.

## 7. Implementation Dependencies & Flow

### 7.1. Core Dependencies
```
fastapi==0.104.1
uvicorn==0.23.2
pydantic==2.4.2
python-multipart==0.0.6
python-dotenv==1.0.0
aiofiles==23.2.1
sse-starlette==1.6.5
google-generativeai==0.3.1
langchain==0.0.1
```

### 7.2. Implementation Flow & Dependencies

1. **Setup Environment & Core Components** (No dependencies)
   - Setup virtual environment
   - Install dependencies
   - Configure environment variables

2. **Implement Core System Components** (Depends on Setup)
   - Configuration Management
   - Structured Logging
   - Core Data Schemas
   - Tool Interface & Registry
   - Memory Management
   - Status Update Mechanism

3. **Implement Backend API** (Depends on Core System)
   - FastAPI setup
   - Simulation endpoint (basic)
   - SSE implementation

4. **Implement Basic UI** (Depends on Backend API)
   - HTML/CSS structure
   - File input
   - Simulation control
   - Basic visualization setup

5. **Implement Coordinator Agent** (Depends on Core System)
   - Orchestration logic
   - Status update integration
   - Report aggregation (basic)

6. **Implement Specialized Agents** (Depends on Coordinator & Core System)
   - Base agent class
   - Individual agent implementations
   - Tool integration
   - LLM integration

7. **Implement Evaluation Logic** (Depends on Specialized Agents)
   - Evaluation criteria
   - Integration with MDTReport

8. **Complete UI Implementation** (Depends on Backend & Coordinator)
   - Full visualization functionality
   - Report display
   - Error handling
   - Optional log/state view

9. **Testing & Documentation** (Depends on all above)
   - Unit tests
   - Integration tests
   - UI tests
   - Comprehensive README

## 8. Success Metrics

* **SM1 (Assignment Completion):** All mandatory and bonus requirements from the technical assignment `README.md` are clearly implemented and demonstrable.
* **SM2 (Functionality):** System successfully processes valid JSON, utilizes all agent mechanisms, handles errors, logs, generates report, and provides accurate real-time workflow visualization.
* **SM3 (UI Functionality):** UI allows core workflow; workflow visualization updates correctly and smoothly; optional log/state view (if implemented) is functional.
* **SM4 (Code Quality):** Codebase is modular, readable, testable, and demonstrates clear architecture incorporating the specified features.
* **SM5 (Documentation Quality):** `README.md` comprehensively covers the system, architecture, features (incl. visualization), setup, usage, and AI reflection.

## 9. Error Handling & Recovery Strategies

### 9.1. Backend Error Categories
1. **Input Validation Errors** - Invalid JSON or schema violations
2. **LLM Service Errors** - API unavailability, rate limiting, unexpected responses
3. **Tool Execution Errors** - Failures in simulated tools
4. **Memory Access Errors** - File access/write issues
5. **Internal Logic Errors** - Bugs or unexpected conditions

### 9.2. Frontend Error Categories
1. **Network Errors** - Failed API calls, timeouts
2. **SSE Connection Errors** - Connection drops, timeout, invalid events
3. **Visualization Rendering Errors** - Mermaid.js syntax/rendering issues
4. **Browser Compatibility Issues** - Feature support variances

### 9.3. Recovery Strategies
1. **SSE Reconnection Logic** - Automatic reconnection with exponential backoff
2. **Simulation State Preservation** - Save state to allow resuming after interruptions
3. **LLM Retry Logic** - Multiple attempts with backoff for transient failures
4. **Fallback Content** - Default/cached content when primary mechanisms fail
5. **Error Visibility** - Clear error messages and visualization of failure points

## 10. Testing Strategy

### 10.1. Unit Testing
* Test individual components in isolation (Tools, Memory Manager, Agents)
* Mock dependencies and external services
* Focus on core logic and edge cases

### 10.2. Integration Testing
* Test component interactions (Coordinator + Agents)
* Test API endpoints with simulated requests
* Test SSE stream functionality

### 10.3. UI Testing
* Test file upload and validation
* Test visualization updates with mocked status events
* Test error handling and recovery

### 10.4. End-to-End Testing
* Complete workflow with sample data
* Performance under normal conditions
* Error recovery scenarios

## 11. Future Considerations & Extensions

* Refined Medical Logic & Knowledge Base Integration.
* Real Tool Integration (beyond simulation).
* More Sophisticated Reasoning/Planning/Collaboration models.
* Enhanced User Interface (visualizations, history, interaction).
* User Feedback Loop integration with Long-Term Memory.
* Distributed agent execution for scalability.
* Real-time agent communication patterns.
* Advanced state machine for workflow orchestration.

---
