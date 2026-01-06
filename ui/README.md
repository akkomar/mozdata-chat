# Mozdata Assistant

A [CopilotKit](https://copilotkit.ai) chat interface that connects to the Mozilla Data Docs RAG agent deployed on [Vertex AI Agent Engine](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview).

Secured with **Firebase Authentication** restricted to **@mozilla.com accounts only**.

Ask questions about:
- Mozilla telemetry and data collection
- BigQuery datasets and tables
- Glean SDK and metrics
- Looker dashboards and explores
- Data pipelines and ETL processes

**Live deployment:** Configure your own Firebase Hosting URL (requires @mozilla.com account)

## Prerequisites

- Node.js 18+
- Python 3.10+
- Google Cloud authentication (`gcloud auth application-default login`)
- Access to the Vertex AI Agent Engine resource
- Package manager: pnpm, npm, yarn, or bun

## Getting Started

1. **Authenticate with Google Cloud:**
```bash
gcloud auth application-default login
```

2. **Install dependencies:**
```bash
pnpm install
```

3. **Start the development servers:**
```bash
pnpm dev
```

This starts both the Next.js UI (port 3000) and the Python proxy server (port 8000).

4. **Open http://localhost:3000** and start asking questions!

## Architecture

### Local Development
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Browser        │────▶│  Next.js API     │────▶│  Python Proxy       │
│  (CopilotKit)   │     │  /api/copilotkit │     │  localhost:8000     │
└─────────────────┘     └──────────────────┘     └──────────┬──────────┘
                                                            │
                                                            ▼
                                                ┌─────────────────────┐
                                                │  Vertex AI Agent    │
                                                │  Engine (deployed)  │
                                                └─────────────────────┘
```

### Production Deployment (Combined Container)
```
[Browser] → [Firebase Hosting: mozdata-chat.web.app]
                    ↓
            [Cloud Run: mozdata-chat]
            ├── Next.js (port 8080)
            │   ├── UI + Firebase Auth
            │   └── /api/copilotkit route
            │           ↓ (localhost proxy)
            └── Python FastAPI (port 8000)
                    ├── Session mapping ←→ [Firestore]
                    └── Agent queries → [Vertex AI Agent Engine]
```

**Components:**
- **Frontend**: Next.js with CopilotKit + Firebase Auth
- **Backend**: Python FastAPI proxy with token verification
- **Sessions**: Firestore stores thread→session mapping for multi-turn conversations
- **Security**: Identity Platform blocking functions + backend verification
- **Hosting**: Firebase Hosting → Cloud Run single container
- **Process Manager**: supervisord runs both Next.js and Python

## Available Scripts

| Script | Description |
|--------|-------------|
| `pnpm dev` | Start both UI and proxy servers |
| `pnpm dev:ui` | Start only the Next.js UI |
| `pnpm dev:proxy` | Start only the Python proxy |
| `pnpm build` | Build for production |
| `pnpm lint` | Run ESLint |

## Configuration

### Local Development

Create `.env` for Firebase configuration:
```bash
NEXT_PUBLIC_FIREBASE_API_KEY=your-firebase-api-key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-firebase-project
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=your-sender-id
NEXT_PUBLIC_FIREBASE_APP_ID=your-app-id
```

**Note:** The `.env` file is used both locally and in the Docker build (baked into the container at build time).

Agent Engine configuration in `proxy/.env` (copy from `proxy/.env.example`):
```bash
FIREBASE_PROJECT_ID=your-firebase-project
GOOGLE_CLOUD_PROJECT=your-gcp-project-number
VERTEX_LOCATION=us-central1
AGENT_ENGINE_RESOURCE_ID=your-agent-engine-resource-id
```

## Production Deployment

See **[DEPLOY.md](./DEPLOY.md)** for complete deployment instructions.

**Quick overview:**
1. Create `mozdata-chat` GCP project + Firebase
2. Deploy blocking functions to Identity Platform
3. Build combined container with Terraform
4. Deploy to Firebase Hosting

**Estimated cost:** ~$1-6/month for low-traffic PoC

## Project Structure

```
├── src/
│   ├── app/
│   │   ├── page.tsx                  # Main chat UI with auth gate
│   │   ├── layout.tsx                # Auth & CopilotKit providers
│   │   └── api/copilotkit/           # Protocol translation route
│   ├── components/
│   │   ├── AuthProvider.tsx          # Firebase Auth context
│   │   └── CopilotKitProvider.tsx    # Chat runtime with auth
│   └── lib/
│       ├── types.ts                  # TypeScript types
│       └── firebase.ts               # Firebase config
├── proxy/
│   ├── main.py                       # Python proxy + token verification
│   └── pyproject.toml                # Python dependencies
├── functions/
│   ├── index.js                      # Identity Platform blocking functions
│   └── package.json
├── tf/                                # Terraform infrastructure
│   ├── main.tf                       # Cloud Run, functions, IAM
│   └── variables.tf
├── Dockerfile.combined                # Combined Next.js + Python image
├── supervisord.conf                   # Process manager config
├── firebase.json                      # Firebase Hosting config
└── DEPLOY.md                          # Deployment guide
```

## Documentation

- [Vertex AI Agent Engine](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview)
- [CopilotKit Documentation](https://docs.copilotkit.ai)
- [AG-UI Protocol](https://docs.ag-ui.com)
- [Mozilla Data Documentation](https://docs.telemetry.mozilla.org)

## Troubleshooting

### Authentication Errors
If you see authentication errors, ensure you've run:
```bash
gcloud auth application-default login
```

### Agent Connection Issues
If the chat shows connection errors:
1. Check that the proxy server is running on port 8000
2. Verify you have access to the Agent Engine resource
3. Check the proxy server logs for detailed error messages

### Python Dependencies
If you encounter Python import errors:
```bash
cd proxy
uv sync
```
