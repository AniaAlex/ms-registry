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
opts	:= $(opts)

ifeq ("$(detach)", "yes")
	opts := $(opts) -d
endif
ifeq ("$(build)", "yes")
	opts := $(opts) --build
endif

ifneq ("$(test-path)", "")
	cargs := $(test-path)
else
	cargs := $(src)
endif
ifeq ("$(tag)", "")
	cargs := $(cargs) --exclude-tag=integration
else ifeq ("$(tag)", "all")
	cargs := $(cargs)
else
	cargs := $(cargs) --tag=$(tag)
endif
ifneq ("$(verbosity)", "")
	cargs := $(cargs) -v $(verbosity)
else
	cargs := $(cargs)
endif
ifeq ("$(keepdb)", "yes")
	cargs := $(cargs) --keepdb
endif

.PHONY: createsuperuser
createsuperuser: ## Create admin user and 2FA QR code
	docker-compose run --rm django $(src)/manage.py createsuperuser --email $(email) --settings=rp_register.settings
	@echo One time use token:
	docker-compose run --rm django $(src)/manage.py addstatictoken $(email) --settings=rp_register.settings

.PHONY: addstatictoken
addstatictoken: ## Get 2FA code for email
	docker-compose run --rm django $(src)/manage.py addstatictoken $(email) --settings=rp_register.settings

.PHONY: test
test: ## Run unit tests - args: [detach=no] [keepdb=no] [test-path=.]
	docker-compose run --rm $(opts) django $(src)/manage.py test -t $(src) $(cargs) --settings=rp_register.settings_test
