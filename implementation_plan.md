# MDT Agent System Implementation Plan

## Overview
This document outlines the step-by-step implementation plan for upgrading the MDT agent system to use structured markdown outputs and improved medical prompts.

## Phase 1: Core Infrastructure (Week 1)

### 1. Base Schema Updates
```python
# mdt_agent_system/app/core/schemas/agent_output.py

from pydantic import BaseModel
from typing import Dict, Any, Optional

class AgentOutput(BaseModel):
    markdown_content: str
    metadata: Dict[str, Any]
    legacy_output: Optional[Dict[str, Any]] = None
```

### 2. Output Parser Implementation
```python
# mdt_agent_system/app/core/output_parser.py

class MDTOutputParser:
    def parse_llm_output(self, llm_output: str) -> AgentOutput:
        """Parse LLM output into structured format."""
        try:
            # Split on markdown and metadata sections
            parts = llm_output.split("---MARKDOWN---")
            if len(parts) != 2:
                raise ValueError("Missing MARKDOWN section")
            
            markdown_and_metadata = parts[1].split("---METADATA---")
            if len(markdown_and_metadata) != 2:
                raise ValueError("Missing METADATA section")
            
            markdown_content = markdown_and_metadata[0].strip()
            metadata = json.loads(markdown_and_metadata[1].strip())
            
            return AgentOutput(
                markdown_content=markdown_content,
                metadata=metadata
            )
        except Exception as e:
            logger.error(f"Error parsing LLM output: {e}")
            # Return a basic structure if parsing fails
            return AgentOutput(
                markdown_content=llm_output,
                metadata={"error": "Failed to parse structured output"}
            )
```

## Phase 2: Agent Updates (Weeks 2-3)

### 1. Specialist Agent (Pilot - Day 1-3)
```python
# mdt_agent_system/app/agents/specialist_agent.py

class SpecialistAgent(BaseSpecializedAgent):
    def _get_prompt_template(self) -> str:
        with open("prompts/specialist_prompt.txt", "r") as f:
            return f.read()
    
    async def process(self, patient_case: PatientCase, context: Dict[str, Any]) -> AgentOutput:
        # Updated process method using new output format
        agent_input = self._prepare_input(patient_case, context)
        llm_output = await self._run_analysis(agent_input)
        return self.output_parser.parse_llm_output(llm_output)
```

### 2. Remaining Agents (Days 4-14)
Update in this order:
1. Imaging Agent (3 days)
2. Pathology Agent (3 days)
3. EHR Agent (2 days)
4. Guidelines Agent (2 days)

Each agent update includes:
- Implementing new prompt template
- Updating process method
- Basic testing
- Fixing any issues

## Phase 3: Coordinator Updates (Week 4)

### 1. Update Agent Context
```python
# mdt_agent_system/app/agents/coordinator.py

class AgentContext(BaseModel):
    run_id: str
    patient_case: PatientCase
    status_service: StatusUpdateService
    
    # Updated output fields
    ehr_analysis: Optional[AgentOutput] = None
    imaging_analysis: Optional[AgentOutput] = None
    pathology_analysis: Optional[AgentOutput] = None
    specialist_assessment: Optional[AgentOutput] = None
    guideline_recommendations: Optional[AgentOutput] = None
```

### 2. Update MDT Report Generation
```python
class MDTCoordinator:
    def _generate_mdt_report(self, context: AgentContext) -> MDTReport:
        """Generate final MDT report using markdown content."""
        return MDTReport(
            patient_id=context.patient_case.patient_id,
            summary=context.summary.markdown_content if context.summary else None,
            specialist_assessment=context.specialist_assessment.markdown_content if context.specialist_assessment else None,
            # ... other fields
        )
```

## Phase 4: Testing & Refinement (Week 5)

### 1. Basic Test Cases
```python
def test_specialist_agent_output():
    """Test specialist agent output format."""
    agent = SpecialistAgent(run_id="test", status_service=mock_status_service)
    result = await agent.process(test_patient_case, {})
    
    assert isinstance(result, AgentOutput)
    assert "# Clinical Assessment" in result.markdown_content
    assert "key_findings" in result.metadata
```

### 2. Integration Testing
- Test full MDT workflow
- Verify markdown rendering
- Check metadata consistency
- Validate backward compatibility

## Implementation Schedule

### Week 1: Core Infrastructure
- Day 1-2: Set up new schemas and parsers
- Day 3-4: Update base agent class
- Day 5: Testing and fixes

### Week 2: First Agents
- Day 1-3: Specialist Agent update and testing
- Day 4-5: Imaging Agent update and testing

### Week 3: Remaining Agents
- Day 1-2: Pathology Agent
- Day 3-4: EHR Agent
- Day 5: Guidelines Agent

### Week 4: Coordinator
- Day 1-3: Update coordinator and context handling
- Day 4-5: Update report generation

### Week 5: Testing & Refinement
- Day 1-2: Individual agent testing
- Day 3-4: Integration testing
- Day 5: Final adjustments

## Rollback Plan

### Quick Rollback
If issues occur with an updated agent:
1. Revert agent's prompt to previous version
2. Use legacy output format
3. System continues functioning

### Full Rollback
If major issues occur:
1. Revert to previous agent versions
2. Restore old coordinator
3. Remove new schemas

## Success Metrics

### 1. Output Quality
- Markdown formatting correctness
- Metadata completeness
- Clinical accuracy

### 2. System Performance
- Response times
- Error rates
- Memory usage

### 3. User Experience
- Report readability
- Information accessibility
- Navigation ease

## Post-Implementation

### 1. Monitoring
- Track error rates
- Monitor performance
- Collect user feedback

### 2. Optimization
- Refine prompts based on usage
- Optimize output parsing
- Enhance metadata structure

### 3. Documentation
- Update technical docs
- Create user guides
- Document best practices

## Future Enhancements

### 1. Advanced Features
- Enhanced metadata validation
- Automated quality checks
- Advanced formatting options

### 2. Integration Options
- API improvements
- External system connections
- Reporting enhancements

### 3. User Interface
- Better markdown rendering
- Interactive elements
- Customizable views 