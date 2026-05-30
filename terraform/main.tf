locals {
  app_name               = "ai-readiness-intelligence-studio"
  instance_name          = coalesce(var.instance_name, "${local.app_name}-${var.env}")
  bucket_name            = "youth-dev-ai-ollama-models-${var.env}"
  bucket_mount           = "/mnt/ollama-models"
  repo_dir               = "/opt/AI-Readiness-Intelligence-Studio"
  gcsfuse_cache          = "/var/cache/gcsfuse"
  startup_models         = join(" ", [for model in var.startup_models : "'${model}'"])
  startup_models_display = join(", ", var.startup_models)
  reasoning_model        = var.startup_models[0]
  structured_model       = length(var.startup_models) > 1 ? var.startup_models[1] : var.startup_models[0]
  common_labels = {
    app = "ai-readiness"
    env = var.env
  }

  startup_script = <<-EOT
    #!/usr/bin/env bash
    set -Eeuo pipefail

    exec > >(tee -a /var/log/ai-readiness-startup.log) 2>&1

    APP_NAME="${local.app_name}"
    REPO_DIR="${local.repo_dir}"
    BUCKET_NAME="${google_storage_bucket.ollama_models.name}"
    BUCKET_MOUNT="${local.bucket_mount}"
    CACHE_DIR="${local.gcsfuse_cache}"
    GCSFUSE_CONFIG="/etc/gcsfuse.yaml"
    MODELS=(${local.startup_models})
    PUBLIC_IP="$(curl -fsH 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip)"

    retry() {
      local attempts="$1"
      shift
      local n=1
      until "$@"; do
        if [ "$n" -ge "$attempts" ]; then
          return 1
        fi
        sleep $((n * 2))
        n=$((n + 1))
      done
    }

    wait_for_apt() {
      while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || fuser /var/lib/apt/lists/lock >/dev/null 2>&1; do
        echo "Waiting for apt locks to clear..."
        sleep 5
      done
    }

    install_base_packages() {
      wait_for_apt
      export DEBIAN_FRONTEND=noninteractive
      apt-get update
      apt-get install -y ca-certificates curl git gnupg lsb-release psmisc unzip
    }

    install_google_cloud_cli() {
      if command -v gcloud >/dev/null 2>&1; then
        return
      fi

      install -d -m 0755 /etc/apt/keyrings
      curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /etc/apt/keyrings/google-cloud.gpg
      echo "deb [signed-by=/etc/apt/keyrings/google-cloud.gpg] https://packages.cloud.google.com/apt cloud-sdk main" > /etc/apt/sources.list.d/google-cloud-sdk.list
      wait_for_apt
      apt-get update
      apt-get install -y google-cloud-cli
    }

    install_gcsfuse() {
      if command -v gcsfuse >/dev/null 2>&1; then
        return
      fi

      install -d -m 0755 /usr/share/keyrings
      curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | tee /usr/share/keyrings/cloud.google.asc >/dev/null
      echo "deb [signed-by=/usr/share/keyrings/cloud.google.asc] https://packages.cloud.google.com/apt gcsfuse-$(lsb_release -c -s) main" > /etc/apt/sources.list.d/gcsfuse.list
      wait_for_apt
      apt-get update
      apt-get install -y gcsfuse
    }

    install_docker() {
      if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
        return
      fi

      wait_for_apt
      apt-get update
      if ! apt-get install -y docker.io docker-compose-v2; then
        apt-get install -y docker.io docker-compose-plugin
      fi
      systemctl enable --now docker
      usermod -aG docker ubuntu || true
    }

    write_gcsfuse_config() {
      mkdir -p "${local.bucket_mount}" "${local.gcsfuse_cache}"
      cat > "$GCSFUSE_CONFIG" <<'EOF'
app-name: ai-readiness-intelligence-studio
profile: aiml-serving
implicit-dirs: true
cache-dir: /var/cache/gcsfuse
file-cache:
  max-size-mb: 4096
  enable-parallel-downloads: true
  cache-file-for-range-read: true
metadata-cache:
  ttl-secs: 300
  negative-ttl-secs: 0
  stat-cache-max-size-mb: 256
  type-cache-max-size-mb: 64
read:
  enable-buffered-read: true
  global-max-blocks: 64
write:
  enable-streaming-writes: true
file-system:
  rename-dir-limit: 200000
gcs-retries:
  max-retry-sleep: 30s
logging:
  severity: info
EOF
    }

    write_mount_service() {
      cat > /etc/systemd/system/ollama-models.service <<EOF
[Unit]
Description=Mount Ollama model bucket with Cloud Storage FUSE
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStartPre=/bin/mkdir -p ${local.bucket_mount} ${local.gcsfuse_cache}
ExecStart=/usr/bin/gcsfuse --config-file /etc/gcsfuse.yaml ${google_storage_bucket.ollama_models.name} ${local.bucket_mount}
ExecStop=/usr/bin/fusermount -u ${local.bucket_mount}
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

      systemctl daemon-reload
      systemctl enable ollama-models.service
      if mountpoint -q "${local.bucket_mount}"; then
        echo "Cloud Storage FUSE mount already present."
      else
        retry 5 systemctl start ollama-models.service
      fi
    }

    sync_repo() {
      mkdir -p /opt
      if [ ! -d "$REPO_DIR/.git" ]; then
        git clone --branch "${var.repo_branch}" --single-branch "${var.repo_url}" "$REPO_DIR"
      else
        git -C "$REPO_DIR" fetch origin "${var.repo_branch}"
        git -C "$REPO_DIR" checkout "${var.repo_branch}"
        git -C "$REPO_DIR" reset --hard "origin/${var.repo_branch}"
      fi
    }

    write_env_file() {
      cat > "$REPO_DIR/.env" <<EOF
USE_OLLAMA=true
OLLAMA_HOST=http://ollama:11434
OLLAMA_REASONING_MODEL=${local.reasoning_model}
OLLAMA_STRUCTURED_MODEL=${local.structured_model}
OLLAMA_LIGHTWEIGHT_MODEL=phi3.5:latest
OLLAMA_EMBEDDING_MODEL=nomic-embed-text:latest
OLLAMA_MODEL_MOUNT_PATH=${local.bucket_mount}
NEXT_PUBLIC_API_URL=http://${"$"}{PUBLIC_IP}:8000/api/v1
CORS_ORIGINS=http://${"$"}{PUBLIC_IP}:3000,http://localhost:3000,http://127.0.0.1:3000
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=aireadiness
POSTGRES_HOST=db
POSTGRES_PORT=5432
SECRET_KEY=${var.secret_key}
GROQ_API_KEY=${var.groq_api_key}
EOF
    }

    wait_for_ollama() {
      local retries=40
      local attempt=1
      until curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; do
        if [ "$attempt" -ge "$retries" ]; then
          docker compose -f "$REPO_DIR/docker-compose.yml" logs ollama || true
          return 1
        fi
        echo "Waiting for Ollama API... attempt $attempt/$retries"
        sleep 5
        attempt=$((attempt + 1))
      done
    }

    ensure_models() {
      local existing
      existing="$(docker compose -f "$REPO_DIR/docker-compose.yml" exec -T ollama ollama list 2>/dev/null || true)"

      for model in "${"$"}{MODELS[@]}"; do
        if echo "$existing" | awk 'NR > 1 {print $1}' | grep -Fxq "$model"; then
          echo "Model already present in mounted bucket: $model"
        else
          echo "Pulling missing Ollama model: $model"
          docker compose -f "$REPO_DIR/docker-compose.yml" exec -T ollama ollama pull "$model"
        fi
      done
    }

    bring_up_stack() {
      cd "$REPO_DIR"
      docker compose pull ollama || true
      docker compose up -d db ollama
      wait_for_ollama
      ensure_models
      docker compose up -d backend
      retry 10 docker compose exec -T backend alembic upgrade head
      docker compose up -d frontend
      docker compose ps
    }

    print_endpoints() {
      echo ""
      echo "============================================================"
      echo "AI Readiness Intelligence Studio deployment is ready"
      echo "Frontend: http://${"$"}{PUBLIC_IP}:3000"
      echo "Backend : http://${"$"}{PUBLIC_IP}:8000"
      echo "Ollama  : http://${"$"}{PUBLIC_IP}:11434"
      echo "Bucket  : gs://${"$"}{BUCKET_NAME}"
      echo "Models  : ${local.startup_models_display}"
      echo "============================================================"
    }

    install_base_packages
    install_google_cloud_cli
    install_gcsfuse
    install_docker
    write_gcsfuse_config
    write_mount_service
    sync_repo
    write_env_file
    bring_up_stack
    print_endpoints
  EOT
}

