"""
LLM Client for AI Operations Assistant.

This module provides a centralized interface for all LLM interactions,
supporting OpenAI-compatible APIs with retry logic, logging, and error handling.
"""

import logging
import time
import json
from typing import List, Dict, Optional, Any

try:
    from openai import OpenAI, OpenAIError, APIError, APIConnectionError, RateLimitError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


logger = logging.getLogger(__name__)


class LLMClient:
    """
    Centralized client for LLM API interactions.
    
    Supports OpenAI-compatible APIs with features including:
    - Configurable model and parameters
    - JSON mode for structured outputs
    - Request/response logging
    - Automatic retry with exponential backoff
    - Token usage tracking
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4",
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_retries: int = 3,
        timeout: int = 30,
        provider: str = "openai"
    ):
        """
        Initialize the LLM client.
        
        Args:
            api_key: API key (OpenAI or Gemini)
            model: Model name to use (default: gpt-4 for OpenAI, gemini-1.5-flash for Gemini)
            base_url: Optional custom base URL for OpenAI-compatible APIs
            temperature: Sampling temperature (0.0 to 2.0, default: 0.7)
            max_retries: Maximum number of retry attempts (default: 3)
            timeout: Request timeout in seconds (default: 30)
            provider: LLM provider - "openai" or "gemini" (default: openai)
        
        Raises:
            ValueError: If api_key is empty or invalid, or provider not available
        """
        if not api_key:
            raise ValueError("API key is required")
        
        self.provider = provider.lower()
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        self.timeout = timeout
        
        # Initialize provider-specific client
        if self.provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ValueError("OpenAI library not installed. Run: pip install openai")
            
            client_kwargs = {
                "api_key": api_key,
                "timeout": timeout,
                "max_retries": 0  # We handle retries manually for better control
            }
            
            if base_url:
                client_kwargs["base_url"] = base_url
            
            self.client = OpenAI(**client_kwargs)
            
        elif self.provider == "gemini":
            if not GEMINI_AVAILABLE:
                raise ValueError("Gemini library not installed. Run: pip install google-generativeai")
            
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(model)
            
        else:
            raise ValueError(f"Unsupported provider: {provider}. Must be 'openai' or 'gemini'")
        
        logger.info(
            f"LLM Client initialized with provider={provider}, model={model}, "
            f"temperature={temperature}, max_retries={max_retries}"
        )
    
    def generate_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2000,
        response_format: Optional[Dict] = None
    ) -> str:
        """
        Generate a text completion from the LLM.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            max_tokens: Maximum tokens in the response (default: 2000)
            response_format: Optional response format specification (e.g., {"type": "json_object"})
        
        Returns:
            str: The generated completion text
        
        Raises:
            ValueError: If messages is empty or invalid
            OpenAIError: If the API request fails after all retries
        """
        if not messages:
            raise ValueError("Messages list cannot be empty")
        
        self._log_request(messages)
        
        # Retry logic with exponential backoff
        last_error = None
        for attempt in range(self.max_retries):
            try:
                if self.provider == "openai":
                    completion = self._generate_openai(messages, max_tokens, response_format)
                elif self.provider == "gemini":
                    completion = self._generate_gemini(messages, max_tokens, response_format)
                else:
                    raise ValueError(f"Unsupported provider: {self.provider}")
                
                self._log_response(completion)
                return completion
            
            except Exception as e:
                # Handle provider-specific errors
                if self.provider == "openai" and OPENAI_AVAILABLE:
                    if isinstance(e, RateLimitError):
                        last_error = e
                        wait_time = self._calculate_backoff(attempt)
                        logger.warning(
                            f"Rate limit exceeded (attempt {attempt + 1}/{self.max_retries}). "
                            f"Retrying in {wait_time}s..."
                        )
                        time.sleep(wait_time)
                        continue
                    elif isinstance(e, APIConnectionError):
                        last_error = e
                        wait_time = self._calculate_backoff(attempt)
                        logger.warning(
                            f"API connection error (attempt {attempt + 1}/{self.max_retries}). "
                            f"Retrying in {wait_time}s... Error: {str(e)}"
                        )
                        time.sleep(wait_time)
                        continue
                    elif isinstance(e, APIError):
                        if hasattr(e, 'status_code') and 500 <= e.status_code < 600:
                            last_error = e
                            wait_time = self._calculate_backoff(attempt)
                            logger.warning(
                                f"API error {e.status_code} (attempt {attempt + 1}/{self.max_retries}). "
                                f"Retrying in {wait_time}s..."
                            )
                            time.sleep(wait_time)
                            continue
                        else:
                            logger.error(f"Non-retryable API error: {str(e)}")
                            raise
                
                # Check if error is retryable (for Gemini or generic errors)
                error_str = str(e).lower()
                is_retryable = any(keyword in error_str for keyword in [
                    "rate limit", "quota", "429", "503", "timeout", "connection"
                ])
                
                if is_retryable and attempt < self.max_retries - 1:
                    last_error = e
                    wait_time = self._calculate_backoff(attempt)
                    logger.warning(
                        f"Retryable error (attempt {attempt + 1}/{self.max_retries}). "
                        f"Retrying in {wait_time}s... Error: {str(e)}"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    # Non-retryable error
                    logger.error(f"Non-retryable error: {str(e)}")
                    raise
        
        # All retries exhausted
        error_msg = f"Failed after {self.max_retries} attempts. Last error: {str(last_error)}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    def generate_json_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Generate a JSON completion from the LLM.
        
        Uses JSON mode to ensure the response is valid JSON.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            max_tokens: Maximum tokens in the response (default: 2000)
        
        Returns:
            dict: Parsed JSON response
        
        Raises:
            ValueError: If messages is empty or response is not valid JSON
            OpenAIError: If the API request fails after all retries
        """
        # Enable JSON mode
        response_format = {"type": "json_object"}
        
        # Get completion with JSON mode
        completion_text = self.generate_completion(
            messages=messages,
            max_tokens=max_tokens,
            response_format=response_format
        )
        
        # Parse JSON response
        try:
            json_response = json.loads(completion_text)
            logger.debug("Successfully parsed JSON response")
            return json_response
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON response: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Invalid JSON content: {completion_text}")
            raise ValueError(error_msg)
    
    def _calculate_backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff wait time.
        
        Args:
            attempt: Current attempt number (0-indexed)
        
        Returns:
            float: Wait time in seconds
        """
        # Exponential backoff: 1s, 2s, 4s, 8s, ...
        return min(2 ** attempt, 60)  # Cap at 60 seconds
    
    def _log_request(self, messages: List[Dict[str, str]]) -> None:
        """
        Log the LLM request details.
        
        Args:
            messages: List of message dictionaries
        """
        logger.debug("=" * 80)
        logger.debug("LLM REQUEST")
        logger.debug(f"Model: {self.model}")
        logger.debug(f"Temperature: {self.temperature}")
        logger.debug("Messages:")
        for i, msg in enumerate(messages):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            # Truncate long content for logging
            content_preview = content[:200] + "..." if len(content) > 200 else content
            logger.debug(f"  [{i}] {role}: {content_preview}")
        logger.debug("=" * 80)
    
    def _log_response(self, response: str) -> None:
        """
        Log the LLM response details.
        
        Args:
            response: The completion text
        """
        logger.debug("=" * 80)
        logger.debug("LLM RESPONSE")
        # Truncate long responses for logging
        response_preview = response[:500] + "..." if len(response) > 500 else response
        logger.debug(response_preview)
        logger.debug("=" * 80)

    def _generate_openai(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        response_format: Optional[Dict]
    ) -> str:
        """Generate completion using OpenAI API."""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": max_tokens
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        response = self.client.chat.completions.create(**kwargs)
        
        # Extract completion text
        completion = response.choices[0].message.content
        
        # Log token usage
        if hasattr(response, 'usage') and response.usage:
            logger.debug(
                f"Token usage - Prompt: {response.usage.prompt_tokens}, "
                f"Completion: {response.usage.completion_tokens}, "
                f"Total: {response.usage.total_tokens}"
            )
        
        return completion
    
    def _generate_gemini(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        response_format: Optional[Dict]
    ) -> str:
        """Generate completion using Gemini API."""
        # Convert messages to Gemini format
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                prompt_parts.append(f"Instructions: {content}\n")
            elif role == "user":
                prompt_parts.append(f"User: {content}\n")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}\n")
        
        prompt = "\n".join(prompt_parts)
        
        # Add JSON format instruction if needed
        if response_format and response_format.get("type") == "json_object":
            prompt += "\n\nIMPORTANT: You MUST respond with valid JSON only. Do not include any text before or after the JSON. Start your response with { and end with }."
        
        # Generate response
        generation_config = {
            "temperature": self.temperature,
            "max_output_tokens": max_tokens,
        }
        
        # Use JSON response mode if requested
        if response_format and response_format.get("type") == "json_object":
            generation_config["response_mime_type"] = "application/json"
        
        response = self.client.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        completion = response.text
        
        return completion
