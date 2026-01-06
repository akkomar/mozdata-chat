# Quick Deployment Guide (Combined Container)

This guide covers deploying the Mozdata Assistant using a **single container** that runs both Next.js and Python.

> **Note:** This guide uses `mozdata-chat` as an example project name. Replace it with your own project name throughout.

## Architecture

```
[Firebase Hosting: mozdata-chat.web.app]
    ↓ (proxies all requests)
[Single Cloud Run Service: mozdata-chat]
    ├── Next.js frontend (port 8080) ← User-facing
    │   └── /api/copilotkit route
    │           ↓ (internal proxy to localhost:8000)
    └── Python backend (port 8000) ← Internal only
            ↓ (calls)
        [Vertex AI Agent Engine in agent-engine-project]
```

**Key points:**
- One Docker container runs both services using supervisord
- Next.js serves the UI and `/api/copilotkit` route on port 8080
- Python backend runs internally on port 8000
- Firebase Hosting provides the nice domain and CDN
- Identity Platform blocks non-Mozilla users at sign-in

---

## Prerequisites

1. **Create GCP project:**
   ```bash
   gcloud projects create mozdata-chat
   gcloud config set project mozdata-chat

   # Enable billing (required)
   gcloud billing projects link mozdata-chat --billing-account=YOUR_BILLING_ACCOUNT
   ```

2. **Add Firebase to the project:**
   ```bash
   firebase projects:addfirebase mozdata-chat
   ```

   Or manually in Firebase Console: https://console.firebase.google.com/

3. **Install Firebase CLI:**
   ```bash
   npm install -g firebase-tools
   firebase login
   ```

---

## Step 1: Configure Firebase

### 1a. Get Firebase Configuration

1. Go to https://console.firebase.google.com/project/mozdata-chat/settings/general
2. Scroll to "Your apps" → Click web app icon `</>`
3. Copy the `firebaseConfig` values

### 1b. Update Firebase Config

Create `.env.local` file:
```bash
NEXT_PUBLIC_FIREBASE_API_KEY=AIza...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=mozdata-chat.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=mozdata-chat
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=mozdata-chat.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=123...
NEXT_PUBLIC_FIREBASE_APP_ID=1:123...
```

Or update `src/lib/firebase.ts` directly (lines 22-27).

---

## Step 2: Enable Google Sign-In in Firebase Console

1. Go to https://console.firebase.google.com/project/mozdata-chat/authentication/providers
2. Click on "Google" provider
3. Click "Enable"
4. Configure:
   - **Project support email**: Your @mozilla.com email
   - **Project public-facing name**: "Mozdata Assistant"
5. Click "Save"

That's it! Firebase will auto-create OAuth credentials for you.

---

## Step 3: Build and Deploy with Terraform

Terraform will automatically:
- ✅ Deploy blocking functions (beforeSignIn, beforeCreate)
- ✅ Register them with Identity Platform
- ✅ Configure Identity Platform with blocking triggers
- ✅ Create Cloud Run service
- ✅ Set up all IAM permissions

### 3a. Initialize Terraform

```bash
cd tf
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars if needed (defaults should work)
terraform init
```

### 3b. Build Container Image Locally

```bash
# From project root
cd ..

# Install dependencies first (makes build faster)
pnpm install

# Build the combined container (just builds locally, doesn't push)
docker build --platform linux/amd64 -t us-central1-docker.pkg.dev/mozdata-chat/mozdata-chat/app:latest \
  -f Dockerfile.combined .

# Authenticate Docker with GCP for later push
gcloud auth configure-docker us-central1-docker.pkg.dev
```

### 3c. Apply Terraform (First Run)

```bash
cd tf

# Preview changes
terraform plan

# Apply - this creates Artifact Registry and other infrastructure
# Cloud Run will fail to deploy because image doesn't exist yet - that's expected!
terraform apply
```

### 3d. Push Image and Deploy

