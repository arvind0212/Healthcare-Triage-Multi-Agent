# Simulated MDT Agent System - Development Tasks

This document outlines the development tasks for the Simulated MDT Agent System with LangChain integration. Tasks are organized by module for clarity and follow a logical progression that enables modular development and testing.

## Phase 1: Core System Setup & LangChain Integration

### Task 0: Environment & Dependencies Setup
* **Sub-Task 0.1:** Set up Python virtual environment
* **Sub-Task 0.2:** Install core dependencies:
  ```
  fastapi==0.104.1
  uvicorn==0.23.2
  pydantic==2.4.2
  python-multipart==0.0.6
  python-dotenv==1.0.0
  aiofiles==23.2.1
  sse-starlette==1.6.5
  google-generativeai==0.3.1
  langchain==0.1.0
  langchain-google-genai==0.0.5
  langchain-core==0.1.5
  ```
* **Sub-Task 0.3:** Set up directory structure:
  ```
  /app
    /api
    /agents
    /core
      /config
      /logging
      /schemas
      /tools
      /memory
    /utils
    /static
    /tests
  ```
* **Sub-Task 0.4:** Create basic entry points (main.py, app.py)

### Task 1: Configuration Management Module (NFR09)
* **Sub-Task 1.1:** Create `.env` file template with required parameters
* **Sub-Task 1.2:** Implement config loader using python-dotenv
* **Sub-Task 1.3:** Add config validation for required parameters
* **Sub-Task 1.4:** Create config singleton for application-wide access
* **Sub-Task 1.5:** Add unit tests for config loading and validation

### Task 2: Structured Logging Module with LangChain Callbacks (FR11)
* **Sub-Task 2.1:** Configure Python logging with JSON formatter
* **Sub-Task 2.2:** Create log file rotation and directory structure
* **Sub-Task 2.3:** Implement request ID/trace ID for correlation
* **Sub-Task 2.4:** Create custom LangChain callback handler for logging
* **Sub-Task 2.5:** Add log level configuration (from environment variables)
* **Sub-Task 2.6:** Add unit tests for logging functionality

### Task 3: Core Data Schemas Module (FR01, FR07)
* **Sub-Task 3.1:** Create PatientCase schema (Pydantic)
* **Sub-Task 3.2:** Create MDTReport schema (Pydantic)
* **Sub-Task 3.3:** Create StatusUpdate schema (Pydantic)
* **Sub-Task 3.4:** Create adapter models to convert between LangChain and system schemas
* **Sub-Task 3.5:** Add schema validation functions and JSON generation utilities
* **Sub-Task 3.6:** Add unit tests for schema validation

### Task 4: LangChain Tool Interface Module (FR05, FR13)
* **Sub-Task 4.1:** Create custom MDTTool class extending LangChain's BaseTool
* **Sub-Task 4.2:** Implement tool registration mechanism
* **Sub-Task 4.3:** Create pharmacology reference tool implementation
* **Sub-Task 4.4:** Create medical guideline reference tool implementation
* **Sub-Task 4.5:** Implement retry logic wrapper for tool execution
* **Sub-Task 4.6:** Add unit tests for tools with mock responses

### Task 5: LangChain Memory System Module (FR06)
* **Sub-Task 5.1:** Create JSON file adapter for LangChain's memory persistence
* **Sub-Task 5.2:** Implement ConversationBufferMemory with custom persistence
* **Sub-Task 5.3:** Create memory initialization and loading utilities
* **Sub-Task 5.4:** Implement memory transaction logging
* **Sub-Task 5.5:** Create memory inspection utilities (for FR12)
* **Sub-Task 5.6:** Add unit tests for memory persistence and retrieval

### Task 6: Status Update System Module (FR16, NFR13)
* **Sub-Task 6.1:** Create StatusUpdateService class
* **Sub-Task 6.2:** Implement custom LangChain callback for status updates
* **Sub-Task 6.3:** Create in-memory queue for status updates
* **Sub-Task 6.4:** Implement status update persistence (for recovery)
* **Sub-Task 6.5:** Add unit tests for status update mechanisms

