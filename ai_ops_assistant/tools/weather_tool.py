"""
Weather Tool for AI Operations Assistant.

This module provides integration with the OpenWeather API for fetching
current weather data, supporting single city queries and multi-city comparisons.
"""

import logging
import time
from typing import Dict, List, Optional
import requests


logger = logging.getLogger(__name__)


class WeatherTool:
    """
    Interacts with OpenWeather API for current weather data.
    
    Supports fetching current weather for cities, comparing weather
    across multiple cities, and handling location ambiguity.
    Provides temperature, conditions, humidity, and wind information.
    """
    
    BASE_URL = "https://api.openweathermap.org/data/2.5"
    
    def __init__(self, api_key: str):
        """
        Initialize Weather Tool with OpenWeather API key.
        
        Args:
            api_key: OpenWeather API key (required).
                    Get one from: https://openweathermap.org/api
        
        Raises:
            ValueError: If api_key is None or empty.
        """
        if not api_key:
            raise ValueError("OpenWeather API key is required")
        
        self.api_key = api_key
        self.session = requests.Session()
        
        # Set up headers
        self.session.headers.update({
            "User-Agent": "AI-Operations-Assistant/1.0"
        })
        
        logger.info("Weather Tool initialized with API key")
    
    def get_current_weather(self, city: str, units: str = "metric") -> Dict:
        """
        Get current weather data for a specific city.
        
        Args:
            city: City name (e.g., "London", "New York", "Tokyo").
                 Can include country code for disambiguation (e.g., "London,GB").
            units: Unit system - "metric" (Celsius), "imperial" (Fahrenheit),
                  or "standard" (Kelvin). Default: "metric".
        
        Returns:
            Dictionary with weather information including:
            - city: City name
            - country: Country code
            - temperature: Current temperature
            - feels_like: Feels-like temperature
            - conditions: Weather conditions description
            - humidity: Humidity percentage
            - wind_speed: Wind speed
            - timestamp: Data timestamp
            - units: Unit system used
        
        Raises:
            requests.exceptions.HTTPError: If city not found (404) or API error.
            requests.exceptions.RequestException: For network errors.
            ValueError: If units parameter is invalid.
        """
        logger.info(f"Fetching weather for city: '{city}', units: {units}")
        
        # Validate units parameter
        valid_units = ["metric", "imperial", "standard"]
        if units not in valid_units:
            logger.warning(f"Invalid units parameter '{units}', defaulting to 'metric'")
            units = "metric"
        
        # Build request parameters
        params = {
            "q": city,
            "appid": self.api_key,
            "units": units
        }
        
        try:
            # Make API request
            response = self._make_request("/weather", params=params)
            
            # Parse and format weather data
            weather_data = self._parse_weather_data(response, units)
            
            logger.info(f"Successfully fetched weather for {weather_data['city']}, {weather_data['country']}")
            return weather_data
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.error(f"City not found: {city}")
                raise ValueError(f"City '{city}' not found. Please check the spelling or try adding a country code (e.g., 'London,GB')")
            elif e.response.status_code == 401:
                logger.error("Invalid API key")
                raise ValueError("Invalid OpenWeather API key. Please check your configuration.")
            else:
                logger.error(f"Failed to fetch weather data: {e}")
                raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch weather data: {e}")
            raise
    
    def compare_weather(self, cities: List[str], units: str = "metric") -> List[Dict]:
        """
        Compare weather across multiple cities.
        
        This method fetches weather data for each city and returns results
        for side-by-side comparison. It is resilient to partial failures -
        if one city fails, it will still return results for successful queries.
        
        Args:
            cities: List of city names to compare.
                   Examples: ["London", "Paris", "Tokyo"]
                   Can include country codes: ["London,GB", "Paris,FR"]
            units: Unit system - "metric", "imperial", or "standard".
                  Default: "metric".
        
        Returns:
            List of weather dictionaries, one for each city.
            Returns partial results if some queries fail.
            Failed queries include an "error" field.
        
        Note:
            This method continues execution even if individual city queries fail,
            providing partial results for successful queries.
        """
        logger.info(f"Comparing weather for {len(cities)} cities")
        
        results = []
        
        for city in cities:
            try:
                weather_data = self.get_current_weather(city, units=units)
                results.append(weather_data)
                
            except ValueError as e:
                # City not found or API key error
                logger.warning(f"Failed to fetch weather for '{city}': {e}")
                results.append({
                    "city": city,
                    "country": "Unknown",
                    "error": str(e),
                    "temperature": None,
                    "feels_like": None,
                    "conditions": "Error",
                    "humidity": None,
                    "wind_speed": None,
                    "timestamp": None,
                    "units": units
                })
                
            except Exception as e:
                # Other errors
                logger.error(f"Unexpected error fetching weather for '{city}': {e}")
                results.append({
                    "city": city,
                    "country": "Unknown",
                    "error": f"Unexpected error: {str(e)}",
                    "temperature": None,
                    "feels_like": None,
                    "conditions": "Error",
                    "humidity": None,
                    "wind_speed": None,
                    "timestamp": None,
                    "units": units
                })
        
        logger.info(f"Weather comparison complete: {len(results)} results")
        return results
    
    def _make_request(self, endpoint: str, params: Dict) -> Dict:
        """
        Make a request to the OpenWeather API with error handling.
        
        Args:
            endpoint: API endpoint path (e.g., "/weather")
            params: Query parameters including API key
        
        Returns:
            JSON response as dictionary
        
        Raises:
            requests.exceptions.HTTPError: For HTTP errors (404, 401, 429, etc.)
            requests.exceptions.RequestException: For network errors
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        logger.debug(f"Making request to: {url}")
        logger.debug(f"Parameters: {params}")
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            
            # Handle rate limiting (429)
            if response.status_code == 429:
                self._handle_rate_limit(response)
            
            # Raise exception for HTTP errors
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
    
    def _handle_rate_limit(self, response: requests.Response) -> None:
        """
        Handle OpenWeather API rate limiting.
        
        OpenWeather free tier allows 60 calls/minute.
        
        Args:
            response: Response object from OpenWeather API
        
        Raises:
            requests.exceptions.HTTPError: If rate limit exceeded
        """
        logger.warning("Rate limit exceeded for OpenWeather API")
        
        # Try to wait a bit and retry (simple exponential backoff)
        wait_time = 60  # Wait 1 minute for rate limit reset
        
        logger.warning(f"Rate limit exceeded. Consider upgrading your API plan or waiting {wait_time} seconds")
        
        error_message = "OpenWeather API rate limit exceeded (60 calls/minute on free tier)"
        raise requests.exceptions.HTTPError(error_message, response=response)
    
    def _parse_weather_data(self, raw_data: Dict, units: str) -> Dict:
        """
        Parse raw OpenWeather API response into clean weather data.
        
        Args:
            raw_data: Raw JSON response from OpenWeather API
            units: Unit system used for the request
        
        Returns:
            Formatted weather dictionary with clean field names
        """
        # Extract main weather data
        main = raw_data.get("main", {})
        weather = raw_data.get("weather", [{}])[0]
        wind = raw_data.get("wind", {})
        sys = raw_data.get("sys", {})
        
        # Determine unit symbols
        temp_unit = "°C" if units == "metric" else ("°F" if units == "imperial" else "K")
        speed_unit = "m/s" if units == "metric" else ("mph" if units == "imperial" else "m/s")
        
        # Format weather data
        formatted = {
            "city": raw_data.get("name", "Unknown"),
            "country": sys.get("country", "Unknown"),
            "temperature": main.get("temp"),
            "temperature_unit": temp_unit,
            "feels_like": main.get("feels_like"),
            "conditions": weather.get("description", "").capitalize(),
            "conditions_main": weather.get("main", ""),
            "humidity": main.get("humidity"),
            "wind_speed": wind.get("speed"),
            "wind_speed_unit": speed_unit,
            "pressure": main.get("pressure"),
            "visibility": raw_data.get("visibility"),
            "cloudiness": raw_data.get("clouds", {}).get("all"),
            "timestamp": raw_data.get("dt"),
            "timezone": raw_data.get("timezone"),
            "units": units
        }
        
        return formatted
