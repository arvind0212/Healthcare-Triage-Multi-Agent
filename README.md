# Healthcare Triage Multi-Agent System

## Problem Statement

Healthcare teams often need to collaborate efficiently to diagnose and plan treatment for complex patient cases. This traditionally occurs in Multi-Disciplinary Team (MDT) meetings, where specialists from different areas review patient data and collaboratively form a care plan. However, these meetings are time-intensive, require coordination of busy schedules, and may suffer from information overload or cognitive biases.

The Healthcare Triage Multi-Agent System addresses these challenges by creating an autonomous AI system that:

1. Coordinates multiple specialized medical AI agents to analyze patient data
2. Ensures comprehensive review of all medical information sources
3. Compares findings against established medical guidelines
4. Provides a summarized report to support clinical decision-making
5. Maintains a record of the analytical process for transparency and future reference

This system doesn't replace human medical expertise but provides a structured initial analysis to streamline the MDT process, highlight important considerations, and ensure all relevant data is properly integrated.

## System Architecture

### Overview

The system uses a multi-agent architecture with specialized agents coordinated by a central orchestrator. This mimics the structure of a real medical MDT with different specialists contributing their expertise.

![System Architecture Diagram]

### Core Components

#### 1. Coordinator
- Orchestrates the multi-agent workflow
- Maintains the context between agent steps
- Tracks status of each agent's work
- Assembles the final MDT report

#### 2. Specialized Agents
- **EHR Agent**: Analyzes Electronic Health Record data
- **Imaging Agent**: Interprets imaging studies
- **Pathology Agent**: Reviews pathology findings
- **Guideline Agent**: Applies medical guidelines to the case
- **Specialist Agent**: Provides domain expertise assessment
- **Evaluation Agent**: Evaluates consistency across analyses
- **Summary Agent**: Creates the final comprehensive report

#### 3. Memory System
- **Short-term Memory**: Session-specific context
- **Persistent Memory**: Long-term storage of past agent interactions
- **Memory Manager**: Handles different memory types and persistence

#### 4. Tools
- **Medical Reference Tools**: Access to pharmacology and guideline data
- **Tool Registry**: Manages available tools for agent use

#### 5. Supporting Infrastructure
- **Logging System**: Comprehensive logging of agent activities
- **Status Updates**: Real-time tracking of system progress
- **Schema Validation**: Ensures data integrity across agent interactions

### Agent Workflow

The system implements a sophisticated agentic workflow that follows these steps:

1. **Initialization**:
   - Patient case is submitted with EHR data, imaging reports, pathology findings
   - Coordinator creates a unique run ID and initializes the agent context
   - Status service begins tracking the execution process

2. **Sequential Agent Execution**:
   - **EHR Analysis Phase**: EHR Agent extracts and analyzes patient history, medications, allergies, lab results
   - **Imaging Analysis Phase**: Imaging Agent processes radiological findings, building on EHR context
   - **Pathology Analysis Phase**: Pathology Agent reviews biopsy/histology results with awareness of previous findings
   - **Guideline Application Phase**: Guideline Agent compares the case against established medical protocols
   - **Specialist Assessment Phase**: Specialist Agent applies domain-specific expertise to the combined analyses
   - **Evaluation Phase**: Evaluation Agent checks for consistency and identifies potential conflicts
   - **Summary Phase**: Summary Agent creates a comprehensive, structured report

3. **Tool Use During Analysis**:
   - The Guideline Agent invokes specialized tools for accessing medical guidelines and recommendations
   - Tool responses are incorporated into agent reasoning
   - Each tool operation is logged for traceability

4. **Memory Integration**:
   - Short-term memory: The AgentContext provides immediate context between agent steps
   - Each agent can access outputs from previous agents
   - Session memory is maintained for the duration of a single MDT analysis
   - Long-term persistent memory allows agents to reference past similar cases

5. **Output Generation**:
   - Each agent produces a structured output with standardized sections
   - The Summary Agent creates the final MDT report with treatment recommendations
   - All agent outputs are preserved for transparency

### Tool Implementation Details

The system implements a modular tool framework that allows agents to access external information sources. For this implementation, we've created a simulated tool that mimics real-world medical reference systems:

#### Tool Architecture

1. **Base Tool Class (`MDTTool`)**
   - Serves as the foundation for all tools
   - Implements a consistent interface with `name`, `description`, and `_run` methods
   - Provides error handling and logging for all tool calls
   - Located in `mdt_agent_system/app/core/tools/base.py`

2. **Tool Registry**
   - Manages the collection of available tools
   - Provides a discovery mechanism for agents to find appropriate tools
   - Implements a singleton pattern to ensure consistent tool access
   - Located in `mdt_agent_system/app/core/tools/registry.py`

3. **Medical Reference Tool**
   - `GuidelineReferenceTool`: Accesses medical guidelines and recommendations for specific conditions
   - Located in `mdt_agent_system/app/core/tools/medical.py`

#### Tool Mocking Approach

Rather than integrating with real external APIs (which would introduce dependencies and potential rate limits), we implemented a mock tool that:

1. **Simulates Real-World Behavior**:
   - The tool contains a curated dataset of representative medical information
   - For the `GuidelineReferenceTool`, we incorporated simplified versions of actual medical guidelines (e.g., AHA/ACC guidelines for chest pain)

2. **Implements Realistic Interfaces**:
   - The tool accepts the same parameters it would in a production environment
   - Returns structured data in formats consistent with real medical reference APIs
   - Includes appropriate error handling and "not found" responses

3. **Enables Extensibility**:
   - The tool architecture allows for easy replacement with real API calls in the future
   - New tools can be added by simply extending the `MDTTool` base class and registering with the registry

Example of our mocked tool implementation:

