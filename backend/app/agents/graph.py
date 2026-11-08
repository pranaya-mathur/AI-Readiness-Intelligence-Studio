import logging
from typing import Any, Dict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.agents.nodes.agent_nodes import (
    ai_use_case_node,
    business_context_node,
    document_understanding_node,
    process_bottleneck_node,
    proposal_writing_node,
    readiness_scoring_node,
    report_generation_node,
    risk_governance_node,
    roadmap_planning_node,
)
from app.agents.state import AssessmentState
from app.services.llm_router import LLMRouter

logger = logging.getLogger("AssessmentOrchestrator")


class AssessmentOrchestrator:
    def __init__(self):
        # 1. Initialize Graph with state model
        workflow = StateGraph(AssessmentState)

        # 2. Add nodes
        workflow.add_node("document_understanding", document_understanding_node)
        workflow.add_node("business_context", business_context_node)
        workflow.add_node("process_bottleneck", process_bottleneck_node)
        workflow.add_node("ai_use_case", ai_use_case_node)
        workflow.add_node("readiness_scoring", readiness_scoring_node)
        workflow.add_node("risk_governance", risk_governance_node)
        workflow.add_node("roadmap_planning", roadmap_planning_node)
        workflow.add_node("proposal_writing", proposal_writing_node)
        workflow.add_node("report_generation", report_generation_node)

        # 3. Add sequential transitions
        workflow.set_entry_point("document_understanding")
        workflow.add_edge("document_understanding", "business_context")
        workflow.add_edge("business_context", "process_bottleneck")
        workflow.add_edge("process_bottleneck", "ai_use_case")
        workflow.add_edge("ai_use_case", "readiness_scoring")
        workflow.add_edge("readiness_scoring", "risk_governance")
        workflow.add_edge("risk_governance", "roadmap_planning")
        workflow.add_edge("roadmap_planning", "proposal_writing")
        workflow.add_edge("proposal_writing", "report_generation")
        workflow.add_edge("report_generation", END)

        # 4. Set Memory Checkpointer to enable pause/resume
        self.checkpointer = MemorySaver()
        self.app = workflow.compile(checkpointer=self.checkpointer)
        logger.info("LangGraph Assessment Orchestrator compiled successfully.")

    def run_assessment(
        self, initial_state: Dict[str, Any], thread_id: str = "default_thread"
    ) -> Dict[str, Any]:
        """
        Executes the LangGraph analysis pipeline on the given initial state under a thread.
        """
        logger.info(
            f"Triggering LangGraph run on thread {thread_id} for assessment {initial_state.get('assessment_id')}..."
        )
        LLMRouter.reset_session()
        config = {"configurable": {"thread_id": thread_id}}

        # Compile input structure
        inputs = AssessmentState(**initial_state)

        # Run graph
        final_state = self.app.invoke(inputs, config=config)
        if isinstance(final_state, dict) and final_state.get("analysis_incomplete"):
            logger.warning(
                "LangGraph run finished incomplete: %s",
                final_state.get("incomplete_reason"),
            )
        else:
            logger.info("LangGraph run completed successfully.")
        return final_state