# Enable the core APIs used by this stack before provisioning dependent resources.
resource "google_project_service" "services" {
  for_each = toset([
    "compute.googleapis.com",
    "iam.googleapis.com",
    "storage.googleapis.com",
  ])

  project                    = var.project_id
  service                    = each.value
  disable_dependent_services = false
  disable_on_destroy         = false
}

# Discover the latest Ubuntu 24.04 LTS AMD64 image family so the VM stays current.
data "google_compute_image" "ubuntu_2404" {
  family  = "ubuntu-2404-lts-amd64"
  project = "ubuntu-os-cloud"

  depends_on = [google_project_service.services]
}

# Dedicated bucket for Ollama manifests and model blobs, separate from the VM lifecycle.
resource "google_storage_bucket" "ollama_models" {
  name          = local.bucket_name
  project       = var.project_id
  location      = var.region
  storage_class = var.bucket_storage_class
  force_destroy = var.bucket_force_destroy

  labels = local.common_labels

  versioning {
    enabled = true
  }

  uniform_bucket_level_access = true

  depends_on = [google_project_service.services]
}

# Service account used by the VM so gcsfuse can mount the bucket with ADC.
resource "google_service_account" "vm" {
  account_id   = "aireadiness-${var.env}-vm"
  display_name = "AI Readiness ${upper(var.env)} VM service account"
  description  = "Least-privilege runtime identity for the AI Readiness demo VM."

  depends_on = [google_project_service.services]
}

