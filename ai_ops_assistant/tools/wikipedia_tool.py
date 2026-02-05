"""
Wikipedia Tool for AI Operations Assistant.

This module provides integration with the Wikipedia REST API for fetching
article summaries, searching articles, and comparing multiple topics.
"""

import logging
from typing import Dict, List, Optional
import requests


logger = logging.getLogger(__name__)


class WikipediaTool:
    """
    Interacts with Wikipedia REST API for article summaries.
    
    Supports fetching article summaries, searching for articles,
    and comparing multiple topics. Handles disambiguation pages
    and common API errors gracefully.
    """
    
    BASE_URL = "https://en.wikipedia.org"
    REST_API_BASE = "https://en.wikipedia.org/api/rest_v1"
    
    def __init__(self):
        """
        Initialize Wikipedia Tool.
        
        No authentication required for Wikipedia API.
        """
        self.session = requests.Session()
        
        # Set up headers
        self.session.headers.update({
            "User-Agent": "AI-Operations-Assistant/1.0 (Educational Project)"
        })
        
        logger.info("Wikipedia Tool initialized")
    
    def get_summary(self, topic: str, sentences: int = 3) -> Dict:
        """
        Get a summary of a Wikipedia article.
        
        Args:
            topic: Article topic/title (e.g., "Python (programming language)", "London")
            sentences: Number of sentences to include in extract (default: 3)
                      Note: Wikipedia API returns full summary, this is informational
        
        Returns:
            Dictionary with article information including:
            - title: Article title
            - summary: Full summary text
            - extract: Short extract (first few sentences)
            - url: Wikipedia article URL
            - thumbnail: Thumbnail image URL (if available)
            - description: Short description
        
        Raises:
            requests.exceptions.HTTPError: If article not found (404) or API error.
            requests.exceptions.RequestException: For network errors.
            ValueError: If topic is empty or article not found.
        """
        if not topic or not topic.strip():
            raise ValueError("Topic cannot be empty")
        
        topic = topic.strip()
        logger.info(f"Fetching Wikipedia summary for topic: '{topic}'")
        
        try:
            # Try to get the article summary
            endpoint = f"/page/summary/{self._encode_title(topic)}"
            response = self._make_request(endpoint)
            
            # Check if this is a disambiguation page
            if response.get("type") == "disambiguation":
                logger.warning(f"Topic '{topic}' is a disambiguation page")
                # Try to handle disambiguation
                alternative = self._handle_disambiguation(topic)
                if alternative and alternative != topic:
                    logger.info(f"Trying alternative topic: '{alternative}'")
                    return self.get_summary(alternative, sentences)
                else:
                    # Return disambiguation info
                    return {
                        "title": response.get("title", topic),
                        "summary": response.get("extract", "This is a disambiguation page. Please be more specific."),
                        "extract": response.get("extract", "")[:200] + "...",
                        "url": response.get("content_urls", {}).get("desktop", {}).get("page", ""),
                        "thumbnail": None,
                        "description": "Disambiguation page",
                        "type": "disambiguation"
                    }
            
            # Parse and format the summary
            summary_data = self._parse_summary_data(response, sentences)
            
            logger.info(f"Successfully fetched summary for '{summary_data['title']}'")
            return summary_data
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.error(f"Article not found: {topic}")
                # Try searching for similar articles
                search_results = self.search_articles(topic, limit=1)
                if search_results:
                    suggestion = search_results[0]
                    raise ValueError(f"Article '{topic}' not found. Did you mean '{suggestion}'?")
                else:
                    raise ValueError(f"Article '{topic}' not found. Please check the spelling or try a different search term.")
            else:
                logger.error(f"Failed to fetch Wikipedia summary: {e}")
                raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch Wikipedia summary: {e}")
            raise
    
    def search_articles(self, query: str, limit: int = 5) -> List[str]:
        """
        Search for Wikipedia articles by query string.
        
        Uses the OpenSearch API to find articles matching the query.
        
        Args:
            query: Search query (e.g., "machine learning", "Python programming")
            limit: Maximum number of results to return (default: 5)
        
        Returns:
            List of article titles matching the query.
        
        Raises:
            requests.exceptions.RequestException: If API request fails.
            ValueError: If query is empty.
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        query = query.strip()
        logger.info(f"Searching Wikipedia articles for query: '{query}', limit: {limit}")
        
        try:
            # Use OpenSearch API
            params = {
                "action": "opensearch",
                "search": query,
                "limit": min(limit, 10),  # Wikipedia typically returns max 10
                "namespace": 0,  # Main namespace only
                "format": "json"
            }
            
            url = f"{self.BASE_URL}/w/api.php"
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # OpenSearch returns: [query, [titles], [descriptions], [urls]]
            if len(data) >= 2:
                titles = data[1][:limit]
                logger.info(f"Found {len(titles)} articles")
                return titles
            else:
                logger.warning(f"No results found for query: {query}")
                return []
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to search Wikipedia articles: {e}")
            raise
    
    def compare_topics(self, topics: List[str]) -> List[Dict]:
        """
        Compare multiple Wikipedia topics by fetching summaries for each.
        
        This method fetches article summaries for each topic and returns results
        for side-by-side comparison. It is resilient to partial failures -
        if one topic fails, it will still return results for successful queries.
        
        Args:
            topics: List of article topics to compare.
                   Examples: ["Python (programming language)", "Java (programming language)"]
        
        Returns:
            List of summary dictionaries, one for each topic.
            Returns partial results if some queries fail.
            Failed queries include an "error" field.
        
        Note:
            This method continues execution even if individual topic queries fail,
            providing partial results for successful queries.
        """
        logger.info(f"Comparing {len(topics)} Wikipedia topics")
        
        results = []
        
        for topic in topics:
            try:
                summary_data = self.get_summary(topic)
                results.append(summary_data)
                
            except ValueError as e:
                # Article not found
                logger.warning(f"Failed to fetch summary for '{topic}': {e}")
                results.append({
                    "title": topic,
                    "summary": None,
                    "extract": None,
                    "url": None,
                    "thumbnail": None,
                    "description": None,
                    "error": str(e)
                })
                
            except Exception as e:
                # Other errors
                logger.error(f"Unexpected error fetching summary for '{topic}': {e}")
                results.append({
                    "title": topic,
                    "summary": None,
                    "extract": None,
                    "url": None,
                    "thumbnail": None,
                    "description": None,
                    "error": f"Unexpected error: {str(e)}"
                })
        
        logger.info(f"Topic comparison complete: {len(results)} results")
        return results
    
    def _make_request(self, endpoint: str) -> Dict:
        """
        Make a request to the Wikipedia REST API with error handling.
        
        Args:
            endpoint: API endpoint path (e.g., "/page/summary/Python")
        
        Returns:
            JSON response as dictionary
        
        Raises:
            requests.exceptions.HTTPError: For HTTP errors (404, etc.)
            requests.exceptions.RequestException: For network errors
        """
        url = f"{self.REST_API_BASE}{endpoint}"
        
        logger.debug(f"Making request to: {url}")
        
        try:
            response = self.session.get(url, timeout=30)
            
            # Raise exception for HTTP errors
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
    
    def _handle_disambiguation(self, topic: str) -> Optional[str]:
        """
        Handle Wikipedia disambiguation pages by searching for alternatives.
        
        When a topic leads to a disambiguation page, this method searches
        for the most relevant alternative article.
        
        Args:
            topic: Original topic that led to disambiguation
        
        Returns:
            Alternative topic title, or None if no good alternative found
        """
        logger.info(f"Handling disambiguation for topic: '{topic}'")
        
        try:
            # Search for the topic to find alternatives
            search_results = self.search_articles(topic, limit=3)
            
            if search_results:
                # Return the first result that's not the disambiguation page itself
                for result in search_results:
                    if not result.endswith("(disambiguation)"):
                        logger.info(f"Found alternative: '{result}'")
                        return result
            
            logger.warning(f"No good alternative found for disambiguation page: {topic}")
            return None
            
        except Exception as e:
            logger.error(f"Error handling disambiguation: {e}")
            return None
    
    def _encode_title(self, title: str) -> str:
        """
        Encode article title for use in URL.
        
        Wikipedia uses underscores instead of spaces in URLs.
        
        Args:
            title: Article title
        
        Returns:
            URL-encoded title
        """
        # Replace spaces with underscores (Wikipedia convention)
        encoded = title.replace(" ", "_")
        return encoded
    
    def _parse_summary_data(self, raw_data: Dict, sentences: int = 3) -> Dict:
        """
        Parse raw Wikipedia API response into clean summary data.
        
        Args:
            raw_data: Raw JSON response from Wikipedia REST API
            sentences: Number of sentences to include in extract
        
        Returns:
            Formatted summary dictionary with clean field names
        """
        # Extract main fields
        title = raw_data.get("title", "")
        extract = raw_data.get("extract", "")
        
        # Get thumbnail if available
        thumbnail_data = raw_data.get("thumbnail")
        thumbnail_url = thumbnail_data.get("source") if thumbnail_data else None
        
        # Get URLs
        content_urls = raw_data.get("content_urls", {})
        desktop_url = content_urls.get("desktop", {}).get("page", "")
        
        # Create short extract (first N sentences)
        short_extract = self._extract_sentences(extract, sentences)
        
        # Format summary data
        formatted = {
            "title": title,
            "summary": extract,
            "extract": short_extract,
            "url": desktop_url,
            "thumbnail": thumbnail_url,
            "description": raw_data.get("description", ""),
            "type": raw_data.get("type", "standard"),
            "lang": raw_data.get("lang", "en"),
            "timestamp": raw_data.get("timestamp", "")
        }
        
        return formatted
    
    def _extract_sentences(self, text: str, num_sentences: int) -> str:
        """
        Extract the first N sentences from text.
        
        Args:
            text: Full text
            num_sentences: Number of sentences to extract
        
        Returns:
            First N sentences
        """
        if not text:
            return ""
        
        # Simple sentence splitting (split on ". " followed by capital letter or end)
        sentences = []
        current = ""
        
        for i, char in enumerate(text):
            current += char
            
            # Check for sentence end
            if char == "." and (i + 1 >= len(text) or 
                               (i + 1 < len(text) and text[i + 1] == " " and 
                                i + 2 < len(text) and text[i + 2].isupper())):
                sentences.append(current.strip())
                current = ""
                
                if len(sentences) >= num_sentences:
                    break
        
        # Add remaining text if we didn't reach num_sentences
        if current.strip() and len(sentences) < num_sentences:
            sentences.append(current.strip())
        
        result = " ".join(sentences[:num_sentences])
        
        # If we extracted less than the full text, add ellipsis
        if len(result) < len(text):
            result += "..."
        
        return result
