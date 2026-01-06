variable "project_id" {
  description = "GCP project ID for the UI deployment"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "agent_engine_project" {
  description = "Project containing the Vertex AI Agent Engine"
  type        = string
}

variable "agent_engine_project_number" {
  description = "Project number of the agent engine project"
  type        = string
}

variable "agent_engine_resource_id" {
  description = "Vertex AI Agent Engine resource ID"
  type        = string
}

variable "container_image" {
  description = "Container image URL for the combined Next.js + Python service"
  type        = string
}

variable "service_name" {
  description = "Name of the Cloud Run service"
  type        = string
  default     = "mozdata-chat"
}
