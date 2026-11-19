# Provisioning foundation only. Workload deployment is intentionally not claimed complete.
terraform {
  required_providers {
    google = { source = "hashicorp/google", version = "~> 6.0" }
  }
}
variable "project_id" { type = string }
variable "region" {
  type = string
  default = "africa-south1"
}
variable "artifact_bucket_name" { type = string }
provider "google" {
  project = var.project_id
  region = var.region
}

resource "google_project_service" "required" {
  for_each = toset(["run.googleapis.com", "sqladmin.googleapis.com", "secretmanager.googleapis.com", "cloudtasks.googleapis.com", "monitoring.googleapis.com", "iamcredentials.googleapis.com"])
  service = each.key
  disable_on_destroy = false
}
resource "google_service_account" "api" {
  account_id = "arcambe-api"
  display_name = "ARCAMBE API"
}
resource "google_service_account" "worker" {
  account_id = "arcambe-worker"
  display_name = "ARCAMBE raster worker"
}
resource "google_service_account" "artifact_signer" {
  account_id = "arcambe-artifact-signer"
  display_name = "ARCAMBE private artifact signing"
}
resource "google_project_iam_custom_role" "bucket_policy_reader" {
  role_id = "arcambeBucketPolicyReader"
  title = "ARCAMBE bucket policy verification"
  permissions = ["storage.buckets.get"]
}
resource "google_project_iam_custom_role" "artifact_signer" {
  role_id = "arcambeArtifactSigner"
  title = "ARCAMBE signed artifact downloads"
  permissions = ["iam.serviceAccounts.signBlob"]
}
resource "google_service_account_iam_member" "artifact_signing" {
  for_each = { api = google_service_account.api.email, worker = google_service_account.worker.email }
  service_account_id = google_service_account.artifact_signer.name
  role = google_project_iam_custom_role.artifact_signer.name
  member = "serviceAccount:${each.value}"
}
resource "google_storage_bucket" "artifacts" {
  name = var.artifact_bucket_name
  location = var.region
  uniform_bucket_level_access = true
  public_access_prevention = "enforced"
  force_destroy = false
  versioning { enabled = true }
}
resource "google_storage_bucket_iam_member" "worker" {
  bucket = google_storage_bucket.artifacts.name
  role = "roles/storage.objectUser"
  member = "serviceAccount:${google_service_account.worker.email}"
}
resource "google_storage_bucket_iam_member" "api" {
  bucket = google_storage_bucket.artifacts.name
  role = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.api.email}"
}
resource "google_storage_bucket_iam_member" "policy_readers" {
  for_each = { api = google_service_account.api.email, worker = google_service_account.worker.email }
  bucket = google_storage_bucket.artifacts.name
  role = google_project_iam_custom_role.bucket_policy_reader.name
  member = "serviceAccount:${each.value}"
}
resource "google_storage_bucket_iam_member" "signer_read" {
  bucket = google_storage_bucket.artifacts.name
  role = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.artifact_signer.email}"
}
resource "google_secret_manager_secret" "database_url" {
  secret_id = "arcambe-database-url"
  replication {
    auto {}
  }
}
resource "google_secret_manager_secret" "download_secret" {
  secret_id = "arcambe-download-secret"
  replication {
    auto {}
  }
}
# Secret versions are populated through Secret Manager, never Terraform variables/state.