```bash
# Now that Artifact Registry exists, push the image
cd ..
docker push us-central1-docker.pkg.dev/mozdata-chat/mozdata-chat/app:latest

# Apply Terraform again - now Cloud Run deploys successfully
cd tf
terraform apply
```

**What Terraform creates:**
- ✅ Artifact Registry repository for containers
- ✅ Cloud Run service (Next.js + Python)
- ✅ Service account with Vertex AI access
- ✅ Cross-project IAM binding to Agent Engine
- ✅ Identity Platform configuration

---

## Step 4: Deploy to Firebase Hosting

```bash
# From project root
firebase init hosting

# Select options:
# - Use existing project: mozdata-chat
# - Public directory: out (won't be used, but required)
# - Configure as single-page app: No
# - Set up automatic builds with GitHub: No

# Deploy
firebase deploy --only hosting --project=mozdata-chat
```

**Firebase Hosting config is already set** in `firebase.json` to proxy all requests to Cloud Run.

---

## Step 5: Test the Deployment

1. **Get your URL:**
   ```bash
   # Firebase Hosting URL (recommended):
   echo "https://mozdata-chat.web.app"

   # Or Cloud Run URL:
   gcloud run services describe mozdata-chat \
     --region=us-central1 \
     --format='value(status.url)'
   ```

2. **Visit the URL and test:**
   - Try signing in with @mozilla.com account ✅
   - Try signing in with non-Mozilla account ❌ (should be blocked)
   - Ask the chat a question about Mozilla data

---

## Updating the Application

### Update Code

```bash
# Rebuild container
docker build --platform linux/amd64 -t us-central1-docker.pkg.dev/mozdata-chat/mozdata-chat/app:latest \
  -f Dockerfile.combined .

# Push new version
docker push us-central1-docker.pkg.dev/mozdata-chat/mozdata-chat/app:latest

# Deploy new version (forces Cloud Run to pull latest image)
gcloud run services update mozdata-chat \
  --image us-central1-docker.pkg.dev/mozdata-chat/mozdata-chat/app:latest \
  --region=us-central1 \
  --project=mozdata-chat
```

### Update Blocking Functions

```bash
# Blocking functions are managed by Terraform
# Just re-run terraform apply after modifying functions/index.js
cd tf
terraform apply
cd ..
```

---

## Implementation Notes

### Blocking Functions Architecture

**Important:** Identity Platform blocking functions require **Gen1 Cloud Functions**, not Gen2. The Terraform configuration automatically deploys them as Gen1.

- Functions use `ingress_settings = "ALLOW_ALL"` and `member = "allUsers"` IAM binding
- Security is provided by the `gcip-cloud-functions` library which validates Identity Platform tokens
- Only Identity Platform can invoke them with valid token signatures

### Authentication Token Flow

1. User signs in with Google → Identity Platform validates @mozilla.com domain
2. Blocking functions (beforeSignIn/beforeCreate) enforce email restriction
3. Frontend receives Firebase ID token
4. Token passed via custom `x-firebase-token` header (avoids conflicts with HttpAgent)
5. Python backend verifies token with `firebase-admin` SDK
6. Backend validates @mozilla.com domain again (defense in depth)

### Timeout Configuration

Long-running Agent Engine queries with multiple tool calls are supported:
- **Cloud Run timeout**: 600 seconds (10 minutes)
- **Next.js API route**: 300 seconds (5 minutes via `maxDuration`)
- **SSE heartbeat**: Sends keepalive every 10 seconds of inactivity

---

## Troubleshooting

### Container fails to start

Check logs:
```bash
gcloud run services logs read mozdata-chat --region=us-central1 --project=mozdata-chat
```

Common issues:
- Missing environment variables (check Terraform outputs)
- Python dependencies not installed (check Dockerfile)
- Next.js build failed (check build logs)

### Blocking functions not working

