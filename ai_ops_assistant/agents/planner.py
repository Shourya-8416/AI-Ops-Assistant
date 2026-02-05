"""
Planner Agent for AI Operations Assistant.

This module provides the PlannerAgent class that converts natural language
queries into structured execution plans using an LLM. The planner analyzes
user intent, detects comparison requests, and generates step-by-step plans
with appropriate tool selections and parameters.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from ai_ops_assistant.llm.llm_client import LLMClient


logger = logging.getLogger(__name__)


class PlannerAgent:
    """
    Plans task execution by analyzing user queries and generating
    structured JSON plans with sequential steps.
    
    The planner uses an LLM to understand user intent, detect comparison
    requests, select appropriate tools, and generate detailed execution
    plans with parameters for each step.
    """
    
    # Plan JSON schema for validation
    PLAN_SCHEMA = {
        "required_fields": ["task_description", "intent", "steps"],
        "optional_fields": ["comparison_mode", "entities"],
        "step_required_fields": ["step_number", "action", "tool", "parameters", "expected_output"],
        "valid_intents": ["search", "compare", "summarize", "mixed"],
        "valid_tools": ["github", "weather", "wikipedia"]
    }
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize the Planner Agent.
        
        Args:
            llm_client: LLMClient instance for generating plans
        """
        self.llm_client = llm_client
        logger.info("Planner Agent initialized")
    
    def create_plan(self, user_query: str) -> Dict[str, Any]:
        """
        Create a structured execution plan from a user query.
        
        Analyzes the user query using an LLM to understand intent,
        detect comparison requests, and generate a detailed plan with
        sequential steps, tool selections, and parameters.
        
        Args:
            user_query: Natural language query from the user
        
        Returns:
            Dictionary containing the execution plan with structure:
            {
                "task_description": str,
                "intent": str (search|compare|summarize|mixed),
                "steps": [
                    {
                        "step_number": int,
                        "action": str,
                        "tool": str (github|weather|wikipedia),
                        "parameters": dict,
                        "expected_output": str
                    }
                ],
                "comparison_mode": bool (optional),
                "entities": list (optional)
            }
        
        Raises:
            ValueError: If user_query is empty or plan validation fails
            Exception: If LLM fails to generate a valid plan
        """
        if not user_query or not user_query.strip():
            raise ValueError("User query cannot be empty")
        
        user_query = user_query.strip()
        logger.info(f"Creating plan for query: '{user_query}'")
        
        # Detect if this is a comparison query
        is_comparison = self._detect_comparison_intent(user_query)
        logger.debug(f"Comparison intent detected: {is_comparison}")
        
        # Build the planning prompt
        messages = self._build_planning_prompt(user_query)
        
        try:
            # Generate plan using LLM with JSON mode
            plan = self.llm_client.generate_json_completion(
                messages=messages,
                max_tokens=2000
            )
            
            # Validate the plan structure
            if not self._validate_plan(plan):
                raise ValueError("Generated plan failed validation")
            
            logger.info(f"Successfully created plan with {len(plan.get('steps', []))} steps")
            logger.debug(f"Plan: {json.dumps(plan, indent=2)}")
            
            return plan
        
        except Exception as e:
            logger.error(f"Failed to create plan: {str(e)}")
            raise
    
    def _build_planning_prompt(self, user_query: str) -> List[Dict[str, str]]:
        """
        Build the prompt messages for the LLM to generate a plan.
        
        Creates a system message defining the planner's role and capabilities,
        includes tool descriptions and parameters, provides examples, and
        adds the user query.
        
        Args:
            user_query: The user's natural language query
        
        Returns:
            List of message dictionaries for the LLM
        """
        system_message = """You are an intelligent task planner for an AI Operations Assistant. Your role is to analyze user queries and create structured execution plans.

Available Tools:

1. **GitHub Tool** (tool: "github")
   - Purpose: Search and retrieve GitHub repository information
   - Capabilities:
     * Search repositories by query with sorting options
     * Get detailed repository information
     * Compare multiple repositories
   - Parameters:
     * query (required): Search query string (e.g., "machine learning", "language:python stars:>1000")
     * sort (optional): Sort by "stars", "forks", or "updated" (default: "stars")
     * limit (optional): Number of results (default: 5)
   - Example: {"query": "rust web frameworks", "sort": "stars", "limit": 5}

2. **Weather Tool** (tool: "weather")
   - Purpose: Fetch current weather data for cities
   - Capabilities:
     * Get current weather for a city
     * Compare weather across multiple cities
   - Parameters:
     * city (required): City name (e.g., "London", "New York", "Tokyo")
     * units (optional): "metric" (Celsius), "imperial" (Fahrenheit), or "standard" (Kelvin) (default: "metric")
   - Example: {"city": "London", "units": "metric"}

3. **Wikipedia Tool** (tool: "wikipedia")
   - Purpose: Fetch article summaries and factual information
   - Capabilities:
     * Get article summaries
     * Search for articles
     * Compare multiple topics
   - Parameters:
     * topic (required): Article topic/title (e.g., "Python (programming language)", "London")
     * sentences (optional): Number of sentences in extract (default: 3)
   - Example: {"topic": "Artificial Intelligence", "sentences": 3}

Your Task:
Analyze the user query and create a structured JSON plan with the following format:

{
  "task_description": "Clear description of what the user wants to accomplish",
  "intent": "search|compare|summarize|mixed",
  "steps": [
    {
      "step_number": 1,
      "action": "Descriptive action to perform",
      "tool": "github|weather|wikipedia",
      "parameters": {
        "param_name": "param_value"
      },
      "expected_output": "What this step should produce"
    }
  ],
  "comparison_mode": true|false,
  "entities": ["entity1", "entity2"]  // Only for comparison queries
}

Guidelines:
1. **Intent Detection**: Determine if the user wants to search, compare, summarize, or a mix
2. **Comparison Queries**: If comparing multiple entities (cities, repos, topics), set comparison_mode to true and list entities
3. **Step Creation**: Break down complex tasks into sequential steps
4. **Tool Selection**: Choose the most appropriate tool for each step
5. **Parameter Inference**: Infer reasonable parameters when not explicitly stated
6. **Clarity**: Make actions and expected outputs clear and specific

Examples:

Query: "What's the weather in Paris?"
Response:
{
  "task_description": "Get current weather information for Paris",
  "intent": "search",
  "steps": [
    {
      "step_number": 1,
      "action": "Fetch current weather for Paris",
      "tool": "weather",
      "parameters": {"city": "Paris", "units": "metric"},
      "expected_output": "Current temperature, conditions, humidity for Paris"
    }
  ],
  "comparison_mode": false
}

Query: "Compare weather in London and Tokyo"
Response:
{
  "task_description": "Compare current weather between London and Tokyo",
  "intent": "compare",
  "steps": [
    {
      "step_number": 1,
      "action": "Fetch current weather for London",
      "tool": "weather",
      "parameters": {"city": "London", "units": "metric"},
      "expected_output": "Weather data for London"
    },
    {
      "step_number": 2,
      "action": "Fetch current weather for Tokyo",
      "tool": "weather",
      "parameters": {"city": "Tokyo", "units": "metric"},
      "expected_output": "Weather data for Tokyo"
    }
  ],
  "comparison_mode": true,
  "entities": ["London", "Tokyo"]
}

Query: "Find top Python web frameworks on GitHub"
Response:
{
  "task_description": "Search for top Python web frameworks on GitHub",
  "intent": "search",
  "steps": [
    {
      "step_number": 1,
      "action": "Search GitHub for Python web frameworks",
      "tool": "github",
      "parameters": {"query": "python web framework", "sort": "stars", "limit": 5},
      "expected_output": "List of top Python web framework repositories with stars and descriptions"
    }
  ],
  "comparison_mode": false
}

Query: "Tell me about machine learning and show me popular ML repos"
Response:
{
  "task_description": "Get information about machine learning and find popular ML repositories",
  "intent": "mixed",
  "steps": [
    {
      "step_number": 1,
      "action": "Get Wikipedia summary for machine learning",
      "tool": "wikipedia",
      "parameters": {"topic": "Machine learning", "sentences": 3},
      "expected_output": "Summary of machine learning concept"
    },
    {
      "step_number": 2,
      "action": "Search GitHub for popular machine learning repositories",
      "tool": "github",
      "parameters": {"query": "machine learning", "sort": "stars", "limit": 5},
      "expected_output": "List of popular ML repositories"
    }
  ],
  "comparison_mode": false
}

Important: Always respond with valid JSON only. Do not include any explanatory text outside the JSON structure."""

        user_message = f"Create an execution plan for this query: {user_query}"
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        return messages
    
    def _validate_plan(self, plan: Dict[str, Any]) -> bool:
        """
        Validate that a plan has the required structure and valid values.
        
        Checks for required fields, validates field types, ensures step
        numbers are sequential, and verifies tool names are valid.
        
        Args:
            plan: The plan dictionary to validate
        
        Returns:
            bool: True if plan is valid, False otherwise
        """
        try:
            # Check required fields
            for field in self.PLAN_SCHEMA["required_fields"]:
                if field not in plan:
                    logger.error(f"Plan missing required field: {field}")
                    return False
            
            # Validate intent
            intent = plan.get("intent")
            if intent not in self.PLAN_SCHEMA["valid_intents"]:
                logger.error(f"Invalid intent: {intent}")
                return False
            
            # Validate steps
            steps = plan.get("steps", [])
            if not steps or not isinstance(steps, list):
                logger.error("Plan must have at least one step")
                return False
            
            # Validate each step
            for i, step in enumerate(steps):
                # Check required step fields
                for field in self.PLAN_SCHEMA["step_required_fields"]:
                    if field not in step:
                        logger.error(f"Step {i+1} missing required field: {field}")
                        return False
                
                # Validate step number is sequential
                expected_step_num = i + 1
                actual_step_num = step.get("step_number")
                if actual_step_num != expected_step_num:
                    logger.error(f"Step number mismatch: expected {expected_step_num}, got {actual_step_num}")
                    return False
                
                # Validate tool name
                tool = step.get("tool")
                if tool not in self.PLAN_SCHEMA["valid_tools"]:
                    logger.error(f"Invalid tool in step {i+1}: {tool}")
                    return False
                
                # Validate parameters is a dict
                parameters = step.get("parameters")
                if not isinstance(parameters, dict):
                    logger.error(f"Step {i+1} parameters must be a dictionary")
                    return False
            
            # If comparison_mode is true, entities should be present
            if plan.get("comparison_mode", False):
                entities = plan.get("entities", [])
                if not entities or not isinstance(entities, list):
                    logger.warning("Comparison mode is true but entities list is missing or invalid")
            
            logger.debug("Plan validation successful")
            return True
        
        except Exception as e:
            logger.error(f"Plan validation error: {str(e)}")
            return False
    
    def _detect_comparison_intent(self, user_query: str) -> bool:
        """
        Detect if the user query is asking for a comparison.
        
        Uses keyword matching to identify comparison requests.
        Common patterns include "compare", "vs", "versus", "difference between",
        "which is better", etc.
        
        Args:
            user_query: The user's query string
        
        Returns:
            bool: True if comparison intent detected, False otherwise
        """
        query_lower = user_query.lower()
        
        # Comparison keywords and patterns
        comparison_keywords = [
            "compare",
            "comparison",
            "vs",
            "versus",
            "difference between",
            "differences between",
            "which is better",
            "better than",
            "contrast",
            " and ",  # e.g., "weather in London and Paris"
            " or ",   # e.g., "should I use X or Y"
        ]
        
        # Check for comparison keywords
        for keyword in comparison_keywords:
            if keyword in query_lower:
                logger.debug(f"Comparison keyword detected: '{keyword}'")
                return True
        
        # Check for multiple entities with conjunctions
        # e.g., "weather in London, Paris, and Tokyo"
        if "," in query_lower and (" and " in query_lower or " or " in query_lower):
            logger.debug("Multiple entities with conjunctions detected")
            return True
        
        return False
