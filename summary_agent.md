# Summary Agent & Drill-Down UI Implementation Plan

## Overview
This plan outlines the implementation of a Summary Agent and complementary UI enhancements without disrupting the existing MDT system architecture. The goal is to improve report readability by providing a concise markdown summary at the top with collapsible detailed sections.

## 1. Create SummaryAgent Class

### File: `mdt_agent_system/app/agents/summary_agent.py`
```python
import json
from typing import Dict, Any

from mdt_agent_system.app.core.schemas import PatientCase
from mdt_agent_system.app.core.status import StatusUpdateService
from mdt_agent_system.app.core.logging import get_logger
from mdt_agent_system.app.agents.base_agent import BaseSpecializedAgent

class SummaryAgent(BaseSpecializedAgent):
    """Summary Agent responsible for creating concise, markdown-formatted overview of MDT findings.
    
    This agent focuses on:
    1. Extracting key information from all previous agent outputs
    2. Creating a concise summary in markdown format
    3. Highlighting critical findings and recommendations
    4. Providing an executive summary for quick clinical decision-making
    """
    
    def __init__(self, run_id: str, status_service: StatusUpdateService, callbacks=None):
        super().__init__(
            agent_id="SummaryAgent",
            run_id=run_id,
            status_service=status_service,
            callbacks=callbacks
        )
    
    def _get_agent_type(self) -> str:
        """Return the agent type for prompt template selection."""
        return "summary"
        
    def _prepare_input(self, patient_case: PatientCase, context: Dict[str, Any]) -> Dict[str, Any]:
        """Convert complete MDT report data to LLM-friendly input for summarization"""
        # Implementation details here
        
    def _structure_output(self, llm_output: str) -> Dict[str, Any]:
        """Preserve markdown formatting from LLM output"""
        # Implementation details here
```

## 2. Create System Prompt Template for Summary Agent

### File: `mdt_agent_system/app/core/prompts/summary_template.txt`
```
You are a medical summarization specialist. Your task is to create a concise, clear summary of a multidisciplinary team (MDT) report in Markdown format.

Extract only the most critical information that a clinician needs to know at a glance:

# MDT Summary: [PATIENT_ID]

## Diagnosis & Staging
- **Confirmed Diagnosis**: [DIAGNOSIS]
- **Stage**: [STAGE]
- **Key Molecular Findings**: [MOLECULAR DATA]
- **Performance Status**: [KPS/ECOG]

## Key Recommendations
1. [PRIMARY TREATMENT RECOMMENDATION]
2. [SECONDARY RECOMMENDATION]
3. [TERTIARY RECOMMENDATION]

## Critical Next Steps
- [ ] [NEXT STEP 1]
- [ ] [NEXT STEP 2]
- [ ] [NEXT STEP 3]

Focus only on the most important information that would inform immediate clinical decision-making. Use bullet points and formatting to enhance readability. Do not include detailed analyses - those are available in the sections below.
```

## 3. Update Coordinator to Include SummaryAgent

### File: `mdt_agent_system/app/agents/coordinator.py`
```python
# Import the new SummaryAgent
from mdt_agent_system.app.agents.summary_agent import SummaryAgent

# Add summary agent step function
async def _run_summary_step(context: AgentContext) -> AgentContext:
    agent_id = "SummaryAgent"
    # Implementation details similar to other agent step functions
    
# Add to workflow pipeline
mdt_workflow: Runnable[AgentContext, AgentContext] = (
    RunnableLambda(emit_and_run_ehr)
    | RunnableLambda(emit_and_run_imaging)
    | RunnableLambda(emit_and_run_pathology)
    | RunnableLambda(emit_and_run_guideline)
    | RunnableLambda(emit_and_run_specialist)
    | RunnableLambda(emit_and_run_evaluation)
    | RunnableLambda(emit_and_run_summary)  # Add summary as final step
)

# Update MDTReport creation to include summary
final_report = MDTReport(
    # Existing fields...
    summary_markdown=final_context.summary.get("markdown_summary") if final_context.summary else None,
    # Other fields...
)
```

## 4. Update MDTReport Schema

### File: `mdt_agent_system/app/core/schemas/report.py`
```python
class MDTReport(BaseModel):
    """Schema for MDT meeting report."""
    # Existing fields...
    summary_markdown: Optional[str] = Field(None, description="Markdown-formatted executive summary of the MDT report")
    # Other fields...
```

## 5. Update Frontend UI for Collapsible Sections

### File: `mdt_agent_system/app/static/app.js`
```javascript
// Add summary section rendering at the top
function renderSummary(data) {
    if (data.summary_markdown) {
        const summaryElement = document.getElementById('mdt-summary');
        summaryElement.innerHTML = marked.parse(data.summary_markdown);
        summaryElement.classList.remove('hidden');
    }
}

// Convert existing sections to collapsible elements
function createCollapsibleSection(title, content, expanded = false) {
    const details = document.createElement('details');
    details.className = 'agent-details';
    if (expanded) details.setAttribute('open', '');
    
    const summary = document.createElement('summary');
    summary.textContent = title;
    details.appendChild(summary);
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'agent-content';
    contentDiv.innerHTML = content;
    details.appendChild(contentDiv);
    
    return details;
}

// Update the existing render functions to use collapsible sections
```

### File: `mdt_agent_system/app/static/styles.css`
```css
/* Add styles for collapsible sections */
.mdt-summary {
    background-color: #f8f9fa;
    border-left: 4px solid #007bff;
    padding: 1rem;
    margin-bottom: 2rem;
}

details.agent-details {
    border: 1px solid #dee2e6;
    border-radius: 0.25rem;
    margin-bottom: 1rem;
}

details.agent-details summary {
    padding: 0.75rem;
    cursor: pointer;
    background-color: #f8f9fa;
    font-weight: 500;
}

details.agent-details .agent-content {
    padding: 1rem;
}
```

### File: `mdt_agent_system/app/templates/report.html`
```html
<!-- Add summary section at the top -->
<div id="mdt-summary" class="mdt-summary hidden"></div>

<!-- The rest of the sections will be rendered as collapsible elements -->
<div id="mdt-content"></div>
```

## 6. Potential Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| LLM summary quality issues | Provide clear instructions and examples in the prompt |
| Performance impact from additional agent | Profile and optimize if needed |
| Markdown rendering issues | Use marked.js, a well-tested and versatile markdown parser library that's lightweight and widely adopted |
| UI/UX complexity | Keep design simple and follow web standards |

This implementation plan prioritizes complementing the existing solution without revamping the core architecture, focusing on adding value through better information organization and presentation. 