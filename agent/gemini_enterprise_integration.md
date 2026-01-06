# Gemini Enterprise Integration

This document captures information about integrating ADK agents with Gemini Enterprise for future reference.

## Overview

**Gemini Enterprise** (formerly "AgentSpace") is Google's enterprise chat interface that gives employees access to Gemini + custom ADK agents in one unified place.

## Pricing

| Tier | Cost |
|------|------|
| Enterprise | $30/user/month |
| Business | $21/user/month |
| **Free Trial** | 30 days |

## Prerequisites

Before registering an ADK agent with Gemini Enterprise:

1. **Discovery Engine Admin role** - Required IAM permission
2. **Discovery Engine API enabled** - Must be activated in your Google Cloud project
3. **Existing Gemini Enterprise app** - The agent will be registered within an app
4. **ADK agent hosted on Vertex AI Agent Engine** - Agents must be deployed to Agent Engine (not Cloud Run)

## How It Works

1. **Deploy to Agent Engine**: Use `make deploy` (deploys to Vertex AI Agent Engine)
2. **Enable Gemini Enterprise trial**: In GCP Console, enable the 30-day trial
3. **Register your agent**: Run `make register-gemini-enterprise`
4. **Users access**: Via `gemini.google.com/enterprise` with SSO authentication

## Registration Steps

### Via Google Cloud Console

1. Navigate to your Gemini Enterprise app
2. Select **Agents > Add Agents**
3. Choose **Custom agent via Agent Engine**
4. Optionally configure OAuth 2.0 authorization if the agent needs resource access
5. Enter the agent name, description, and Agent Engine reasoning engine resource path
6. Click **Create**

### Via CLI

```bash
make register-gemini-enterprise
```

This command is interactive and will prompt for required details. For non-interactive use, set environment variables:
- `ID` or `GEMINI_ENTERPRISE_APP_ID` (full GE resource name)
- `GEMINI_DISPLAY_NAME` (optional)
- `GEMINI_DESCRIPTION` (optional)
- `GEMINI_TOOL_DESCRIPTION` (optional)
- `AGENT_ENGINE_ID` (optional)

### Via REST API

Use a POST request to the Discovery Engine API endpoint with:
- Agent's display name
- Description
- Reasoning engine resource path in format:
  ```
  https://LOCATION-aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/reasoningEngines/ADK_RESOURCE_ID
  ```

## Benefits

- **Polished UI**: Production-ready chat interface
- **SSO built-in**: Integrates with Google Workspace identity
- **Unified access**: Users get Gemini + your custom agents in one place
- **No custom UI needed**: Google maintains the frontend

## Resources

- [Register ADK agents in Gemini Enterprise](https://docs.cloud.google.com/gemini/enterprise/docs/register-and-manage-an-adk-agent)
- [Gemini Enterprise Overview](https://cloud.google.com/gemini-enterprise)
- [ADK Training - Gemini Enterprise Tutorial](https://raphaelmansuy.github.io/adk_training/docs/google_agentspace/)
- [Gemini Enterprise Release Notes](https://docs.cloud.google.com/gemini/enterprise/docs/release-notes)

## Notes

- As of October 2025, Google Agentspace was rebranded to Gemini Enterprise
- Starting December 31, 2025, Google Agentspace is no longer available for new subscriptions
- Agent Engine pricing updates: billing for additional Agent Engine services starts January 28, 2026
