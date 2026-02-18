# MS Registry Containerized Deployment Makefile

.PHONY: help build run stop logs clean test restart status shell migrate collectstatic

# Default target
help: ## Show this help message
	@echo "MS Registry - Containerized Django Deployment"
	@echo "This builds and deploys the MS Registry service"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build the Docker image
	@echo "Building docker-ms-registry containerized image from GitHub (main branch)..."
	docker build -t docker-ms-registry:latest https://github.com/AniaAlex/ms-registry.git#main

run: build ## Build and run docker-ms-registry with docker-compose
	@echo "Starting containerized docker-ms-registry"
	docker-compose up -d

stop: ## Stop the running service
	@echo "Stopping containerized docker-ms-registry"
	docker-compose down

logs: ## View service logs
	docker-compose logs -f docker-ms-registry

restart: stop run ## Restart the service

status: ## Check service status
	@echo "Service Status:"
	docker-compose ps

shell: ## Open a shell in the running container
	docker-compose exec docker-ms-registry /bin/bash

migrate: ## Run database migrations
	docker-compose exec docker-ms-registry python manage.py migrate

collectstatic: ## Collect static files
	docker-compose exec docker-ms-registry python manage.py collectstatic --noinput

test: ## Run tests
	@echo "Running ms-registry tests..."
	docker-compose exec docker-ms-registry python manage.py test --settings=ms_registry.settings_test

clean: ## Remove containers and volumes
	@echo "Cleaning up containers and volumes..."
	docker-compose down -v
	docker rmi docker-ms-registry:latest || true
