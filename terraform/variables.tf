variable "project_id" {
  description = "Google Cloud project ID that will host the demo stack."
  type        = string
  default     = "youth-dev-ai"
}

variable "env" {
  description = "Short environment suffix used in names, labels, and bucket naming."
  type        = string
  default     = "demo"
}

variable "region" {
  description = "Primary Google Cloud region for storage and compute resources."
  type        = string
  default     = "asia-south1"
}

variable "zone" {
  description = "Primary zone where the Compute Engine VM will run."
  type        = string
  default     = "asia-south1-a"
}

variable "machine_type" {
  description = "Compute Engine machine type for the demo VM."
  type        = string
  default     = "e2-standard-4"
}

variable "boot_disk_size_gb" {
  description = "Boot disk size for the VM in GB."
  type        = number
  default     = 100
}

variable "boot_disk_type" {
  description = "Boot disk type for the VM."
  type        = string
  default     = "pd-balanced"
}

variable "instance_name" {
  description = "Override for the VM name. Leave null to derive it from the project name and env."
  type        = string
  default     = null
}

variable "repo_url" {
  description = "Git repository cloned by the startup script."
  type        = string
  default     = "https://github.com/pranaya-mathur/AI-Readiness-Intelligence-Studio"
}

variable "repo_branch" {
  description = "Git branch checked out by the startup script."
  type        = string
  default     = "main"
}

variable "startup_models" {
  description = "Ollama models to preload on first boot if they do not already exist in the mounted bucket."
  type        = list(string)
  default     = ["qwen2.5:7b", "llama3:8b"]

  validation {
    condition     = length(var.startup_models) > 0
    error_message = "startup_models must contain at least one Ollama model tag."
  }
}

variable "bucket_storage_class" {
  description = "Storage class for the Ollama model bucket."
  type        = string
  default     = "STANDARD"
}

variable "bucket_force_destroy" {
  description = "If true, deleting the bucket resource will also delete stored models. Keep true only when you explicitly want bucket deletion."
  type        = bool
  default     = true
}

variable "allowed_source_ranges" {
  description = "CIDR blocks allowed to reach the demo VM over the opened firewall ports."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "ssh_public_keys" {
  description = "Optional list of SSH public keys in Compute Engine metadata format, for example 'ubuntu:ssh-ed25519 AAAA...'."
  type        = list(string)
  default     = []
}

variable "secret_key" {
  description = "Application secret key passed into the backend container."
  type        = string
  default     = "change-me-before-public-demo"
  sensitive   = true
}

variable "groq_api_key" {
  description = "Optional Groq API key. Leave empty for Ollama-only demos."
  type        = string
  default     = ""
  sensitive   = true
}
