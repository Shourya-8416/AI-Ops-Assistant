# Streamlit Web UI

This directory contains the Streamlit web interface for the AI Operations Assistant.

## Running the UI

```bash
streamlit run ai_ops_assistant/ui/app.py
```

## Features

- **Interactive Query Input**: Text area with example queries
- **Real-time Processing**: Loading indicators during execution
- **Expandable Sections**: Plan, execution logs, and verification details
- **Comparison Views**: Side-by-side comparison tables for multiple entities
- **Error Handling**: Clear error messages with helpful suggestions
- **Session State**: Maintains assistant instance across queries

## UI Components

### Header
- Application title and description
- Capability overview

### Input Section
- Text area for query input
- Example query buttons
- Expandable examples section

### Results Display
- Overall status and timing
- Execution plan (JSON)
- Execution results with step details
- Verification summary
- Formatted output
- Comparison tables (when applicable)

### Error Panel
- Error messages
- Contextual help based on error type
- Configuration guidance

## Customization

The UI can be customized by modifying:
- Page configuration in `st.set_page_config()`
- CSS styling in markdown sections
- Layout columns and containers
- Color schemes and icons
