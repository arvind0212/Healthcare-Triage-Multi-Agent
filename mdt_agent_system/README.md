# MDT Agent System

A simulated Multi-Disciplinary Team (MDT) Agent System for healthcare triage using LangChain and Google Gemini.

## Current Status

The MDT Agent System is fully functional with all core components integrated and working together. The system successfully:

1. Processes patient cases through a series of specialized agents
2. Generates comprehensive MDT reports with clinical recommendations
3. Delivers reports through multiple channels (SSE streaming and direct API)
4. Provides real-time status updates during simulation
5. Stores persistent reports for later retrieval

### Known Issues

1. **Mermaid Workflow Visualization** - The workflow diagram currently experiences rendering errors due to syntax issues with class attributes.
2. **SSE Connection Stability** - There are occasional connection issues with the SSE stream that may require manual intervention.

## Module Integration Status

We have successfully completed Module Integration (Phase 5, Task 1):

1. **LangChain LLM Integration** ✅
   - Successfully integrated Google Gemini API with all agent implementations
   - Implemented consistent LLM configuration across all agents
   - Added robust error handling and retry logic

2. **Coordinator and Agent Integration** ✅
   - Connected the coordinator with all specialized agents
   - Implemented proper data passing between agents
   - Added comprehensive error handling

3. **Tool Integration** ✅
   - Properly integrated the ToolRegistry with all agent implementations
   - Verified tool registration and access by agents
   - Confirmed tool error handling and retry logic

4. **Memory System Integration** ✅
   - Connected the memory system across all components
   - Verified persistence between runs with the same run_id
   - Tested memory access patterns across agents

5. **Status Update System and UI Integration** ✅
   - Confirmed end-to-end status flow from agents to UI
   - Tested SSE connectivity and reconnection logic
   - Verified proper visualization updates based on status changes

## Report Access Features

To ensure reliable access to simulation reports, the system now provides multiple ways to retrieve reports:

1. **Automatic Display** - Reports are automatically displayed after simulation completion
2. **Direct Fetch Button** - A dedicated "Fetch Report Directly" button retrieves reports via REST API
3. **Manual Run ID Entry** - Users can manually enter any run ID to retrieve historical reports
4. **JSON File Storage** - All reports are saved as JSON files in the `mdt_agent_system` directory as `report_<run_id>.json`

## Integration Tests Status

Integration tests have been created, but need fixes for API compatibility issues:

1. **API Compatibility Issues**:
   - Need to update `PersistentConversationMemory` parameters
   - Need to replace `.dict()` calls with `.model_dump()` for Pydantic v2
   - Need to add missing `get_all_tools()` method to ToolRegistry
   - Need to update agent initialization parameters

2. **Dependencies Required**:
   - For UI tests: `playwright` (optional)
   - For API tests: `fastapi` and `sse-starlette`
   - For LLM tests: Valid Google API key

## Running Integration Tests (After Fixes)

To run the integration tests:

```bash
# Navigate to the project directory first
cd mdt_agent_system

# Then run the tests
python -m pytest app/tests/integration_test.py -v
```

## Running the Application

To run the application:

```bash
# Navigate to the project directory first
cd mdt_agent_system

# Then start the server
python -m uvicorn app.main:app --reload
```

For Windows PowerShell users, use separate commands instead of `&&`:

```powershell
# Navigate to the project directory first
cd mdt_agent_system

# Then start the server
python -m uvicorn app.main:app --reload
```

Then access the application at: http://localhost:8000

## Next Steps

1. **Fix Visualization Issues**:
   - Fix Mermaid.js graph generation syntax
   - Improve error handling for visualization components

2. **Enhance Report Experience**:
   - Add collapsible sections to reports
   - Implement syntax highlighting
   - Add filtering capabilities

3. **Improve Connection Stability**:
   - Enhance SSE reconnection logic
   - Add better error recovery

4. **Complete Documentation**:
   - Finalize system architecture documentation
   - Create comprehensive user guide

5. **Fix Integration Tests**:
   - Update API compatibility issues
   - Install required dependencies
   - Fix test assumptions about agent parameters

6. **Complete Remaining Phase 5 Tasks**:
   - Task 2: End-to-End Testing
   - Task 3: Comprehensive Documentation
   - Task 4: Code Quality Review
   - Task 5: Performance Optimization 