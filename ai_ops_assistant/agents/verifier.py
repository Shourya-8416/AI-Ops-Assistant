"""
Verifier Agent for AI Operations Assistant.

This module provides the VerifierAgent class that validates execution results
for completeness and correctness, uses LLM to assess quality, and improves
output formatting for better readability.
"""

import logging
from typing import Dict, List, Any, Optional


logger = logging.getLogger(__name__)


class VerifierAgent:
    """
    Verifies execution results for completeness and correctness.
    Uses LLM to assess quality and improve formatting.
    
    The verifier takes execution results from the ExecutorAgent and validates
    that all expected outputs are present, checks for data consistency and
    anomalies, and formats the output for better readability.
    """
    
    def __init__(self, llm_client):
        """
        Initialize the Verifier Agent with an LLM client.
        
        Args:
            llm_client: LLMClient instance for quality assessment
        
        Raises:
            ValueError: If llm_client is None
        """
        if not llm_client:
            raise ValueError("LLM client is required")
        
        self.llm_client = llm_client
        
        logger.info("Verifier Agent initialized")
    
    def verify_results(self, plan: Dict[str, Any], execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify execution results for completeness and correctness.
        
        Checks that all expected outputs from the plan are present in the
        execution results, validates data consistency, flags anomalies,
        and improves output formatting using LLM.
        
        Args:
            plan: Original plan dictionary from PlannerAgent
            execution_result: Execution result dictionary from ExecutorAgent
        
        Returns:
            Dictionary with verification results:
            {
                "is_complete": bool,
                "is_correct": bool,
                "confidence_score": float,
                "issues": [str],
                "formatted_output": str,
                "summary": str,
                "recommendations": [str]
            }
        
        Raises:
            ValueError: If plan or execution_result is invalid
        """
        if not plan or not isinstance(plan, dict):
            raise ValueError("Plan must be a non-empty dictionary")
        
        if not execution_result or not isinstance(execution_result, dict):
            raise ValueError("Execution result must be a non-empty dictionary")
        
        logger.info("Starting result verification")
        
        # Check completeness
        is_complete = self._check_completeness(plan, execution_result)
        
        # Collect issues
        issues = []
        
        # Check if all steps succeeded
        if execution_result.get("steps_failed", 0) > 0:
            issues.append(f"{execution_result['steps_failed']} step(s) failed during execution")
        
        # Check for missing data
        if not is_complete:
            expected_steps = len(plan.get("steps", []))
            completed_steps = execution_result.get("steps_completed", 0)
            issues.append(f"Only {completed_steps} of {expected_steps} steps completed successfully")
        
        # Check for anomalies in results
        anomalies = self._check_for_anomalies(execution_result)
        issues.extend(anomalies)
        
        # Use LLM to assess quality and format output
        try:
            llm_verification = self._verify_with_llm(plan, execution_result)
            formatted_output = llm_verification.get("formatted_output", "")
            summary = llm_verification.get("summary", "")
            recommendations = llm_verification.get("recommendations", [])
            confidence_score = llm_verification.get("confidence_score", 0.5)
            
            # Add any additional issues found by LLM
            llm_issues = llm_verification.get("issues", [])
            issues.extend(llm_issues)
        
        except Exception as e:
            logger.warning(f"LLM verification failed: {str(e)}. Using fallback formatting.")
            formatted_output = self._format_for_display(execution_result)
            summary = "Verification completed with basic formatting (LLM unavailable)"
            recommendations = []
            confidence_score = 0.5
        
        # Determine correctness based on issues
        is_correct = len(issues) == 0 and execution_result.get("success", False)
        
        verification_result = {
            "is_complete": is_complete,
            "is_correct": is_correct,
            "confidence_score": confidence_score,
            "issues": issues,
            "formatted_output": formatted_output,
            "summary": summary,
            "recommendations": recommendations
        }
        
        logger.info(f"Verification complete: complete={is_complete}, correct={is_correct}, issues={len(issues)}")
        
        return verification_result
    
    def _check_completeness(self, plan: Dict[str, Any], execution_result: Dict[str, Any]) -> bool:
        """
        Check if all expected outputs from the plan are present.
        
        Args:
            plan: Original plan dictionary
            execution_result: Execution result dictionary
        
        Returns:
            bool: True if all expected outputs are present, False otherwise
        """
        expected_steps = len(plan.get("steps", []))
        completed_steps = execution_result.get("steps_completed", 0)
        
        # Complete if all steps succeeded
        is_complete = completed_steps == expected_steps
        
        logger.debug(f"Completeness check: {completed_steps}/{expected_steps} steps completed")
        
        return is_complete
    
    def _check_for_anomalies(self, execution_result: Dict[str, Any]) -> List[str]:
        """
        Check execution results for anomalies or suspicious data.
        
        Args:
            execution_result: Execution result dictionary
        
        Returns:
            List of anomaly descriptions
        """
        anomalies = []
        
        # Check each result for anomalies
        for result in execution_result.get("results", []):
            if result.get("status") != "success":
                continue
            
            data = result.get("data")
            if not data:
                continue
            
            # Check for weather anomalies
            if isinstance(data, dict) and "temperature" in data:
                temp = data.get("temperature")
                if temp is not None:
                    if temp < -100 or temp > 60:
                        anomalies.append(f"Unusual temperature value: {temp}°C")
            
            # Check for empty lists when data is expected
            if isinstance(data, list) and len(data) == 0:
                anomalies.append("Empty result set returned")
        
        return anomalies
    
    def _verify_with_llm(self, plan: Dict[str, Any], execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use LLM to verify results and improve formatting.
        
        Args:
            plan: Original plan dictionary
            execution_result: Execution result dictionary
        
        Returns:
            Dictionary with LLM verification results
        """
        # Build verification prompt
        messages = self._build_verification_prompt(plan, execution_result)
        
        # Get LLM response
        response = self.llm_client.generate_json_completion(messages, max_tokens=1500)
        
        return response
    
    def _build_verification_prompt(self, plan: Dict[str, Any], execution_result: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Build the verification prompt for the LLM.
        
        Args:
            plan: Original plan dictionary
            execution_result: Execution result dictionary
        
        Returns:
            List of message dictionaries for LLM
        """
        system_message = """You are a verification assistant that validates execution results.

Your tasks:
1. Check if all expected outputs from the plan are present in the results
2. Validate data consistency and flag any anomalies
3. Format the results in a clear, readable way
4. Provide a summary of what was accomplished
5. Suggest follow-up actions or improvements

Respond in JSON format with these fields:
{
    "formatted_output": "Clear, readable presentation of the results",
    "summary": "Brief summary of what was accomplished",
    "issues": ["List of any issues or anomalies found"],
    "recommendations": ["List of suggested follow-up actions"],
    "confidence_score": 0.95
}"""
        
        # Format plan and results for the prompt
        plan_summary = {
            "task": plan.get("task_description", "No description"),
            "steps": len(plan.get("steps", [])),
            "comparison_mode": plan.get("comparison_mode", False)
        }
        
        result_summary = {
            "success": execution_result.get("success", False),
            "steps_completed": execution_result.get("steps_completed", 0),
            "steps_failed": execution_result.get("steps_failed", 0),
            "results": execution_result.get("results", [])
        }
        
        user_message = f"""Please verify these execution results:

PLAN:
{plan_summary}

EXECUTION RESULTS:
{result_summary}

Provide your verification in JSON format."""
        
        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
    
    def _format_for_display(self, execution_result: Dict[str, Any]) -> str:
        """
        Format execution results for readable display (fallback method).
        
        Args:
            execution_result: Execution result dictionary
        
        Returns:
            Formatted string for display
        """
        lines = []
        lines.append("=" * 60)
        lines.append("EXECUTION RESULTS")
        lines.append("=" * 60)
        
        # Overall status
        if execution_result.get("success"):
            lines.append("✓ Overall Status: SUCCESS")
        else:
            lines.append("✗ Overall Status: FAILED")
        
        lines.append(f"Steps Completed: {execution_result.get('steps_completed', 0)}")
        lines.append(f"Steps Failed: {execution_result.get('steps_failed', 0)}")
        lines.append("")
        
        # Individual results
        for result in execution_result.get("results", []):
            step_num = result.get("step_number", 0)
            status = result.get("status", "unknown")
            
            lines.append(f"Step {step_num}: {status.upper()}")
            
            if status == "success":
                data = result.get("data")
                if data:
                    lines.append(f"  Data: {self._format_data(data)}")
            else:
                error = result.get("error", "Unknown error")
                lines.append(f"  Error: {error}")
            
            lines.append("")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def _format_data(self, data: Any) -> str:
        """
        Format data for display.
        
        Args:
            data: Data to format
        
        Returns:
            Formatted string
        """
        if isinstance(data, list):
            if len(data) == 0:
                return "Empty list"
            elif len(data) <= 3:
                return f"{len(data)} items: {[self._format_item(item) for item in data]}"
            else:
                return f"{len(data)} items (showing first 3): {[self._format_item(item) for item in data[:3]]}"
        
        elif isinstance(data, dict):
            return self._format_item(data)
        
        else:
            return str(data)
    
    def _format_item(self, item: Any) -> str:
        """
        Format a single item for display.
        
        Args:
            item: Item to format
        
        Returns:
            Formatted string
        """
        if isinstance(item, dict):
            # Try to find a good identifier
            if "name" in item:
                return item["name"]
            elif "title" in item:
                return item["title"]
            elif "city" in item:
                return f"{item['city']} ({item.get('temperature', 'N/A')}°C)"
            else:
                return f"Dict with {len(item)} fields"
        
        return str(item)