# Bucket-scoped write permissions are sufficient for gcsfuse mounts and Ollama model pulls.
resource "google_storage_bucket_iam_member" "vm_bucket_admin" {
  bucket = google_storage_bucket.ollama_models.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.vm.email}"
}

# Single demo VM that hosts Docker, Ollama, the backend API, and the Next.js frontend.
resource "google_compute_instance" "app" {
  name         = local.instance_name
  machine_type = var.machine_type
  zone         = var.zone

  tags = ["ai-readiness-demo", "ollama-demo"]

  labels = local.common_labels

  boot_disk {
    auto_delete = true

    initialize_params {
      image = data.google_compute_image.ubuntu_2404.self_link
      size  = var.boot_disk_size_gb
      type  = var.boot_disk_type
    }
  }

  network_interface {
    network = "default"

    access_config {}
  }

  service_account {
    email  = google_service_account.vm.email
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }

  metadata = length(var.ssh_public_keys) == 0 ? {} : {
    ssh-keys = join("\n", var.ssh_public_keys)
  }

  metadata_startup_script = local.startup_script

  scheduling {
    automatic_restart   = true
    on_host_maintenance = "MIGRATE"
  }

  depends_on = [
    google_project_service.services,
    google_storage_bucket_iam_member.vm_bucket_admin,
  ]
}

# Open only the demo ports required for SSH, the frontend, the backend, and Ollama.
resource "google_compute_firewall" "demo_ingress" {
  name    = "${local.app_name}-${var.env}-ingress"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["22", "80", "443", "8000", "3000", "11434"]
  }

  source_ranges = var.allowed_source_ranges
  target_tags   = google_compute_instance.app.tags

  depends_on = [google_project_service.services]
}
