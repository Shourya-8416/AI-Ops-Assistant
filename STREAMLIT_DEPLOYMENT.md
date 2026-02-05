# Deploy to Streamlit Cloud - Simple Guide

## Prerequisites
1. GitHub account
2. Your code pushed to a GitHub repository
3. API keys ready (Gemini, OpenWeather, GitHub)

## Step-by-Step Deployment

### 1. Push Code to GitHub
```bash
git init
git add .
git commit -m "AI Operations Assistant"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### 2. Go to Streamlit Cloud
Visit: https://share.streamlit.io/

### 3. Sign in with GitHub
Click "Sign in with GitHub"

### 4. Deploy New App
1. Click "New app"
2. Select your repository
3. Set main file path: `ai_ops_assistant/ui/app.py`
4. Click "Advanced settings"

### 5. Add Secrets (API Keys)
In the "Secrets" section, paste this (replace with your actual keys):

```toml
# LLM Provider
LLM_PROVIDER = "gemini"

# Gemini API Key
GEMINI_API_KEY = "your_gemini_api_key_here"
GEMINI_MODEL = "gemini-2.5-flash"

# OpenAI (optional)
OPENAI_API_KEY = "your_openai_key_here"
OPENAI_MODEL = "gpt-3.5-turbo"

# Required APIs
OPENWEATHER_API_KEY = "your_openweather_key_here"

# Optional
GITHUB_TOKEN = "your_github_token_here"
LOG_LEVEL = "INFO"
```

### 6. Deploy
Click "Deploy!" and wait 2-3 minutes

### 7. Done! 🎉
Your app will be live at: `https://YOUR_APP_NAME.streamlit.app`

## Updating Your App
Just push changes to GitHub - Streamlit auto-deploys!

```bash
git add .
git commit -m "Update"
git push
```

## Troubleshooting

**App won't start?**
- Check secrets are added correctly
- Verify API keys are valid
- Check logs in Streamlit Cloud dashboard

**API quota exceeded?**
- Gemini free tier: 20 requests/day
- Switch to OpenAI or wait for reset

**Need help?**
- Streamlit docs: https://docs.streamlit.io/streamlit-community-cloud
- Check app logs in dashboard

## That's It!
No Docker, no complex configs - just push and deploy! 🚀
