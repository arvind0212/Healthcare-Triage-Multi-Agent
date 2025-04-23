#!/usr/bin/env python
"""
Script to test individual agents with a sample patient case.

Usage:
    python test_agent.py agent_type

Where agent_type is one of:
    ehr, imaging, pathology, guideline, specialist, evaluation

Example:
    python test_agent.py ehr
"""

import asyncio
import json
import sys
import uuid
import os
from typing import Dict, Any, List, Optional

from mdt_agent_system.app.core.schemas import PatientCase
from mdt_agent_system.app.core.status import StatusUpdateService
from mdt_agent_system.app.core.status.service import get_status_service
from mdt_agent_system.app.core.logging.logger import get_logger

# Import agents
from mdt_agent_system.app.agents.ehr_agent import EHRAgent
from mdt_agent_system.app.agents.imaging_agent import ImagingAgent
from mdt_agent_system.app.agents.pathology_agent import PathologyAgent
from mdt_agent_system.app.agents.guideline_agent import GuidelineAgent
from mdt_agent_system.app.agents.specialist_agent import SpecialistAgent
from mdt_agent_system.app.agents.evaluation_agent import EvaluationAgent

# Set up logging
logger = get_logger(__name__)

# Sample patient case path
SAMPLE_PATIENT_CASE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 
    "core", "samples", "patient_case.json"
)

class AgentTester:
    """Test harness for individual agents."""
    
    def __init__(self):
        """Initialize the tester with sample data and services."""
        # Create run_id for this test
        self.run_id = str(uuid.uuid4())
        
        # Initialize status service (use the one from the application)
        self.status_service = get_status_service()
        
        # Subscribe to status updates
        self.status_subscription = None
        
        # Load sample patient case
        with open(SAMPLE_PATIENT_CASE_PATH, "r") as f:
            self.patient_case = PatientCase(**json.load(f))
        
        # Sample outputs from other agents for context
        self.ehr_output = {
            "summary": "62-year-old female with history of smoking",
            "key_history_points": ["Former smoker", "Type 2 Diabetes"],
            "current_presentation": {
                "main_symptoms": ["Persistent cough", "Weight loss"]
            }
        }
        
        self.imaging_output = {
            "summary": "Stage IIIA lung adenocarcinoma",
            "disease_extent": {
                "primary_tumor": "3.8 cm RUL mass",
                "nodal_status": "Multiple hilar and mediastinal nodes"
            },
            "staging": {
                "clinical_stage": "cT2aN2M0, Stage IIIA" 
            }
        }
        
        self.pathology_output = {
            "summary": "Adenocarcinoma with KRAS G12C mutation",
            "histology": "Adenocarcinoma",
            "molecular_profile": {
                "key_mutations": "KRAS G12C mutation",
                "immunotherapy_markers": "PD-L1 80%"
            }
        }
        
        self.guideline_recommendations = [
            {
                "guideline": "NCCN Non-Small Cell Lung Cancer",
                "recommendation": "Consider concurrent chemoradiation followed by immunotherapy"
            }
        ]
        
        self.specialist_output = {
            "summary": "Potentially curable stage IIIA NSCLC",
            "overall_assessment": "Potentially curable stage IIIA NSCLC with favorable molecular profile",
            "treatment_considerations": [
                "High PD-L1 expression favors immunotherapy inclusion",
                "KRAS G12C mutation offers additional targeted therapy options"
            ]
        }
        
        # Ensure memory_data directory exists for agent memory persistence
        os.makedirs("memory_data", exist_ok=True)
        
        logger.info(f"AgentTester initialized with run_id: {self.run_id}")
        
    async def subscribe_to_status_updates(self):
        """Subscribe to status updates and print them."""
        # Don't await the generator, store it directly
        self.status_subscription = self.status_service.subscribe(self.run_id)
        
        # Process status updates in background
        asyncio.create_task(self._process_status_updates())
        
    async def _process_status_updates(self):
        """Process and print status updates."""
        if not self.status_subscription:
            return
            
        async for update in self.status_subscription:
            print(f"STATUS: [{update.agent_id}] [{update.status}] {update.message}")
    
    def get_agent_context(self, agent_type: str) -> Dict[str, Any]:
        """Get appropriate context for the specified agent type."""
        context = {}
        
        # Add context based on agent type and dependencies
        if agent_type in ["imaging", "pathology", "guideline", "specialist", "evaluation"]:
            context["ehr_analysis"] = self.ehr_output
            
        if agent_type in ["pathology", "guideline", "specialist", "evaluation"]:
            context["imaging_analysis"] = self.imaging_output
            
        if agent_type in ["guideline", "specialist", "evaluation"]:
            context["pathology_analysis"] = self.pathology_output
            
        if agent_type in ["specialist", "evaluation"]:
            context["guideline_recommendations"] = self.guideline_recommendations
            
        if agent_type in ["evaluation"]:
            context["specialist_assessment"] = self.specialist_output
            
        return context
    
    def create_agent(self, agent_type: str):
        """Create an agent instance based on the specified type."""
        if agent_type == "ehr":
            return EHRAgent(run_id=self.run_id, status_service=self.status_service)
        elif agent_type == "imaging":
            return ImagingAgent(run_id=self.run_id, status_service=self.status_service)
        elif agent_type == "pathology":
            return PathologyAgent(run_id=self.run_id, status_service=self.status_service)
        elif agent_type == "guideline":
            return GuidelineAgent(run_id=self.run_id, status_service=self.status_service)
        elif agent_type == "specialist":
            return SpecialistAgent(run_id=self.run_id, status_service=self.status_service)
        elif agent_type == "evaluation":
            return EvaluationAgent(run_id=self.run_id, status_service=self.status_service)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
    
    async def test_agent(self, agent_type: str):
        """Test a specific agent type with sample data."""
        print(f"\n{'='*50}")
        print(f"Testing {agent_type.upper()} Agent")
        print(f"{'='*50}\n")
        
        # Subscribe to status updates
        await self.subscribe_to_status_updates()
        
        try:
            # Create the agent instance
            agent = self.create_agent(agent_type)
            
            # Get appropriate context
            context = self.get_agent_context(agent_type)
            
            print(f"Processing with {agent_type.upper()} Agent... (this may take a moment)")
            
            # Run the agent
            result = await agent.process(self.patient_case, context)
            
            print("\nRESULT:")
            print(json.dumps(result, indent=2))
            
            return result
            
        except Exception as e:
            print(f"ERROR: {str(e)}")
            logger.exception(f"Error testing {agent_type} agent: {str(e)}")
            raise
        finally:
            # Allow time for final status updates
            await asyncio.sleep(1)
            # Clean up by removing run data
            self.status_service.clear_run_data(self.run_id)

async def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    
    agent_type = sys.argv[1].lower()
    valid_types = ["ehr", "imaging", "pathology", "guideline", "specialist", "evaluation"]
    
    if agent_type not in valid_types:
        print(f"Error: {agent_type} is not a valid agent type.")
        print(f"Valid types: {', '.join(valid_types)}")
        sys.exit(1)
    
    logger.info(f"Starting agent test for {agent_type}")
    tester = AgentTester()
    await tester.test_agent(agent_type)
    logger.info(f"Completed agent test for {agent_type}")

if __name__ == "__main__":
    asyncio.run(main()) 