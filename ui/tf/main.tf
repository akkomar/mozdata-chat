data "google_project" "current" {
  project_id = var.project_id
}

# Grant Compute Engine default service account permissions to build functions
# Gen2 Cloud Functions use the Compute Engine default SA for builds
resource "google_project_iam_member" "compute_logs" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"

  depends_on = [google_project_service.apis]
}

resource "google_project_iam_member" "compute_artifactregistry" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"

  depends_on = [google_project_service.apis]
}

resource "google_project_iam_member" "compute_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"

  depends_on = [google_project_service.apis]
}

# Enable required GCP APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudfunctions.googleapis.com",
    "identitytoolkit.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

# Artifact Registry for container images
resource "google_artifact_registry_repository" "repo" {
  project       = var.project_id
  location      = var.region
  repository_id = "mozdata-chat"
  description   = "Container registry for mozdata-chat backend"
  format        = "DOCKER"

  depends_on = [google_project_service.apis]
}

# Service Account for Cloud Run service
resource "google_service_account" "app" {
  project      = var.project_id
  account_id   = "mozdata-chat-app"
  display_name = "Cloud Run Service Account"
  description  = "Service account for mozdata-chat Cloud Run service"

  depends_on = [google_project_service.apis]
}

# Cross-project IAM: Allow app to call Vertex AI Agent Engine
resource "google_project_iam_member" "vertex_ai_access" {
  project = var.agent_engine_project
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.app.email}"
}

# Cloud Run service for combined Next.js + Python app
resource "google_cloud_run_v2_service" "app" {
  project             = var.project_id
  name                = var.service_name
  location            = var.region
  deletion_protection = false # Set to true for production

  template {
    service_account = google_service_account.app.email
    timeout         = "600s" # 10 minutes for long-running agent queries

    containers {
      image = var.container_image

      env {
        name  = "FIREBASE_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.agent_engine_project_number
      }
      env {
        name  = "VERTEX_LOCATION"
        value = var.region
      }
      env {
        name  = "AGENT_ENGINE_RESOURCE_ID"
        value = var.agent_engine_resource_id
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "1Gi"
        }
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }
  }

  depends_on = [
    google_project_service.apis,
    google_artifact_registry_repository.repo,
  ]
}

# Allow unauthenticated access to Cloud Run (app handles auth via Firebase tokens)
resource "google_cloud_run_v2_service_iam_member" "public" {
  project  = var.project_id
  name     = google_cloud_run_v2_service.app.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Storage bucket for Cloud Functions source code
resource "google_storage_bucket" "functions_source" {
  project                     = var.project_id
  name                        = "${var.project_id}-functions-source"
  location                    = "US"
  uniform_bucket_level_access = true
  force_destroy               = true

  depends_on = [google_project_service.apis]
}

# Create zip archive of functions source code
data "archive_file" "functions_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../functions"
  output_path = "${path.module}/functions-source.zip"
  excludes    = ["node_modules"]
}

# Upload functions source to GCS
resource "google_storage_bucket_object" "functions_zip" {
  name   = "functions-source-${data.archive_file.functions_zip.output_md5}.zip"
  bucket = google_storage_bucket.functions_source.name
  source = data.archive_file.functions_zip.output_path
}

# Cloud Function for beforeSignIn blocking (Gen1 - required for Identity Platform)
resource "google_cloudfunctions_function" "before_sign_in" {
  project     = var.project_id
  name        = "beforeSignIn"
  region      = var.region
  runtime     = "nodejs20"
  entry_point = "beforeSignIn"

  source_archive_bucket = google_storage_bucket.functions_source.name
  source_archive_object = google_storage_bucket_object.functions_zip.name

  trigger_http = true

  available_memory_mb = 256
  timeout             = 60
  max_instances       = 10
  ingress_settings    = "ALLOW_ALL"

  depends_on = [
    google_project_service.apis,
    google_storage_bucket_object.functions_zip,
  ]
}

# Allow Identity Platform to invoke beforeSignIn function
resource "google_cloudfunctions_function_iam_member" "before_sign_in_invoker" {
  project        = var.project_id
  region         = var.region
  cloud_function = google_cloudfunctions_function.before_sign_in.name
  role           = "roles/cloudfunctions.invoker"
  member         = "allUsers"
}

# Cloud Function for beforeCreate blocking (Gen1 - required for Identity Platform)
resource "google_cloudfunctions_function" "before_create" {
  project     = var.project_id
  name        = "beforeCreate"
  region      = var.region
  runtime     = "nodejs20"
  entry_point = "beforeCreate"

  source_archive_bucket = google_storage_bucket.functions_source.name
  source_archive_object = google_storage_bucket_object.functions_zip.name

  trigger_http = true

  available_memory_mb = 256
  timeout             = 60
  max_instances       = 10
  ingress_settings    = "ALLOW_ALL"

  depends_on = [
    google_project_service.apis,
    google_storage_bucket_object.functions_zip,
  ]
}

# Allow Identity Platform to invoke beforeCreate function
resource "google_cloudfunctions_function_iam_member" "before_create_invoker" {
  project        = var.project_id
  region         = var.region
  cloud_function = google_cloudfunctions_function.before_create.name
  role           = "roles/cloudfunctions.invoker"
  member         = "allUsers"
}

# Identity Platform configuration with blocking functions
resource "google_identity_platform_config" "default" {
  project = var.project_id

  sign_in {
    allow_duplicate_emails = false

    email {
      enabled           = false
      password_required = false
    }
  }

  blocking_functions {
    triggers {
      event_type   = "beforeSignIn"
      function_uri = google_cloudfunctions_function.before_sign_in.https_trigger_url
    }

    triggers {
      event_type   = "beforeCreate"
      function_uri = google_cloudfunctions_function.before_create.https_trigger_url
    }
  }

  depends_on = [
    google_project_service.apis,
    google_cloudfunctions_function.before_sign_in,
    google_cloudfunctions_function.before_create,
  ]
}

# Note: Google Sign-In provider should be enabled manually in Firebase Console
# Go to: https://console.firebase.google.com/project/mozdata-chat/authentication/providers
# Click "Google" → Enable → Save
# This is simpler than managing OAuth credentials in Terraform
