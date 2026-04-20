src=.

.PHONY: run
run: ## Build and start project
	@docker-compose build
	@docker-compose up -d

.PHONY: lint
lint: ## PEP8 syntax check
	@docker-compose run --rm --name flake8 --no-deps django python -m flake8 .

.PHONY: black
black: ## Black python code formatter
	@docker-compose run --rm --name black --no-deps django python -m black .

.PHONY: isort
isort: ## Orders imports alphabetically
	@docker-compose run --rm --name isort --no-deps django python -m isort .

.PHONY: collectstatic
collectstatic: ## Collect static files
	@docker-compose run --rm --name collectstatic --no-deps django ./manage.py collectstatic --noinput

.PHONY: migrations
migrations: ## Create migrations
	@docker-compose run --rm --name makemigrations --no-deps django ./manage.py makemigrations

.PHONY: migrate
migrate: ## Run migrations
	@docker-compose run --rm --name manage_migrate --no-deps django ./manage.py migrate --noinput

.PHONY: createsuperuser
createsuperuser: ## Create admin user
	docker-compose run --rm django $(src)/manage.py createsuperuser --email $(email) --settings=ms_registry.settings

.PHONY: pytest
pytest: ## Run pytest - args: [test-path=.] e.g. make pytest test-path=registry/tests/
	docker-compose run --rm django python -m pytest $(if $(test-path),$(test-path),)

.PHONY: gen-access-cert
gen-access-cert: ## Generate a dev access certificate from a cnf JWT - args: token=<jwt>
	@docker-compose run --rm --no-deps django ./manage.py generate_access_certificates_help_function --token $(token)
