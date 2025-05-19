.PHONY: build up down bash
COMPOSE=docker-compose $(COMPOSE_OPTS)

build:
	$(COMPOSE) build

up: build
	$(COMPOSE) up

down:
	$(COMPOSE) down --rmi all --volumes --remove-orphans

bash:
	$(COMPOSE) exec app bash