### Task 7: Sample Data Creation
* **Sub-Task 7.1:** Create sample PatientCase.json
* **Sub-Task 7.2:** Create expected MDTReport.json template
* **Sub-Task 7.3:** Create sample agent prompt templates

## Phase 2: Backend API Implementation

### Task 1: FastAPI Backend Setup
* **Sub-Task 1.1:** Create FastAPI application with CORS configuration
* **Sub-Task 1.2:** Configure error handling middleware
* **Sub-Task 1.3:** Implement health check endpoint
* **Sub-Task 1.4:** Add dependency injection setup
* **Sub-Task 1.5:** Add unit tests for basic API functionality

### Task 2: Simulation API Endpoint
* **Sub-Task 2.1:** Create /simulate endpoint with file upload handling
* **Sub-Task 2.2:** Implement JSON validation against PatientCase schema
* **Sub-Task 2.3:** Create unique run_id generation
* **Sub-Task 2.4:** Implement background task for simulation processing
* **Sub-Task 2.5:** Add error handling and response formatting
* **Sub-Task 2.6:** Add integration test for simulation endpoint

### Task 3: Server-Sent Events (SSE) Implementation
* **Sub-Task 3.1:** Create /stream/{run_id} endpoint for SSE
* **Sub-Task 3.2:** Implement SSE generator function
* **Sub-Task 3.3:** Connect StatusUpdateService to SSE stream
* **Sub-Task 3.4:** Add reconnection support (with last-event-id)
* **Sub-Task 3.5:** Add error handling for stream interruptions
* **Sub-Task 3.6:** Test SSE functionality with mock status updates

### Task 4: Agent State and Log Access API
* **Sub-Task 4.1:** Create /logs/{run_id} endpoint
* **Sub-Task 4.2:** Create /state/{run_id}/{agent_id} endpoint
* **Sub-Task 4.3:** Implement filtering and pagination options
* **Sub-Task 4.4:** Add authentication if required (optional)
* **Sub-Task 4.5:** Test log and state access endpoints

## Phase 3: Agent Implementation with LangChain

### Task 1: LangChain LLM Integration Module
* **Sub-Task 1.1:** Create GoogleGenerativeAILLM wrapper
* **Sub-Task 1.2:** Configure retry mechanisms for API calls
* **Sub-Task 1.3:** Implement caching for LLM calls (optional)
* **Sub-Task 1.4:** Add logging callbacks for LLM interactions
* **Sub-Task 1.5:** Test LLM integration with sample prompts

### Task 2: LangChain Coordinator Implementation
* **Sub-Task 2.1:** Create coordinator agent prompt template
* **Sub-Task 2.2:** Set up AgentExecutor with appropriate tools
* **Sub-Task 2.3:** Implement SequentialChain for agent orchestration
* **Sub-Task 2.4:** Configure memory integration for context passing
* **Sub-Task 2.5:** Add status update callback integration
* **Sub-Task 2.6:** Implement error handling and recovery strategies
* **Sub-Task 2.7:** Add coordinator state tracking via LangChain
* **Sub-Task 2.8:** Test coordinator with mock agent responses

### Task 3: Specialized Agent Base Module
* **Sub-Task 3.1:** Create base agent configuration with common settings
* **Sub-Task 3.2:** Implement status update callback integration
* **Sub-Task 3.3:** Set up memory integration template
* **Sub-Task 3.4:** Create agent initialization utilities
* **Sub-Task 3.5:** Add logging integration
* **Sub-Task 3.6:** Test base agent functionality

### Task 4: EHR Agent Implementation
* **Sub-Task 4.1:** Create specialized prompt template
* **Sub-Task 4.2:** Implement LangChain agent configuration
* **Sub-Task 4.3:** Add any EHR-specific tools
* **Sub-Task 4.4:** Configure memory requirements
* **Sub-Task 4.5:** Test with sample patient data

