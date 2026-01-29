"""Planner v5 integration adapter for RFSN Controller.

Provides a simple adapter to integrate Planner v5 with the existing
controller loop. This adapter translates between the controller's
expectations and Planner v5's proposal-based interface.

Usage:
    from rfsn_controller.planner_v5_adapter import PlannerV5Adapter
    
    adapter = PlannerV5Adapter()
    proposal = adapter.get_next_action(controller_feedback)
    
    # Execute proposal through controller
    result = controller.execute_proposal(proposal)
    
    # Feed result back to planner
    adapter.process_result(result)
"""

from __future__ import annotations

from typing import Any, Optional
from dataclasses import dataclass

try:
    from .planner_v5 import MetaPlanner, StateTracker, Proposal
    HAS_PLANNER_V5 = True
except ImportError:
    HAS_PLANNER_V5 = False
    MetaPlanner = None  # type: ignore
    StateTracker = None  # type: ignore
    Proposal = None  # type: ignore


@dataclass
class ControllerAction:
    """Action translated from Planner v5 proposal for controller."""
    
    action_type: str  # "edit_file", "run_tests", "read_file", etc.
    target_path: Optional[str] = None
    content: Optional[str] = None
    test_path: Optional[str] = None
    command: Optional[str] = None
    metadata: dict[str, Any] | None = None


class PlannerV5Adapter:
    """Adapter to integrate Planner v5 with RFSN Controller.
    
    This adapter provides a bridge between the controller's action-based
    interface and Planner v5's proposal-based interface.
    
    Attributes:
        meta_planner: Planner v5 MetaPlanner instance
        state_tracker: StateTracker for maintaining state
        enabled: Whether Planner v5 is available and enabled
    
    Example:
        >>> adapter = PlannerV5Adapter()
        >>> if adapter.enabled:
        ...     action = adapter.get_next_action(feedback)
        ...     result = controller.execute(action)
        ...     adapter.process_result(result)
    """
    
    def __init__(self, enabled: bool = True):
        """Initialize Planner v5 adapter.
        
        Args:
            enabled: Whether to enable Planner v5 (default: True)
        """
        self.enabled = enabled and HAS_PLANNER_V5
        
        if self.enabled:
            self.state_tracker = StateTracker()
            self.meta_planner = MetaPlanner(state_tracker=self.state_tracker)
        else:
            self.state_tracker = None
            self.meta_planner = None
        
        self.last_proposal: Optional[Proposal] = None
    
    def get_next_action(
        self,
        controller_feedback: Optional[dict] = None,
        gate_rejection: Optional[tuple[str, str]] = None
    ) -> Optional[ControllerAction]:
        """Get next action from Planner v5.
        
        Args:
            controller_feedback: Feedback from controller execution
            gate_rejection: Gate rejection info (type, reason)
            
        Returns:
            ControllerAction to execute, or None if planner not enabled
            
        Example:
            >>> action = adapter.get_next_action({"tests_failed": 2})
            >>> print(action.action_type)
            'edit_file'
        """
        if not self.enabled or not self.meta_planner:
            return None
        
        # Get proposal from Planner v5
        proposal = self.meta_planner.next_proposal(
            controller_feedback=controller_feedback,
            gate_rejection=gate_rejection
        )
        
        self.last_proposal = proposal
        
        # Translate proposal to controller action
        return self._translate_proposal(proposal)
    
    def _translate_proposal(self, proposal: Proposal) -> ControllerAction:
        """Translate Planner v5 proposal to controller action.
        
        Args:
            proposal: Planner v5 proposal
            
        Returns:
            ControllerAction for controller execution
        """
        # Extract action info from proposal
        action_type = proposal.action_type
        target_path = proposal.target.get("path") if proposal.target else None
        
        # Build metadata
        metadata = {
            "proposal_id": proposal.proposal_id,
            "intent": proposal.intent,
            "hypothesis": proposal.hypothesis,
            "risk_level": proposal.risk_level,
        }
        
        # Translate to controller action
        if action_type == "edit_file":
            return ControllerAction(
                action_type="edit_file",
                target_path=target_path,
                content=proposal.change_summary,  # Simplified
                metadata=metadata
            )
        
        elif action_type == "run_tests":
            return ControllerAction(
                action_type="run_tests",
                test_path=target_path,
                metadata=metadata
            )
        
        elif action_type == "read_file":
            return ControllerAction(
                action_type="read_file",
                target_path=target_path,
                metadata=metadata
            )
        
        elif action_type == "run_command":
            return ControllerAction(
                action_type="run_command",
                command=proposal.change_summary,  # Command stored here
                metadata=metadata
            )
        
        else:
            # Generic action
            return ControllerAction(
                action_type=action_type,
                target_path=target_path,
                metadata=metadata
            )
    
    def process_result(self, result: dict) -> None:
        """Process execution result and update planner state.
        
        Args:
            result: Result dictionary from controller execution
            
        Example:
            >>> result = {"success": True, "tests_passed": 5}
            >>> adapter.process_result(result)
        """
        if not self.enabled or not self.meta_planner:
            return
        
        # Extract feedback for planner
        feedback = {
            "output": result.get("output", ""),
            "tests_failed": result.get("tests_failed", 0),
            "tests_passed": result.get("tests_passed", 0),
            "traceback": result.get("traceback"),
            "duration": result.get("duration", 0),
        }
        
        # Store for next iteration
        # (The next call to get_next_action will use this feedback)
        self._last_feedback = feedback
    
    def is_enabled(self) -> bool:
        """Check if Planner v5 is enabled.
        
        Returns:
            True if Planner v5 is available and enabled
        """
        return self.enabled
    
    def get_state_summary(self) -> dict:
        """Get summary of planner state.
        
        Returns:
            Dictionary with state summary
        """
        if not self.enabled or not self.state_tracker:
            return {"enabled": False}
        
        return {
            "enabled": True,
            "failing_tests": len(self.state_tracker.failing_tests),
            "suspect_files": len(self.state_tracker.suspect_files),
            "iterations": self.state_tracker.iteration,
            "risk_used": self.state_tracker.risk_used,
        }


def create_planner_adapter(use_v5: bool = True) -> PlannerV5Adapter:
    """Factory function to create planner adapter.
    
    Args:
        use_v5: Whether to use Planner v5 (default: True)
        
    Returns:
        Configured PlannerV5Adapter instance
        
    Example:
        >>> adapter = create_planner_adapter(use_v5=True)
        >>> if adapter.is_enabled():
        ...     print("Planner v5 ready")
    """
    return PlannerV5Adapter(enabled=use_v5)
