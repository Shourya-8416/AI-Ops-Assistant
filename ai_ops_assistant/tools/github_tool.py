"""
GitHub Tool for AI Operations Assistant.

This module provides integration with the GitHub REST API for searching
repositories, retrieving repository details, and comparing multiple repositories.
"""

import logging
import time
from typing import Dict, List, Optional
import requests


logger = logging.getLogger(__name__)


class GitHubTool:
    """
    Interacts with GitHub REST API for repository search and metadata.
    
    Supports searching repositories, fetching detailed information,
    and comparing multiple repositories. Handles rate limiting and
    common API errors gracefully.
    """
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize GitHub Tool with optional authentication token.
        
        Args:
            api_token: Optional GitHub personal access token for authentication.
                      Increases rate limit from 60 to 5000 requests/hour.
        """
        self.api_token = api_token
        self.session = requests.Session()
        
        # Set up headers
        self.session.headers.update({
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AI-Operations-Assistant/1.0"
        })
        
        # Add authentication if token provided
        if self.api_token:
            self.session.headers.update({
                "Authorization": f"token {self.api_token}"
            })
            logger.info("GitHub Tool initialized with authentication token")
        else:
            logger.warning("GitHub Tool initialized without authentication token (rate limit: 60 req/hour)")
    
    def search_repositories(self, query: str, sort: str = "stars", limit: int = 5) -> List[Dict]:
        """
        Search GitHub repositories by query string.
        
        Args:
            query: Search query (e.g., "machine learning", "language:python stars:>1000")
            sort: Sort criteria - "stars", "forks", or "updated" (default: "stars")
            limit: Maximum number of results to return (default: 5)
        
        Returns:
            List of repository dictionaries with key information.
            Each dictionary contains: name, full_name, description, stars,
            forks, language, url, created_at, updated_at.
        
        Raises:
            requests.exceptions.RequestException: If API request fails.
        """
        logger.info(f"Searching repositories with query: '{query}', sort: {sort}, limit: {limit}")
        
        # Validate sort parameter
        valid_sorts = ["stars", "forks", "updated"]
        if sort not in valid_sorts:
            logger.warning(f"Invalid sort parameter '{sort}', defaulting to 'stars'")
            sort = "stars"
        
        # Build request parameters
        params = {
            "q": query,
            "sort": sort,
            "order": "desc",
            "per_page": min(limit, 100)  # GitHub API max is 100
        }
        
        try:
            # Make API request
            response = self._make_request("/search/repositories", params=params)
            
            # Extract and format results
            items = response.get("items", [])
            results = []
            
            for item in items[:limit]:
                repo_data = self._format_repository_data(item)
                results.append(repo_data)
            
            logger.info(f"Found {len(results)} repositories")
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to search repositories: {e}")
            raise
    
    def get_repository_details(self, owner: str, repo: str) -> Dict:
        """
        Get detailed information about a specific repository.
        
        Args:
            owner: Repository owner (username or organization)
            repo: Repository name
        
        Returns:
            Dictionary with detailed repository information including:
            name, full_name, description, stars, forks, language, url,
            created_at, updated_at, open_issues, watchers, default_branch,
            topics, license, homepage.
        
        Raises:
            requests.exceptions.RequestException: If API request fails.
            requests.exceptions.HTTPError: If repository not found (404).
        """
        logger.info(f"Fetching details for repository: {owner}/{repo}")
        
        try:
            # Make API request
            endpoint = f"/repos/{owner}/{repo}"
            response = self._make_request(endpoint)
            
            # Format detailed response
            repo_data = self._format_repository_data(response, detailed=True)
            
            logger.info(f"Successfully fetched details for {owner}/{repo}")
            return repo_data
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.error(f"Repository not found: {owner}/{repo}")
                raise
            else:
                logger.error(f"Failed to fetch repository details: {e}")
                raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch repository details: {e}")
            raise
    
    def compare_repositories(self, repo_queries: List[str]) -> List[Dict]:
        """
        Compare multiple repositories by searching for each query.
        
        This method searches for each query and returns the top result,
        allowing for side-by-side comparison of different repositories.
        
        Args:
            repo_queries: List of repository queries or "owner/repo" strings.
                         Examples: ["tensorflow/tensorflow", "pytorch/pytorch"]
                         or ["machine learning python", "deep learning framework"]
        
        Returns:
            List of repository dictionaries, one for each query.
            Returns partial results if some queries fail.
        
        Note:
            This method is resilient to partial failures - if one query fails,
            it will still return results for successful queries.
        """
        logger.info(f"Comparing {len(repo_queries)} repositories")
        
        results = []
        
        for query in repo_queries:
            try:
                # Check if query is in "owner/repo" format
                if "/" in query and len(query.split("/")) == 2:
                    owner, repo = query.split("/")
                    # Try to get specific repository details
                    try:
                        repo_data = self.get_repository_details(owner, repo)
                        results.append(repo_data)
                        continue
                    except requests.exceptions.HTTPError as e:
                        if e.response.status_code == 404:
                            logger.warning(f"Repository {query} not found, falling back to search")
                        else:
                            raise
                
                # Fall back to search (or if not in owner/repo format)
                search_results = self.search_repositories(query, limit=1)
                
                if search_results:
                    results.append(search_results[0])
                else:
                    logger.warning(f"No results found for query: {query}")
                    # Add placeholder for failed query
                    results.append({
                        "name": query,
                        "error": "No results found",
                        "full_name": query,
                        "description": None,
                        "stars": 0,
                        "forks": 0,
                        "language": None,
                        "url": None
                    })
                    
            except Exception as e:
                logger.error(f"Failed to fetch data for query '{query}': {e}")
                # Add error placeholder
                results.append({
                    "name": query,
                    "error": str(e),
                    "full_name": query,
                    "description": None,
                    "stars": 0,
                    "forks": 0,
                    "language": None,
                    "url": None
                })
        
        logger.info(f"Comparison complete: {len(results)} results")
        return results
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make a request to the GitHub API with error handling and rate limit management.
        
        Args:
            endpoint: API endpoint path (e.g., "/search/repositories")
            params: Optional query parameters
        
        Returns:
            JSON response as dictionary
        
        Raises:
            requests.exceptions.HTTPError: For HTTP errors (404, 403, etc.)
            requests.exceptions.RequestException: For network errors
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        logger.debug(f"Making request to: {url}")
        logger.debug(f"Parameters: {params}")
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            
            # Handle rate limiting
            if response.status_code == 403:
                self._handle_rate_limit(response)
            
            # Raise exception for HTTP errors
            response.raise_for_status()
            
            # Log rate limit info
            self._log_rate_limit_info(response)
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
    
    def _handle_rate_limit(self, response: requests.Response) -> None:
        """
        Handle GitHub API rate limiting.
        
        Args:
            response: Response object from GitHub API
        
        Raises:
            requests.exceptions.HTTPError: If rate limit exceeded and cannot wait
        """
        # Check if this is a rate limit error
        remaining = response.headers.get("X-RateLimit-Remaining", "0")
        reset_time = response.headers.get("X-RateLimit-Reset", "0")
        
        if remaining == "0":
            try:
                reset_timestamp = int(reset_time)
                current_time = int(time.time())
                wait_time = reset_timestamp - current_time
                
                if wait_time > 0 and wait_time < 300:  # Only wait up to 5 minutes
                    logger.warning(f"Rate limit exceeded. Waiting {wait_time} seconds...")
                    time.sleep(wait_time + 1)  # Add 1 second buffer
                    return
                else:
                    logger.error(f"Rate limit exceeded. Reset in {wait_time} seconds (too long to wait)")
            except (ValueError, TypeError):
                logger.error("Rate limit exceeded and cannot determine reset time")
        
        # If we get here, we couldn't handle the rate limit
        error_message = "GitHub API rate limit exceeded"
        if not self.api_token:
            error_message += " (consider using authentication token for higher limits)"
        
        logger.error(error_message)
        raise requests.exceptions.HTTPError(error_message, response=response)
    
    def _log_rate_limit_info(self, response: requests.Response) -> None:
        """
        Log current rate limit information from response headers.
        
        Args:
            response: Response object from GitHub API
        """
        limit = response.headers.get("X-RateLimit-Limit", "unknown")
        remaining = response.headers.get("X-RateLimit-Remaining", "unknown")
        
        logger.debug(f"Rate limit: {remaining}/{limit} remaining")
    
    def _format_repository_data(self, raw_data: Dict, detailed: bool = False) -> Dict:
        """
        Format raw GitHub API response into clean repository data.
        
        Args:
            raw_data: Raw JSON response from GitHub API
            detailed: Whether to include additional detailed fields
        
        Returns:
            Formatted repository dictionary
        """
        # Basic fields (always included)
        formatted = {
            "name": raw_data.get("name", ""),
            "full_name": raw_data.get("full_name", ""),
            "description": raw_data.get("description", ""),
            "stars": raw_data.get("stargazers_count", 0),
            "forks": raw_data.get("forks_count", 0),
            "language": raw_data.get("language", ""),
            "url": raw_data.get("html_url", ""),
            "created_at": raw_data.get("created_at", ""),
            "updated_at": raw_data.get("updated_at", "")
        }
        
        # Additional detailed fields
        if detailed:
            formatted.update({
                "open_issues": raw_data.get("open_issues_count", 0),
                "watchers": raw_data.get("watchers_count", 0),
                "default_branch": raw_data.get("default_branch", "main"),
                "topics": raw_data.get("topics", []),
                "license": raw_data.get("license", {}).get("name", None) if raw_data.get("license") else None,
                "homepage": raw_data.get("homepage", ""),
                "size": raw_data.get("size", 0),
                "has_issues": raw_data.get("has_issues", False),
                "has_wiki": raw_data.get("has_wiki", False),
                "archived": raw_data.get("archived", False)
            })
        
        return formatted