### Task 5: Imaging Agent Implementation
* **Sub-Task 5.1:** Create specialized prompt template
* **Sub-Task 5.2:** Implement LangChain agent configuration
* **Sub-Task 5.3:** Add any imaging-specific tools
* **Sub-Task 5.4:** Configure memory requirements
* **Sub-Task 5.5:** Test with sample imaging data

### Task 6: Pathology Agent Implementation
* **Sub-Task 6.1:** Create specialized prompt template
* **Sub-Task 6.2:** Implement LangChain agent configuration
* **Sub-Task 6.3:** Add any pathology-specific tools
* **Sub-Task 6.4:** Configure memory requirements
* **Sub-Task 6.5:** Test with sample pathology data

### Task 7: Guideline Agent Implementation
* **Sub-Task 7.1:** Create specialized prompt template
* **Sub-Task 7.2:** Implement LangChain agent configuration
* **Sub-Task 7.3:** Register guideline tools with agent
* **Sub-Task 7.4:** Configure memory requirements
* **Sub-Task 7.5:** Test with sample guideline queries

### Task 8: Specialist Agent Implementation
* **Sub-Task 8.1:** Create specialized prompt template
* **Sub-Task 8.2:** Implement LangChain agent configuration
* **Sub-Task 8.3:** Add any specialist-specific tools
* **Sub-Task 8.4:** Configure memory requirements
* **Sub-Task 8.5:** Test with comprehensive patient data

### Task 9: Evaluation Agent Implementation (FR14)
* **Sub-Task 9.1:** Define evaluation criteria and rubric
* **Sub-Task 9.2:** Create evaluation prompt template
* **Sub-Task 9.3:** Implement LangChain evaluation tools
* **Sub-Task 9.4:** Add scoring and feedback generation
* **Sub-Task 9.5:** Integrate with MDTReport 
* **Sub-Task 9.6:** Test evaluation with sample reports

## Phase 4: Frontend Implementation

### Task 1: Basic UI Structure
* **Sub-Task 1.1:** Create HTML structure with key containers
* **Sub-Task 1.2:** Add CSS styles for layout and typography
* **Sub-Task 1.3:** Create color palette variables (UI05)
* **Sub-Task 1.4:** Implement responsive design basics
* **Sub-Task 1.5:** Test basic layout on target device sizes

### Task 2: File Input Component
* **Sub-Task 2.1:** Create file input with styling
* **Sub-Task 2.2:** Add drag-and-drop capability (optional)
* **Sub-Task 2.3:** Implement JSON validation
* **Sub-Task 2.4:** Add upload error handling
* **Sub-Task 2.5:** Test file upload with various file types

### Task 3: Simulation Control
* **Sub-Task 3.1:** Create "Run Simulation" button with states
* **Sub-Task 3.2:** Implement AJAX simulation request
* **Sub-Task 3.3:** Add loading/progress indicators
* **Sub-Task 3.4:** Implement error handling for API calls
* **Sub-Task 3.5:** Test simulation control flow

### Task 4: SSE Connection Handler
* **Sub-Task 4.1:** Implement SSE connection setup
* **Sub-Task 4.2:** Create event listeners for status updates
* **Sub-Task 4.3:** Add reconnection logic with exponential backoff
* **Sub-Task 4.4:** Implement connection status indicators
* **Sub-Task 4.5:** Test with simulated connection drops

### Task 5: Workflow Visualization with Mermaid.js
* **Sub-Task 5.1:** Create Mermaid.js initialization
* **Sub-Task 5.2:** Design base agent workflow diagram
* **Sub-Task 5.3:** Implement dynamic diagram updates from SSE events
* **Sub-Task 5.4:** Add CSS transitions for smooth updates
* **Sub-Task 5.5:** Create error state visualization
* **Sub-Task 5.6:** Test visualization with various status sequences

