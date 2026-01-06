#!/bin/bash
# Setup script for Mozilla Data Docs ingestion infrastructure
# Creates GCS bucket and Vertex AI Search datastore with chunking enabled

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Mozilla Data Docs Infrastructure Setup ===${NC}"

# Get project ID
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: PROJECT_ID not set. Please set it via:${NC}"
    echo "  export PROJECT_ID=your-project-id"
    echo "  or: gcloud config set project your-project-id"
    exit 1
fi

echo -e "${GREEN}Using project: ${PROJECT_ID}${NC}"

# Configuration
GCS_BUCKET="${PROJECT_ID}-mozilla-data-docs"
DATA_STORE_ID="mozilla-data-docs-datastore"
DATA_STORE_REGION="us"
COLLECTION="default_collection"

# Step 1: Create GCS bucket
echo -e "\n${YELLOW}Step 1: Creating GCS bucket...${NC}"
if gsutil ls -b "gs://${GCS_BUCKET}" &>/dev/null; then
    echo -e "${GREEN}Bucket gs://${GCS_BUCKET} already exists${NC}"
else
    gsutil mb -l "${DATA_STORE_REGION}" "gs://${GCS_BUCKET}"
    echo -e "${GREEN}Created bucket gs://${GCS_BUCKET}${NC}"
fi

# Step 2: Enable required APIs
echo -e "\n${YELLOW}Step 2: Enabling required APIs...${NC}"
gcloud services enable discoveryengine.googleapis.com --project="${PROJECT_ID}"
gcloud services enable aiplatform.googleapis.com --project="${PROJECT_ID}"
echo -e "${GREEN}APIs enabled${NC}"

# Step 3: Create Vertex AI Search datastore with chunking
echo -e "\n${YELLOW}Step 3: Creating Vertex AI Search datastore with chunking enabled...${NC}"

# Check if datastore already exists
EXISTING_DATASTORE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $(gcloud auth print-access-token)" \
    -H "Content-Type: application/json" \
    "https://${DATA_STORE_REGION}-discoveryengine.googleapis.com/v1/projects/${PROJECT_ID}/locations/${DATA_STORE_REGION}/collections/${COLLECTION}/dataStores/${DATA_STORE_ID}")

if [ "$EXISTING_DATASTORE" = "200" ]; then
    echo -e "${GREEN}Datastore ${DATA_STORE_ID} already exists${NC}"
    echo -e "${YELLOW}Note: If you need to change chunking settings, you must delete and recreate the datastore${NC}"
else
    # Create datastore with layout-based chunking configuration
    # Using the Discovery Engine API
    echo "Creating datastore with layout-based chunking..."

    RESPONSE=$(curl -s -X POST \
        -H "Authorization: Bearer $(gcloud auth print-access-token)" \
        -H "Content-Type: application/json" \
        -H "X-Goog-User-Project: ${PROJECT_ID}" \
        "https://${DATA_STORE_REGION}-discoveryengine.googleapis.com/v1/projects/${PROJECT_ID}/locations/${DATA_STORE_REGION}/collections/${COLLECTION}/dataStores?dataStoreId=${DATA_STORE_ID}" \
        -d '{
            "displayName": "Mozilla Data Docs",
            "industryVertical": "GENERIC",
            "solutionTypes": ["SOLUTION_TYPE_SEARCH"],
            "contentConfig": "CONTENT_REQUIRED",
            "documentProcessingConfig": {
                "chunkingConfig": {
                    "layoutBasedChunkingConfig": {
                        "chunkSize": 500,
                        "includeAncestorHeadings": true
                    }
                },
                "defaultParsingConfig": {
                    "layoutParsingConfig": {}
                }
            }
        }')

    # Check if creation was successful
    if echo "$RESPONSE" | grep -q "error"; then
        echo -e "${RED}Error creating datastore:${NC}"
        echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
        exit 1
    else
        echo -e "${GREEN}Datastore creation initiated${NC}"
        echo "Response: $RESPONSE"
    fi

    # Wait for datastore to be ready
    echo "Waiting for datastore to be ready..."
    sleep 10

    # Verify datastore was created
    VERIFY=$(curl -s \
        -H "Authorization: Bearer $(gcloud auth print-access-token)" \
        -H "Content-Type: application/json" \
        "https://${DATA_STORE_REGION}-discoveryengine.googleapis.com/v1/projects/${PROJECT_ID}/locations/${DATA_STORE_REGION}/collections/${COLLECTION}/dataStores/${DATA_STORE_ID}")

    if echo "$VERIFY" | grep -q "\"name\""; then
        echo -e "${GREEN}Datastore ${DATA_STORE_ID} created successfully${NC}"
    else
        echo -e "${YELLOW}Datastore creation may still be in progress. Check the console.${NC}"
    fi
fi

# Step 4: Create a Search App (Engine) linked to the datastore
echo -e "\n${YELLOW}Step 4: Creating Search App (Engine)...${NC}"

ENGINE_ID="${DATA_STORE_ID}-app"

EXISTING_ENGINE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $(gcloud auth print-access-token)" \
    -H "Content-Type: application/json" \
    "https://${DATA_STORE_REGION}-discoveryengine.googleapis.com/v1/projects/${PROJECT_ID}/locations/${DATA_STORE_REGION}/collections/${COLLECTION}/engines/${ENGINE_ID}")

if [ "$EXISTING_ENGINE" = "200" ]; then
    echo -e "${GREEN}Search App ${ENGINE_ID} already exists${NC}"
else
    ENGINE_RESPONSE=$(curl -s -X POST \
        -H "Authorization: Bearer $(gcloud auth print-access-token)" \
        -H "Content-Type: application/json" \
        -H "X-Goog-User-Project: ${PROJECT_ID}" \
        "https://${DATA_STORE_REGION}-discoveryengine.googleapis.com/v1/projects/${PROJECT_ID}/locations/${DATA_STORE_REGION}/collections/${COLLECTION}/engines?engineId=${ENGINE_ID}" \
        -d "{
            \"displayName\": \"Mozilla Data Docs Search\",
            \"solutionType\": \"SOLUTION_TYPE_SEARCH\",
            \"searchEngineConfig\": {
                \"searchTier\": \"SEARCH_TIER_ENTERPRISE\",
                \"searchAddOns\": [\"SEARCH_ADD_ON_LLM\"]
            },
            \"dataStoreIds\": [\"${DATA_STORE_ID}\"]
        }")

    if echo "$ENGINE_RESPONSE" | grep -q "error"; then
        echo -e "${YELLOW}Warning: Could not create Search App (may already exist or require manual setup)${NC}"
        echo "$ENGINE_RESPONSE"
    else
        echo -e "${GREEN}Search App creation initiated${NC}"
    fi
fi

echo -e "\n${GREEN}=== Setup Complete ===${NC}"
echo ""
echo "Infrastructure created:"
echo "  - GCS Bucket: gs://${GCS_BUCKET}"
echo "  - Datastore ID: ${DATA_STORE_ID}"
echo "  - Datastore Region: ${DATA_STORE_REGION}"
echo ""
echo "Next steps:"
echo "  1. Run the data ingestion pipeline:"
echo "     make data-ingestion"
echo ""
echo "  2. After ingestion completes, test the agent:"
echo "     make playground"
echo ""
echo -e "${YELLOW}Note: The datastore uses layout-based chunking (500 tokens, with ancestor headings).${NC}"
echo -e "${YELLOW}This setting cannot be changed after creation.${NC}"
