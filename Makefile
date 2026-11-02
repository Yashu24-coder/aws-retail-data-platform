.PHONY: help install run test lint fmt clean infra-plan infra-apply infra-destroy

# Lets `python -m retail_platform` work from a clean clone without installing.
export PYTHONPATH := src

help:            ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

install:         ## Install runtime + dev dependencies
	pip install -r requirements-dev.txt

run:             ## Full local pipeline: generate, ingest, silver, gold, quality, report
	PLATFORM_MODE=local python -m retail_platform.cli run-all --reset

run-keep:        ## Same, but keep the existing lake (incremental demo)
	PLATFORM_MODE=local python -m retail_platform.cli run-all

test:            ## Run the test suite
	pytest -q

lint:            ## Lint
	ruff check .

fmt:             ## Format and autofix
	ruff check --fix . && ruff format .

clean:           ## Delete the local lake and warehouse
	rm -rf data/lake data/warehouse data/raw reports/*.json

infra-plan:      ## Terraform plan (needs AWS credentials)
	cd infra/terraform && terraform init && terraform plan

infra-apply:     ## Terraform apply - creates billable resources
	cd infra/terraform && terraform apply

infra-destroy:   ## Tear everything down
	cd infra/terraform && terraform destroy