### Task 6: Report Display
* **Sub-Task 6.1:** Create report display container
* **Sub-Task 6.2:** Implement JSON formatting/pretty printing
* **Sub-Task 6.3:** Add copy-to-clipboard functionality
* **Sub-Task 6.4:** Create collapsible sections (optional)
* **Sub-Task 6.5:** Test with various sample reports

### Task 7: Log/State View (Optional)
* **Sub-Task 7.1:** Create tabbed interface for logs/state
* **Sub-Task 7.2:** Implement API calls to fetch data
* **Sub-Task 7.3:** Add auto-refresh capability
* **Sub-Task 7.4:** Implement filtering controls
* **Sub-Task 7.5:** Test with sample log/state data

### Task 8: Error Handling Display
* **Sub-Task 8.1:** Create error message components
* **Sub-Task 8.2:** Implement error visualization in workflow diagram
* **Sub-Task 8.3:** Add connection loss indicators
* **Sub-Task 8.4:** Implement retry mechanisms in UI
* **Sub-Task 8.5:** Test error handling with simulated failures

## Phase 5: System Integration and Testing

### Task 1: Module Integration
* **Sub-Task 1.1:** Integrate LangChain LLM with agent implementations
* **Sub-Task 1.2:** Connect coordinator with specialized agents
* **Sub-Task 1.3:** Integrate tools with appropriate agents
* **Sub-Task 1.4:** Connect memory systems across components
* **Sub-Task 1.5:** Integrate status update system with UI
* **Sub-Task 1.6:** Test each integration point individually

### Task 2: End-to-End Testing
* **Sub-Task 2.1:** Test complete workflow with sample data
* **Sub-Task 2.2:** Verify all status updates appear in visualization
* **Sub-Task 2.3:** Test error recovery scenarios
* **Sub-Task 2.4:** Verify report generation and formatting
* **Sub-Task 2.5:** Measure and optimize performance if needed

### Task 3: Comprehensive Documentation
* **Sub-Task 3.1:** Create project overview section
* **Sub-Task 3.2:** Document system architecture with diagrams
* **Sub-Task 3.3:** Detail LangChain integration points
* **Sub-Task 3.4:** Create setup and installation instructions
* **Sub-Task 3.5:** Write usage guide with examples
* **Sub-Task 3.6:** Document API endpoints and schemas
* **Sub-Task 3.7:** Add AI reflection section
* **Sub-Task 3.8:** Include scaling and extension considerations

### Task 4: Code Quality Review
* **Sub-Task 4.1:** Run linting and static analysis tools
* **Sub-Task 4.2:** Review error handling comprehensiveness
* **Sub-Task 4.3:** Check code comments and documentation
* **Sub-Task 4.4:** Verify consistent coding style
* **Sub-Task 4.5:** Conduct security review for basic vulnerabilities

### Task 5: Performance Optimization
* **Sub-Task 5.1:** Profile key operations
* **Sub-Task 5.2:** Optimize LLM prompt size and efficiency
* **Sub-Task 5.3:** Address any UI performance bottlenecks
* **Sub-Task 5.4:** Optimize memory usage patterns
* **Sub-Task 5.5:** Verify status update efficiency

## Development Approach Guidelines

1. **Modular Development:** Each module should be developed independently with clearly defined interfaces before integration. This enables parallel development and easier testing.

2. **Test-Driven Development:** Write tests for each module before or alongside implementation to ensure functionality meets requirements.

3. **Incremental Integration:** Integrate modules incrementally, starting with core components, then adding specialized functionality.

4. **Continuous Testing:** Re-run tests after each integration step to quickly catch integration issues.

5. **Documentation-First Approach:** Document interface contracts before implementation to ensure clear understanding of module boundaries.

6. **Status Updates:** Implement the status update mechanism early to enable visibility into the system's operation during development.

7. **Error Handling:** Build robust error handling into each module from the beginning rather than adding it later.

8. **LangChain Best Practices:** Follow LangChain patterns for agents, tools, chains, and memory to leverage the framework effectively.