```bash
# Check function logs (Gen1 functions - no --gen2 flag)
gcloud functions logs read beforeSignIn --region=us-central1 --project=mozdata-chat

# Verify functions are deployed
gcloud functions list --region=us-central1 --project=mozdata-chat

# Check Terraform state
cd tf
terraform show | grep google_cloudfunctions_function

# Verify functions are registered in Identity Platform
# Go to Console → Identity Platform → Settings → Triggers
# Should see beforeSignIn and beforeCreate with function URIs
# If functions don't appear in the dropdowns, they might be Gen2 (not supported)
```

### Can sign in but chat doesn't work

Check backend logs:
```bash
gcloud run services logs read mozdata-chat --region=us-central1 --project=mozdata-chat | grep python-backend
```

Verify token verification:
- Check Firebase config in `src/lib/firebase.ts`
- Verify auth token is being sent (check browser Network tab)
- Check backend receives Authorization header

### CORS errors

CORS is configured in `proxy/main.py` to allow all origins. If you see CORS errors:
- Verify the backend is running (check supervisor logs)
- Check browser console for specific error
- Verify requests include Authorization header

---

## Cost Estimates

**Estimated monthly cost for low-traffic PoC:**

| Service | Cost |
|---------|------|
| Cloud Run (1 service) | $0-5/month (generous free tier, scales to zero) |
| Cloud Functions (2 functions) | $0-1/month (only run during sign-in) |
| Artifact Registry | $0.10/month (storage) |
| Firebase Hosting | $0/month (free tier: 10GB transfer/month) |
| Identity Platform | $0/month (free tier: 50 DAU) |
| **Total** | **~$1-6/month** |

*Costs increase with traffic. Vertex AI Agent Engine costs are in the agent project (see `../agent/`).*

---

## Architecture Notes

### Why Combined Container?

**Pros:**
- ✅ Simple deployment (one service)
- ✅ Single Cloud Run service to manage
- ✅ Fewer moving parts
- ✅ Perfect for PoC/small projects

**Cons:**
- ❌ Can't scale frontend and backend independently
- ❌ Slightly larger container image
- ❌ More memory needed (both services running)

For production at scale, you'd want separate services. For a PoC, this is perfect!

### Security Model

**Defense in depth:**

1. **Identity Platform blocking functions** (primary defense)
   - Non-Mozilla users blocked at sign-in
   - Never receive authentication token

2. **Backend token verification** (secondary defense)
   - Every request validates Firebase ID token
   - Checks `@mozilla.com` email domain
   - Protects against bypassed/misconfigured blocking functions

3. **Cross-project IAM**
   - Cloud Run service account has minimal permissions
   - Only `aiplatform.user` on Agent Engine project
   - No broader GCP access

### Why Firebase Hosting?

- Nice domain: `mozdata-chat.web.app` (vs `mozdata-chat-xyz.a.run.app`)
- Free SSL certificate
- Global CDN (faster loading)
- Simple configuration

You could skip Firebase Hosting and just use the Cloud Run URL directly if you prefer.

---

## Next Steps

- [ ] Add custom domain (if desired): Firebase Hosting → Add custom domain
- [ ] Set up monitoring: Cloud Console → Cloud Run → mozdata-chat → Metrics
- [ ] Configure alerts: Set up uptime checks and error rate alerts
- [ ] Add more @mozilla.com users: They can sign in immediately, no config needed
- [ ] Update Agent Engine: Make changes in the agent project (`../agent/`), no UI redeployment needed


### Disable
  To disable (minimal public exposure):

1. Delete Cloud Run instances:
gcloud run services delete mozdata-chat --region=us-central1 --project=mozdata-chat
2. Remove Cloud Functions public access:
gcloud functions remove-iam-policy-binding beforeSignIn --member="allUsers" --role="roles/cloudfunctions.invoker" --region=us-central1 --project=mozdata-chat

gcloud functions remove-iam-policy-binding beforeCreate --member="allUsers" --role="roles/cloudfunctions.invoker" --region=us-central1 --project=mozdata-chat

To restore:
```
cd tf
terraform apply
```