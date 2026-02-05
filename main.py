"""
Main orchestrator for AI Operations Assistant.

This module provides the AIOperationsAssistant class that coordinates
all agents and tools to process user queries end-to-end.
"""

import logging
import time
import json
from typing import Dict, Any, Optional

from ai_ops_assistant.config import Config, load_config
from ai_ops_assistant.llm.llm_client import LLMClient
from ai_ops_assistant.agents.planner import PlannerAgent
from ai_ops_assistant.agents.executor import ExecutorAgent
from ai_ops_assistant.agents.verifier import VerifierAgent
from ai_ops_assistant.tools.github_tool import GitHubTool
from ai_ops_assistant.tools.weather_tool import WeatherTool
from ai_ops_assistant.tools.wikipedia_tool import WikipediaTool


logger = logging.getLogger(__name__)


class AIOperationsAssistant:
    """
    Main orchestrator coordinating all agents and tools.
    
    This class provides the main entry point for processing user queries.
    It initializes all agents and tools, then coordinates their interaction
    through a three-stage pipeline: planning, execution, and verification.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the AI Operations Assistant.
        
        Sets up configuration, initializes the LLM client, creates all agents,
        and initializes all tools with appropriate API keys.
        
        Args:
            config: Optional Config instance. If None, loads from environment.
        
        Raises:
            ValueError: If configuration is invalid
            Exception: If initialization of any component fails
        """
        logger.info("Initializing AI Operations Assistant")
        
        # Load and validate configuration
        if config is None:
            config = load_config()
        else:
            config.validate()
        
        self.config = config
        logger.info(f"Configuration loaded: {config}")
        
        # Initialize LLM client
        try:
            # Determine API key and model based on provider
            if config.llm_provider == "gemini":
                api_key = config.gemini_api_key
                model = config.gemini_model
                base_url = None
            else:  # openai
                api_key = config.openai_api_key
                model = config.openai_model
                base_url = config.openai_base_url
            
            self.llm_client = LLMClient(
                api_key=api_key,
                model=model,
                base_url=base_url,
                provider=config.llm_provider
            )
            logger.info(f"LLM client initialized with provider={config.llm_provider}, model={model}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {str(e)}")
            raise
        
        # Initialize agents
        try:
            self.planner = PlannerAgent(self.llm_client)
            logger.info("Planner agent initialized")
            
            self.verifier = VerifierAgent(self.llm_client)
            logger.info("Verifier agent initialized")
        except Exception as e:
            logger.error(f"Failed to initialize agents: {str(e)}")
            raise
        
        # Initialize tools
        try:
            self.tools = self._initialize_tools()
            logger.info(f"Tools initialized: {list(self.tools.keys())}")
        except Exception as e:
            logger.error(f"Failed to initialize tools: {str(e)}")
            raise
        
        # Initialize executor with tools
        try:
            self.executor = ExecutorAgent(self.tools)
            logger.info("Executor agent initialized")
        except Exception as e:
            logger.error(f"Failed to initialize executor: {str(e)}")
            raise
        
        logger.info("AI Operations Assistant initialization complete")
    
    def _initialize_tools(self) -> Dict[str, Any]:
        """
        Initialize all tools with API keys from configuration.
        
        Creates instances of GitHubTool, WeatherTool, and WikipediaTool
        with appropriate API keys and configuration.
        
        Returns:
            Dictionary mapping tool names to tool instances:
            {
                "github": GitHubTool instance,
                "weather": WeatherTool instance,
                "wikipedia": WikipediaTool instance
            }
        
        Raises:
            Exception: If any tool initialization fails
        """
        tools = {}
        
        # Initialize GitHub tool
        try:
            github_tool = GitHubTool(api_token=self.config.github_token)
            tools["github"] = github_tool
            logger.info("GitHub tool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize GitHub tool: {str(e)}")
            raise
        
        # Initialize Weather tool
        try:
            weather_tool = WeatherTool(api_key=self.config.openweather_api_key)
            tools["weather"] = weather_tool
            logger.info("Weather tool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Weather tool: {str(e)}")
            raise
        
        # Initialize Wikipedia tool
        try:
            wikipedia_tool = WikipediaTool()
            tools["wikipedia"] = wikipedia_tool
            logger.info("Wikipedia tool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Wikipedia tool: {str(e)}")
            raise
        
        return tools
    
    def process_query(self, user_query: str) -> Dict[str, Any]:
        """
        Process a user query through the complete pipeline.
        
        Executes the three-stage pipeline:
        1. Planning: Convert natural language to structured plan
        2. Execution: Execute plan steps using tools
        3. Verification: Validate results and improve formatting
        
        Args:
            user_query: Natural language query from the user
        
        Returns:
            Dictionary containing complete results:
            {
                "query": str,
                "plan": dict,
                "execution": dict,
                "verification": dict,
                "total_time": float,
                "success": bool,
                "error": str (optional)
            }
        
        Raises:
            ValueError: If user_query is empty
        """
        # Input validation
        if not user_query or not user_query.strip():
            return {
                "query": "",
                "plan": None,
                "execution": None,
                "verification": None,
                "total_time": 0.0,
                "success": False,
                "error": "Please enter a query. Your question cannot be empty."
            }
        
        user_query = user_query.strip()
        
        # Check for very long queries
        if len(user_query) > 1000:
            return {
                "query": user_query[:100] + "...",
                "plan": None,
                "execution": None,
                "verification": None,
                "total_time": 0.0,
                "success": False,
                "error": "Your query is too long. Please keep it under 1000 characters and try again."
            }
        
        # Check for queries that are just special characters or numbers
        if not any(c.isalpha() for c in user_query):
            return {
                "query": user_query,
                "plan": None,
                "execution": None,
                "verification": None,
                "total_time": 0.0,
                "success": False,
                "error": "Please enter a meaningful question with words, not just numbers or symbols."
            }
        
        logger.info(f"Processing query: '{user_query}'")
        
        # Start timing
        start_time = time.time()
        
        result = {
            "query": user_query,
            "plan": None,
            "execution": None,
            "verification": None,
            "total_time": 0.0,
            "success": False
        }
        
        try:
            # Stage 1: Planning
            logger.info("Stage 1: Planning")
            plan_start = time.time()
            
            try:
                plan = self.planner.create_plan(user_query)
                result["plan"] = plan
                plan_time = time.time() - plan_start
                logger.info(f"Planning completed in {plan_time:.2f}s")
            except ValueError as e:
                # Validation or input errors
                error_msg = str(e)
                logger.error(f"Planning validation error: {error_msg}")
                result["error"] = f"Planning failed: {error_msg}. Please try a simpler or clearer query."
                result["total_time"] = time.time() - start_time
                return result
            except Exception as e:
                # Other planning errors
                error_msg = str(e)
                logger.error(f"Planning failed: {error_msg}")
                
                # Provide helpful error message based on error type
                if "rate limit" in error_msg.lower() or "quota" in error_msg.lower():
                    result["error"] = "API quota exceeded. Please wait for the quota to reset or try again later."
                elif "api key" in error_msg.lower() or "authentication" in error_msg.lower():
                    result["error"] = "API authentication failed. Please check your API keys configuration."
                elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                    result["error"] = "Network connection error. Please check your internet connection and try again."
                else:
                    result["error"] = f"Planning failed: {error_msg}"
                
                result["total_time"] = time.time() - start_time
                return result
            
            # Stage 2: Execution
            logger.info("Stage 2: Execution")
            exec_start = time.time()
            
            try:
                execution_result = self.executor.execute_plan(plan)
                result["execution"] = execution_result
                exec_time = time.time() - exec_start
                logger.info(f"Execution completed in {exec_time:.2f}s")
            except ValueError as e:
                # Invalid plan or parameters
                error_msg = str(e)
                logger.error(f"Execution validation error: {error_msg}")
                result["error"] = f"Execution failed: Invalid request parameters. {error_msg}"
                result["total_time"] = time.time() - start_time
                return result
            except Exception as e:
                # Other execution errors
                error_msg = str(e)
                logger.error(f"Execution failed: {error_msg}")
                
                # Provide helpful error message
                if "not found" in error_msg.lower() or "404" in error_msg:
                    result["error"] = "The requested information was not found. Please check your query and try again."
                elif "rate limit" in error_msg.lower() or "429" in error_msg:
                    result["error"] = "API rate limit exceeded. Please wait a moment and try again."
                elif "timeout" in error_msg.lower():
                    result["error"] = "Request timed out. The service might be slow. Please try again."
                else:
                    result["error"] = f"Execution failed: {error_msg}"
                
                result["total_time"] = time.time() - start_time
                return result
            
            # Stage 3: Verification
            logger.info("Stage 3: Verification")
            verify_start = time.time()
            
            try:
                verification = self.verifier.verify_results(plan, execution_result)
                result["verification"] = verification
                verify_time = time.time() - verify_start
                logger.info(f"Verification completed in {verify_time:.2f}s")
            except Exception as e:
                logger.warning(f"Verification failed: {str(e)}")
                # Verification failure is not critical - continue with results
                result["verification"] = {
                    "is_complete": False,
                    "is_correct": False,
                    "confidence_score": 0.0,
                    "issues": [f"Verification failed: {str(e)}"],
                    "formatted_output": "Verification unavailable",
                    "summary": "Verification failed",
                    "recommendations": []
                }
            
            # Calculate total time
            result["total_time"] = time.time() - start_time
            
            # Determine overall success
            result["success"] = (
                execution_result.get("success", False) and
                verification.get("is_complete", False)
            )
            
            logger.info(f"Query processing complete in {result['total_time']:.2f}s - Success: {result['success']}")
            
            return result
        
        except Exception as e:
            # Unexpected error
            logger.error(f"Unexpected error processing query: {str(e)}")
            result["error"] = f"Unexpected error: {str(e)}"
            result["total_time"] = time.time() - start_time
            return result


