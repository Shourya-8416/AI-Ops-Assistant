"""
Streamlit web interface for AI Operations Assistant.
Simple, clean chatbot interface.
"""

import streamlit as st
import json
from typing import Dict, Any, List
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from main import AIOperationsAssistant


# Page configuration
st.set_page_config(
    page_title="AI Operations Assistant",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Custom CSS - Dark Theme
st.markdown("""
<style>
    /* Main app background - Dark */
    .stApp {
        background-color: #1e1e1e !important;
    }
    
    /* Main content area - Dark */
    .main {
        background-color: #1e1e1e !important;
    }
    
    /* Sidebar - Darker */
    [data-testid="stSidebar"] {
        background-color: #2d2d2d !important;
    }
    
    /* Sidebar text color */
    [data-testid="stSidebar"] * {
        color: #e0e0e0 !important;
    }
    
    /* Chat messages - Dark cards */
    .stChatMessage {
        background-color: #2d2d2d !important;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        color: #e0e0e0 !important;
    }
    
    /* User message - Slightly different shade */
    .stChatMessage[data-testid="user-message"] {
        background-color: #3d3d3d !important;
    }
    
    /* Text color for all elements */
    .main * {
        color: #e0e0e0 !important;
    }
    
    /* Input box - Dark */
    .stChatInputContainer {
        background-color: #2d2d2d !important;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #ffffff !important;
    }
    
    /* Links */
    a {
        color: #4da6ff !important;
    }
    
    /* Buttons */
    .stButton button {
        background-color: #3d3d3d !important;
        color: #e0e0e0 !important;
        border: 1px solid #4d4d4d !important;
    }
    
    .stButton button:hover {
        background-color: #4d4d4d !important;
        border-color: #5d5d5d !important;
    }
</style>
""", unsafe_allow_html=True)


def format_weather_response(data: Dict) -> str:
    """Format weather data as clean text."""
    if isinstance(data, list):
        response = ""
        for weather in data:
            city = weather.get('city', 'Unknown')
            temp = weather.get('temperature', 'N/A')
            feels = weather.get('feels_like', 'N/A')
            conditions = weather.get('conditions', 'N/A')
            humidity = weather.get('humidity', 'N/A')
            
            response += f"""
**{city}**
- 🌡️ Temperature: {temp}°C
- 🤔 Feels like: {feels}°C
- ☁️ Conditions: {conditions}
- 💧 Humidity: {humidity}%

"""
        return response
    else:
        city = data.get('city', 'Unknown')
        temp = data.get('temperature', 'N/A')
        feels = data.get('feels_like', 'N/A')
        conditions = data.get('conditions', 'N/A')
        humidity = data.get('humidity', 'N/A')
        wind = data.get('wind_speed', 'N/A')
        
        return f"""
**Weather in {city}**

🌡️ **Temperature:** {temp}°C  
🤔 **Feels like:** {feels}°C  
☁️ **Conditions:** {conditions}  
💧 **Humidity:** {humidity}%  
💨 **Wind Speed:** {wind} m/s
"""


def format_github_response(data: Any) -> str:
    """Format GitHub data as clean text."""
    if isinstance(data, list):
        response = "**Top Repositories:**\n\n"
        for idx, repo in enumerate(data[:5], 1):
            name = repo.get('full_name', 'Unknown')
            desc = repo.get('description', 'No description')
            stars = repo.get('stars', 0)
            language = repo.get('language', 'N/A')
            url = repo.get('url', '#')
            
            response += f"""
**{idx}. {name}**  
⭐ {stars:,} stars | 💻 {language}  
{desc}  
[View on GitHub]({url})

"""
        return response
    else:
        name = data.get('full_name', 'Unknown')
        desc = data.get('description', 'No description')
        stars = data.get('stars', 0)
        forks = data.get('forks', 0)
        language = data.get('language', 'N/A')
        url = data.get('url', '#')
        
        return f"""
**{name}**

{desc}

⭐ **Stars:** {stars:,}  
🍴 **Forks:** {forks:,}  
💻 **Language:** {language}  

[View on GitHub]({url})
"""


def format_wikipedia_response(data: Dict) -> str:
    """Format Wikipedia data as clean text."""
    if isinstance(data, list):
        response = ""
        for article in data:
            title = article.get('title', 'Unknown')
            extract = article.get('extract', 'No summary available')
            url = article.get('url', '#')
            
            response += f"""
**{title}**

{extract}

[Read more on Wikipedia]({url})

---

"""
        return response
    else:
        title = data.get('title', 'Unknown')
        extract = data.get('extract', 'No summary available')
        url = data.get('url', '#')
        
        return f"""
**{title}**

{extract}

[Read more on Wikipedia]({url})
"""


def extract_clean_response(result: Dict[str, Any]) -> str:
    """Extract and format clean response from result."""
    # Handle errors with user-friendly messages
    if result.get("error"):
        error_msg = result["error"]
        
        # Provide helpful error messages based on error type
        if "planning failed" in error_msg.lower():
            if "validation" in error_msg.lower():
                return """❌ **I couldn't understand your request properly.**

**Possible reasons:**
- The query might be too complex or unclear
- Try breaking it into simpler parts

**Suggestions:**
- Use simple, clear language
- Ask one thing at a time, or combine 2-3 related requests
- Examples:
  - ✅ "What's the weather in London?"
  - ✅ "Tell me about Python and find Python repos"
  - ❌ Very long or confusing queries

**Please try again with a clearer question!**"""
            else:
                return f"""❌ **Planning Error**

I encountered an issue while planning your request:
{error_msg}

**Please try:**
- Simplifying your query
- Asking one question at a time
- Using clear, specific language"""
        
        elif "api key" in error_msg.lower() or "authentication" in error_msg.lower():
            return """❌ **Configuration Error**

There's an issue with the API keys. Please check:
- Gemini API key is set correctly
- OpenWeather API key is valid
- GitHub token (optional) is configured

Contact the administrator to fix the configuration."""
        
        elif "rate limit" in error_msg.lower() or "quota" in error_msg.lower():
            return """❌ **API Limit Reached**

The free API quota has been exceeded.

**What you can do:**
- Wait for the quota to reset (usually 24 hours for Gemini)
- Try again later
- Contact administrator to upgrade the API plan

**Current limits:**
- Gemini: 20 requests per day (free tier)
- OpenWeather: 60 requests per minute"""
        
        elif "network" in error_msg.lower() or "connection" in error_msg.lower():
            return """❌ **Network Error**

I couldn't connect to the required services.

**Please check:**
- Your internet connection
- The service might be temporarily down
- Try again in a few moments"""
        
        elif "execution failed" in error_msg.lower():
            return f"""❌ **Execution Error**

I couldn't complete your request:
{error_msg}

**This might be because:**
- The requested data wasn't found
- An API service is unavailable
- The query parameters were invalid

**Please try:**
- Checking your query for typos
- Using different search terms
- Trying a simpler query"""
        
        else:
            return f"""❌ **Something went wrong**

{error_msg}

**Please try:**
- Refreshing the page
- Simplifying your query
- Trying again in a moment

If the problem persists, contact support."""
    
    execution = result.get("execution", {})
    if not execution.get("success"):
        return """❌ **Request Failed**

I couldn't complete your request successfully.

**Common reasons:**
- The requested information wasn't found
- An API service is temporarily unavailable
- The query was too complex

**Please try:**
- Simplifying your query
- Checking for typos in city names, repository names, etc.
- Trying a different query

**Need help?** Try the example queries in the sidebar!"""
    
    results = execution.get("results", [])
    if not results:
        return """❌ **No Results Found**

I processed your request but didn't find any data.

**This might mean:**
- The search didn't match anything
- The requested information doesn't exist
- Try different search terms

**Suggestions:**
- Check spelling of city names, topics, etc.
- Try broader search terms
- Use the example queries for guidance"""
    
    # Build clean response
    response_parts = []
    
    for step_result in results:
        if step_result.get("status") != "success":
            continue
        
        data = step_result.get("data")
        if not data:
            continue
        
        # Detect data type and format accordingly
        if isinstance(data, dict):
            if "temperature" in data or "city" in data:
                response_parts.append(format_weather_response(data))
            elif "stars" in data or "forks" in data:
                response_parts.append(format_github_response(data))
            elif "title" in data and "extract" in data:
                response_parts.append(format_wikipedia_response(data))
            else:
                response_parts.append(json.dumps(data, indent=2))
        
        elif isinstance(data, list):
            if not data:
                continue
            
            first_item = data[0] if data else {}
            
            if isinstance(first_item, dict):
                if "temperature" in first_item or "city" in first_item:
                    response_parts.append(format_weather_response(data))
                elif "stars" in first_item or "forks" in first_item:
                    response_parts.append(format_github_response(data))
                elif "title" in first_item and "extract" in first_item:
                    response_parts.append(format_wikipedia_response(data))
                else:
                    for item in data[:5]:
                        response_parts.append(str(item))
        else:
            response_parts.append(str(data))
    
    if not response_parts:
        return "✅ Task completed successfully, but no data to display."
    
    return "\n\n".join(response_parts)


def initialize_session_state():
    """Initialize session state."""
    if "assistant" not in st.session_state:
        st.session_state.assistant = None
    
    if "messages" not in st.session_state:
        st.session_state.messages = []


def main():
    """Main application."""
    initialize_session_state()
    
    # Header
    st.title("🤖 AI Assistant")
    st.caption("Ask me about weather, GitHub repositories, or Wikipedia topics")
    
    # Display chat history
    for message in st.session_state.messages:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.markdown(message["content"])
        else:
            with st.chat_message("assistant"):
                st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask me anything..."):
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Add to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Process query
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Initialize assistant if needed
                    if st.session_state.assistant is None:
                        st.session_state.assistant = AIOperationsAssistant()
                    
                    # Get response
                    result = st.session_state.assistant.process_query(prompt)
                    
                    # Extract clean response
                    response = extract_clean_response(result)
                    
                    # Display response
                    st.markdown(response)
                    
                    # Add to history
                    st.session_state.messages.append({"role": "assistant", "content": response})
                
                except Exception as e:
                    error_msg = f"❌ Sorry, I encountered an error: {str(e)}"
                    st.markdown(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
    
    # Sidebar with simple examples
    with st.sidebar:
        st.header("📚 Integrated Tools")
        st.markdown("""
        **🌤️ Weather API**  
        Get current weather for any city
        
        **🐙 GitHub API**  
        Search repositories and projects
        
        **📖 Wikipedia API**  
        Get summaries and information
        """)
        
        st.divider()
        
        st.header("💡 Example Queries")
        
        st.markdown("**Weather:**")
        st.markdown("• What's the weather in Tokyo?")
        st.markdown("• Compare weather in London and Paris")
        
        st.markdown("**GitHub:**")
        st.markdown("• Find popular Python repositories")
        st.markdown("• Search for machine learning projects")
        
        st.markdown("**Wikipedia:**")
        st.markdown("• Tell me about Python programming")
        st.markdown("• What is artificial intelligence?")
        
        st.markdown("**Combined:**")
        st.markdown("• Tell me about Python and find Python repos")
        st.markdown("• What's the weather in Paris and tell me about the Eiffel Tower")
        
        st.divider()
        
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()


if __name__ == "__main__":
    main()
