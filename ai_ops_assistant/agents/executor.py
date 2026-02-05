"""
Executor Agent for AI Operations Assistant.

This module provides the ExecutorAgent class that executes structured plans
by calling appropriate tools, handling retries with exponential backoff,
and managing partial failures gracefully.
"""

import logging
import time
from typing import Dict, List, Any, Callable, Optional
from datetime import datetime


logger = logging.getLogger(__name__)


class ExecutorAgent:
    """
    Executes plans step-by-step using registered tools.
    Handles retries, partial failures, and logging.
    
    The executor takes a structured plan from the PlannerAgent and executes
    each step sequentially, calling the appropriate tool with the specified
    parameters. It implements retry logic with exponential backoff for
    transient failures and continues execution even when non-critical steps fail.
    """
    
    def __init__(self, tools: Dict[str, Any]):
        """
        Initialize the Executor Agent with available tools.
        
        Args:
            tools: Dictionary mapping tool names to tool instances.
                  Expected keys: "github", "weather", "wikipedia"
                  Each tool should have methods matching the plan's action requirements.
        
        Raises:
            ValueError: If tools dictionary is empty or None
        """
        if not tools:
            raise ValueError("Tools dictionary cannot be empty")
        
        self.tools = tools
        self.execution_log = []
        
        logger.info(f"Executor Agent initialized with tools: {list(tools.keys())}")
    
    def execute_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a structured plan step-by-step.
        
        Executes each step in the plan sequentially, calling the appropriate
        tool with the specified parameters. Handles errors gracefully and
        continues execution when possible, collecting partial results.
        
        Args:
            plan: Structured plan dictionary from PlannerAgent with format:
                {
                    "task_description": str,
                    "intent": str,
                    "steps": [
                        {
                            "step_number": int,
                            "action": str,
                            "tool": str,
                            "parameters": dict,
                            "expected_output": str
                        }
                    ],
                    "comparison_mode": bool (optional),
                    "entities": list (optional)
                }
        
        Returns:
            Dictionary with execution results:
            {
                "success": bool,
                "steps_completed": int,
                "steps_failed": int,
                "results": [
                    {
                        "step_number": int,
                        "status": "success"|"failed"|"partial",
                        "data": Any,
                        "error": str|None,
                        "execution_time": float
                    }
                ],
                "execution_log": [str]
            }
        
        Raises:
            ValueError: If plan is invalid or missing required fields
        """
        if not plan or not isinstance(plan, dict):
            raise ValueError("Plan must be a non-empty dictionary")
        
        if "steps" not in plan or not plan["steps"]:
            raise ValueError("Plan must contain at least one step")
        
        logger.info(f"Starting plan execution: {plan.get('task_description', 'No description')}")
        logger.info(f"Plan has {len(plan['steps'])} steps")
        
        # Reset execution log for this plan
        self.execution_log = []
        
        # Track execution statistics
        steps_completed = 0
        steps_failed = 0
        results = []
        
        # Execute each step
        for step in plan["steps"]:
            step_number = step.get("step_number", 0)
            
            try:
                logger.info(f"Executing step {step_number}: {step.get('action', 'No action')}")
                
                # Execute the step
                step_result = self._execute_step(step)
                
                # Check if step was successful
                if step_result["status"] == "success":
                    steps_completed += 1
                    self._log_execution(
                        step_number,
                        "success",
                        step_result["data"]
                    )
                else:
                    steps_failed += 1
                    self._log_execution(
                        step_number,
                        "failed",
                        None,
                        step_result.get("error", "Unknown error")
                    )
                
                results.append(step_result)
                
            except Exception as e:
                # Unexpected error during step execution
                logger.error(f"Unexpected error in step {step_number}: {str(e)}")
                steps_failed += 1
                
                error_result = {
                    "step_number": step_number,
                    "status": "failed",
                    "data": None,
                    "error": f"Unexpected error: {str(e)}",
                    "execution_time": 0.0
                }
                results.append(error_result)
                
                self._log_execution(
                    step_number,
                    "failed",
                    None,
                    f"Unexpected error: {str(e)}"
                )
        
        # Determine overall success
        # Success if at least one step completed successfully
        overall_success = steps_completed > 0
        
        execution_result = {
            "success": overall_success,
            "steps_completed": steps_completed,
            "steps_failed": steps_failed,
            "results": results,
            "execution_log": self.execution_log.copy()
        }
        
        logger.info(f"Plan execution complete: {steps_completed} succeeded, {steps_failed} failed")
        
        return execution_result
    
    def _execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single step from the plan.
        
        Calls the appropriate tool with the specified parameters,
        implements retry logic with exponential backoff, and
        handles errors gracefully.
        
        Args:
            step: Step dictionary with fields:
                - step_number: int
                - action: str
                - tool: str (github|weather|wikipedia)
                - parameters: dict
                - expected_output: str
        
        Returns:
            Dictionary with step execution result:
            {
                "step_number": int,
                "status": "success"|"failed",
                "data": Any,
                "error": str|None,
                "execution_time": float
            }
        """
        step_number = step.get("step_number", 0)
        tool_name = step.get("tool", "")
        parameters = step.get("parameters", {})
        
        # Validate tool exists
        if tool_name not in self.tools:
            error_msg = f"Tool '{tool_name}' not found in available tools"
            logger.error(error_msg)
            return {
                "step_number": step_number,
                "status": "failed",
                "data": None,
                "error": error_msg,
                "execution_time": 0.0
            }
        
        tool = self.tools[tool_name]
        
        # Start timing
        start_time = time.time()
        
        try:
            # Determine which tool method to call based on parameters and tool
            result_data = self._retry_with_backoff(
                lambda: self._call_tool_method(tool, tool_name, parameters)
            )
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            logger.info(f"Step {step_number} completed successfully in {execution_time:.2f}s")
            
            return {
                "step_number": step_number,
                "status": "success",
                "data": result_data,
                "error": None,
                "execution_time": execution_time
            }
        
        except Exception as e:
            # Calculate execution time
            execution_time = time.time() - start_time
            
            error_msg = str(e)
            logger.error(f"Step {step_number} failed after {execution_time:.2f}s: {error_msg}")
            
            return {
                "step_number": step_number,
                "status": "failed",
                "data": None,
                "error": error_msg,
                "execution_time": execution_time
            }
    
    def _call_tool_method(self, tool: Any, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """
        Call the appropriate method on a tool based on parameters.
        
        Determines which tool method to call based on the tool type and
        parameters provided. Handles different tool interfaces.
        
        Args:
            tool: Tool instance
            tool_name: Name of the tool (github|weather|wikipedia)
            parameters: Parameters to pass to the tool method
        
        Returns:
            Result from the tool method call
        
        Raises:
            ValueError: If required parameters are missing
            Exception: If tool method call fails
        """
        if tool_name == "github":
            # GitHub tool methods: search_repositories, get_repository_details, compare_repositories
            if "query" in parameters:
                # Search repositories
                query = parameters["query"]
                sort = parameters.get("sort", "stars")
                limit = parameters.get("limit", 5)
                return tool.search_repositories(query=query, sort=sort, limit=limit)
            else:
                raise ValueError("GitHub tool requires 'query' parameter")
        
        elif tool_name == "weather":
            # Weather tool methods: get_current_weather, compare_weather
            if "city" in parameters:
                # Single city weather
                city = parameters["city"]
                units = parameters.get("units", "metric")
                return tool.get_current_weather(city=city, units=units)
            elif "cities" in parameters:
                # Compare multiple cities
                cities = parameters["cities"]
                units = parameters.get("units", "metric")
                return tool.compare_weather(cities=cities, units=units)
            else:
                raise ValueError("Weather tool requires 'city' or 'cities' parameter")
        
        elif tool_name == "wikipedia":
            # Wikipedia tool methods: get_summary, search_articles, compare_topics
            if "topic" in parameters:
                # Get article summary
                topic = parameters["topic"]
                sentences = parameters.get("sentences", 3)
                return tool.get_summary(topic=topic, sentences=sentences)
            elif "query" in parameters:
                # Search articles
                query = parameters["query"]
                limit = parameters.get("limit", 5)
                return tool.search_articles(query=query, limit=limit)
            elif "topics" in parameters:
                # Compare topics
                topics = parameters["topics"]
                return tool.compare_topics(topics=topics)
            else:
                raise ValueError("Wikipedia tool requires 'topic', 'query', or 'topics' parameter")
        
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    def _retry_with_backoff(
        self,
        func: Callable,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0
    ) -> Any:
        """
        Execute a function with retry logic and exponential backoff.
        
        Retries the function on transient failures (network errors, rate limits)
        with exponential backoff between attempts. Gives up after max_retries.
        
        Args:
            func: Function to execute (should take no arguments)
            max_retries: Maximum number of retry attempts (default: 3)
            initial_delay: Initial delay in seconds before first retry (default: 1.0)
            backoff_factor: Multiplier for delay between retries (default: 2.0)
        
        Returns:
            Result from successful function execution
        
        Raises:
            Exception: The last exception if all retries fail
        """
        last_exception = None
        delay = initial_delay
        
        for attempt in range(max_retries + 1):  # +1 for initial attempt
            try:
                # Try to execute the function
                result = func()
                
                # Success!
                if attempt > 0:
                    logger.info(f"Function succeeded on attempt {attempt + 1}")
                
                return result
            
            except Exception as e:
                last_exception = e
                
                # Check if this is a transient error worth retrying
                error_str = str(e).lower()
                is_transient = any(keyword in error_str for keyword in [
                    "timeout",
                    "rate limit",
                    "429",
                    "503",
                    "502",
                    "connection",
                    "network"
                ])
                
                # If not transient or out of retries, raise immediately
                if not is_transient or attempt >= max_retries:
                    if attempt > 0:
                        logger.error(f"Function failed after {attempt + 1} attempts: {str(e)}")
                    raise
                
                # Log retry attempt
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay}s...")
                
                # Wait before retrying
                time.sleep(delay)
                
                # Increase delay for next retry (exponential backoff)
                delay *= backoff_factor
        
        # Should never reach here, but just in case
        if last_exception:
            raise last_exception
        else:
            raise Exception("Function failed with unknown error")
    
    def _log_execution(
        self,
        step_number: int,
        status: str,
        result: Any,
        error: Optional[str] = None
    ) -> None:
        """
        Log execution details for a step.
        
        Adds a formatted log entry to the execution log with timestamp,
        step number, status, and relevant details.
        
        Args:
            step_number: Step number being logged
            status: Status of the step ("success" or "failed")
            result: Result data (for successful steps)
            error: Error message (for failed steps)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if status == "success":
            # Log success with result summary
            result_summary = self._summarize_result(result)
            log_entry = f"[{timestamp}] Step {step_number}: SUCCESS - {result_summary}"
        else:
            # Log failure with error
            log_entry = f"[{timestamp}] Step {step_number}: FAILED - {error}"
        
        self.execution_log.append(log_entry)
        logger.debug(log_entry)
    
    def _summarize_result(self, result: Any) -> str:
        """
        Create a brief summary of a result for logging.
        
        Args:
            result: Result data to summarize
        
        Returns:
            String summary of the result
        """
        if result is None:
            return "No data"
        
        if isinstance(result, list):
            return f"Retrieved {len(result)} items"
        
        if isinstance(result, dict):
            # Check for common result patterns
            if "city" in result:
                return f"Weather data for {result.get('city', 'unknown')}"
            elif "name" in result:
                return f"Data for {result.get('name', 'unknown')}"
            elif "title" in result:
                return f"Article: {result.get('title', 'unknown')}"
            else:
                return f"Dictionary with {len(result)} fields"
        
        return f"Data: {str(result)[:50]}"
