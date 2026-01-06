output "project_id" {
  description = "GCP project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP region"
  value       = var.region
}

output "service_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_v2_service.app.uri
}

output "service_name" {
  description = "Cloud Run service name"
  value       = google_cloud_run_v2_service.app.name
}

output "artifact_registry_repository" {
  description = "Artifact Registry repository URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.repository_id}"
}

output "service_account_email" {
  description = "Service account email for the Cloud Run service"
  value       = google_service_account.app.email
}

output "functions_source_bucket" {
  description = "Storage bucket for Cloud Functions source code"
  value       = google_storage_bucket.functions_source.name
}

output "before_sign_in_function_uri" {
  description = "URI of the beforeSignIn blocking function"
  value       = google_cloudfunctions_function.before_sign_in.https_trigger_url
}

output "before_create_function_uri" {
  description = "URI of the beforeCreate blocking function"
  value       = google_cloudfunctions_function.before_create.https_trigger_url
}
