src=.

.PHONY: run
run: env ## Build and start project
	@docker-compose build
	@docker-compose up -d
	@echo "Waiting for postgres to be ready..."
	@until docker-compose exec -T postgres sh -c 'pg_isready -U "$${POSTGRES_USER:-postgres}" -q'; do sleep 1; done
	@echo "Postgres is ready."
	@$(MAKE) migrate
	@$(MAKE) init-ca

.PHONY: env
env: ## Create .env from .env.example if not exists
	@test -f .env || (cp .env.example .env && echo "Created .env from .env.example")

.PHONY: init-ca
init-ca: ## Initialize Access CA if not exists
	@docker-compose run --rm django sh -c '\
		python manage.py shell -c "from django_ca.models import CertificateAuthority; exit(0 if CertificateAuthority.objects.filter(name=\"SE Access CA\").exists() else 1)" 2>/dev/null \
		&& echo "Access CA already exists" \
		|| (python manage.py init_ca \
			--key-type EC \
			--elliptic-curve secp384r1 \
			--algorithm SHA-384 \
			--path-length 0 \
			"SE Access CA" \
			"CN=SE Access Certificate Authority,O=EUDI Wallet Registry,C=SE" \
		&& echo "Access CA initialized")'

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
