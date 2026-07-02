# let-go-wiki — developer tasks.
# These mirror the `lgx` tasks (see lgx.edn) but use the underlying Python
# tools directly, so they work without lgx/mise (e.g. in CI).

# Authored Python (excludes the vendored OKF viewer in tools/viz/generator.py
# and its static assets, which we do not lint or reformat).
PYSRC := tools/check_wiki.py tools/build_site.py tools/viz/render_viz.py tools/tests

# `site/` is a generated directory; without .PHONY, make would see it and skip
# the `site` target. No other target has a same-named path, so keep this minimal.
.PHONY: site

all: lint test ## Lint and test (CI gate)

install: ## Install Python dependencies
	python -m pip install -r requirements.txt

test: ## Run the test suite
	python -m pytest tools -q

cover: ## One-shot coverage report
	python -m pytest tools --cov=tools --cov-report=term-missing

lint: ## Validate wiki pages + lint Python (autofix)
	python tools/check_wiki.py .
	ruff check --fix $(PYSRC)

format: ## Format authored Python code
	ruff format $(PYSRC)

doctor: ## Validate wiki pages against the schema
	python tools/check_wiki.py .

viz: ## Regenerate the OKF graph (viz.html)
	python tools/viz/render_viz.py . viz.html

site: ## Build the styled static site into site/
	python tools/build_site.py

serve: ## Local preview of the site
	python tools/build_site.py --serve

enrich: ## Prepare the authoring manifest (SOURCE_ROOT defaults to ../let-go)
	python -m tools.enrich.prepare --source-root $(or $(SOURCE_ROOT),../let-go)

status: ## Report authoring coverage vs the enrich manifest
	python -m tools.enrich.status

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-10s %s\n", $$1, $$2}'