```python
class GuidelineReferenceTool(MDTTool):
    """Tool for accessing medical guidelines."""
    name: str = "guideline_reference"
    description: str = "Access medical guidelines and recommendations"
    
    def _run(self, condition: str, **kwargs: Any) -> Dict[str, Any]:
        """Simulate guideline reference lookup."""
        # Simulated data - in production would query a real guideline database
        sample_guidelines = {
            "chest_pain": {
                "source": "AHA/ACC",
                "version": "2021",
                "recommendations": [
                    "Perform initial risk stratification",
                    "Obtain 12-lead ECG within 10 minutes",
                    "Consider early cardiac biomarkers"
                ],
                "risk_factors": [
                    "Age > 65",
                    "Known CAD",
                    "Diabetes",
                    "Hypertension"
                ]
            },
            "type_2_diabetes": {
                "source": "ADA",
                "version": "2024",
                "recommendations": [
                    "Regular HbA1c monitoring",
                    "Lifestyle modifications",
                    "Consider metformin as first-line therapy"
                ],
                "targets": {
                    "HbA1c": "< 7.0%",
                    "Blood Pressure": "< 140/90 mmHg"
                }
            }
        }
        
        # Simple fuzzy matching
        condition = condition.lower()
        for disease, info in sample_guidelines.items():
            if disease in condition:
                return {
                    "status": "success",
                    "condition": disease,
                    "guidelines": info
                }
        
        return {
            "status": "not_found",
            "message": f"No guidelines found for condition: {condition}"
        }
```

#### Tool Usage in the Guideline Agent

The Guideline Agent invokes this tool during its reasoning process:

1. **Access Pattern**:
   - The agent retrieves the tool from the registry by name
   - Tool calls are fully typed and validated
   - Results are incorporated into the agent's reasoning chain

2. **Integration with LLM Reasoning**:
   - The tool is presented to the LLM as an available capability
   - The LLM decides when to use the tool based on the current analysis needs
   - Tool results expand the LLM's knowledge within a specific interaction

3. **Logging and Traceability**:
   - Each tool invocation is logged with input parameters and response
   - This creates an audit trail of information sources used during analysis
   - Helps explain agent conclusions by revealing the data they referenced

This approach to tool mocking allows us to:
- Develop and test the agent system without external dependencies
- Ensure deterministic behavior for testing and demonstrations
- Create a clear separation between the agent logic and external data sources
- Prepare for future integration with real medical APIs and databases

## Setup Instructions

### Prerequisites
- Python 3.9+
- pip package manager
- Google Gemini API key (free tier available)

### Installation
1. Clone the repository:
   ```
   git clone https://github.com/your-username/Healthcare-Triage-Multi-Agent.git
   cd Healthcare-Triage-Multi-Agent
   ```

2. Install dependencies:
   ```
   pip install -e .
   ```

3. Set up environment variables:
   ```
   # Create a .env file with your API keys
   echo "GOOGLE_API_KEY=your_gemini_api_key_here" > .env
   ```

### Running the System
1. Start the system with uvicorn:
   ```
   python -m uvicorn app.main:app --reload
   ```

2. To run tests:
   ```
   pytest mdt_agent_system/app/tests/
   ```

### Why We Use Google Gemini
This implementation uses Google's Gemini LLM for several reasons:
- **Free Usage Tier**: Generous free quota for development and testing
- **Powerful Capabilities**: Strong medical reasoning capabilities comparable to other leading models
- **Low Latency**: Fast response times for multi-agent interactions
- **Robust API**: Well-designed API with good documentation and stability

Gemini provides the power needed for sophisticated healthcare reasoning while keeping development costs low. The system architecture is model-agnostic and can be easily switched to use other LLMs if needed.

## Reflection on AI Assistance

During the development of this system, I leveraged AI assistance tools in several ways:

### Helpful Applications:
- **Architectural Design**: Used AI to brainstorm different agent system architectures before selecting the MDT-based approach
- **Code Structure**: Generated initial class skeletons to ensure consistent patterns across agents
- **Documentation**: Received suggestions for clearer docstrings and improved explanations
- **Debugging**: Used AI to help identify logical issues in the agent coordination flow

### Limitations and Manual Work:
- **Domain Knowledge**: Had to manually review and correct AI-suggested medical terminology and workflow patterns
- **Complex Logic**: The multi-agent orchestration required significant manual refinement as AI suggestions didn't always account for the complexity of agent interactions
- **Error Handling**: Needed to manually enhance error recovery strategies beyond what AI tools initially suggested
- **Testing**: Created targeted test cases manually to address edge cases in the agent reasoning process

AI tools were most valuable as collaboration partners for code structure and pattern suggestions, while the core agent reasoning patterns and domain-specific implementations required more extensive human oversight.

## Extension Considerations

### Future Enhancements
- **Real-time Collaboration**: Add support for human experts to join the agent workflow at key decision points
- **Additional Specialized Agents**: Expand with more medical specialty agents (e.g., cardiology, neurology)
- **Enhanced Visualization**: Develop better ways to visualize the agent reasoning process
- **Improved Memory**: Implement more sophisticated retrieval for past similar cases
- **Mobile Interface**: Create a companion mobile app for on-the-go access to MDT reports

### Technical Considerations
- The current architecture could be enhanced with a more robust message bus for improved agent communication
- A more sophisticated memory system would benefit from vector database integration
- Containerization would improve deployment flexibility and scaling capabilities

## Conclusion

The Healthcare Triage Multi-Agent System demonstrates how specialized AI agents can collaborate to address complex analytical tasks in healthcare. By modeling the system after real MDT workflows, it provides a structured approach to patient case analysis while maintaining the transparency and traceability essential in medical applications. 