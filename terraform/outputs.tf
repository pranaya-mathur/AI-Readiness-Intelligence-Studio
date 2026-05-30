output "instance_name" {
  description = "Compute Engine instance name."
  value       = google_compute_instance.app.name
}

output "instance_zone" {
  description = "Zone where the VM is deployed."
  value       = google_compute_instance.app.zone
}

output "instance_external_ip" {
  description = "Ephemeral public IP of the VM."
  value       = google_compute_instance.app.network_interface[0].access_config[0].nat_ip
}

output "frontend_url" {
  description = "Public URL for the demo frontend."
  value       = "http://${google_compute_instance.app.network_interface[0].access_config[0].nat_ip}:3000"
}

output "backend_url" {
  description = "Public URL for the FastAPI backend."
  value       = "http://${google_compute_instance.app.network_interface[0].access_config[0].nat_ip}:8000"
}

output "ollama_url" {
  description = "Public URL for the Ollama API."
  value       = "http://${google_compute_instance.app.network_interface[0].access_config[0].nat_ip}:11434"
}

output "ollama_bucket_name" {
  description = "Bucket that stores Ollama model blobs and manifests."
  value       = google_storage_bucket.ollama_models.name
}

output "ssh_command" {
  description = "Convenience SSH command for the created VM."
  value       = "gcloud compute ssh ${google_compute_instance.app.name} --zone ${google_compute_instance.app.zone} --project ${var.project_id}"
}

output "startup_log_command" {
  description = "Convenience command to follow the startup script log."
  value       = "gcloud compute ssh ${google_compute_instance.app.name} --zone ${google_compute_instance.app.zone} --project ${var.project_id} --command 'sudo tail -f /var/log/ai-readiness-startup.log'"
}