def main():
    """
    Main entry point for CLI usage.
    
    Provides a simple command-line interface for testing the assistant.
    """
    import sys
    
    # Check if query provided as command-line argument
    if len(sys.argv) < 2:
        print("AI Operations Assistant - CLI")
        print("=" * 60)
        print("\nUsage: python main.py \"<your query>\"")
        print("\nExamples:")
        print("  python main.py \"What's the weather in London?\"")
        print("  python main.py \"Compare weather in London and Paris\"")
        print("  python main.py \"Find top Python web frameworks on GitHub\"")
        print("  python main.py \"Tell me about machine learning\"")
        print("\n" + "=" * 60)
        sys.exit(1)
    
    # Get query from command-line arguments
    user_query = " ".join(sys.argv[1:])
    
    try:
        # Initialize assistant
        print("Initializing AI Operations Assistant...")
        assistant = AIOperationsAssistant()
        print("✓ Initialization complete\n")
        
        # Process query
        print(f"Processing query: {user_query}")
        print("=" * 60)
        
        result = assistant.process_query(user_query)
        
        # Display results
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)
        
        if result.get("success"):
            print("✓ Status: SUCCESS")
        else:
            print("✗ Status: FAILED")
        
        print(f"Total Time: {result.get('total_time', 0):.2f}s")
        
        if result.get("error"):
            print(f"\nError: {result['error']}")
        
        # Display plan
        if result.get("plan"):
            print("\n--- PLAN ---")
            print(json.dumps(result["plan"], indent=2))
        
        # Display execution results
        if result.get("execution"):
            execution = result["execution"]
            print("\n--- EXECUTION ---")
            print(f"Steps Completed: {execution.get('steps_completed', 0)}")
            print(f"Steps Failed: {execution.get('steps_failed', 0)}")
            
            for step_result in execution.get("results", []):
                step_num = step_result.get("step_number", 0)
                status = step_result.get("status", "unknown")
                print(f"\nStep {step_num}: {status.upper()}")
                
                if status == "success":
                    data = step_result.get("data")
                    if data:
                        print(f"Data: {json.dumps(data, indent=2)}")
                else:
                    error = step_result.get("error", "Unknown error")
                    print(f"Error: {error}")
        
        # Display verification
        if result.get("verification"):
            verification = result["verification"]
            print("\n--- VERIFICATION ---")
            print(f"Complete: {verification.get('is_complete', False)}")
            print(f"Correct: {verification.get('is_correct', False)}")
            print(f"Confidence: {verification.get('confidence_score', 0):.2f}")
            
            if verification.get("issues"):
                print("\nIssues:")
                for issue in verification["issues"]:
                    print(f"  - {issue}")
            
            if verification.get("formatted_output"):
                print("\nFormatted Output:")
                print(verification["formatted_output"])
            
            if verification.get("summary"):
                print(f"\nSummary: {verification['summary']}")
            
            if verification.get("recommendations"):
                print("\nRecommendations:")
                for rec in verification["recommendations"]:
                    print(f"  - {rec}")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        logger.exception("Fatal error in main")
        sys.exit(1)


if __name__ == "__main__":
    main()
