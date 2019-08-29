# Inspired by https://github.com/arve0/leicacam/blob/master/Makefile
.PHONY: help clean clean-pyc lint test test-all coverage docs docs-api

help:
	@echo "check-format - check code format with black code formatter"
	@echo "clean - run all clean operations"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "coverage - check code coverage with pytest-cov plugin"
	@echo "docs - generate Sphinx HTML documentation"
	@echo "docs-api - generate camacq rst file for Sphinx HTML documentation"
	@echo "docs-live - rebuild the documentation when a change is detected"
	@echo "format - format code with black code formatter"
	@echo "lint - check style with flake8, pylint and pydocstyle"
	@echo "test - run tests quickly with the default Python"
	@echo "test-all - run tests on every Python version with tox"

check-format:
	black --check ./

clean: clean-pyc

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +

coverage:
	pytest -v --cov-report term-missing --cov=camacq tests/

docs:
	$(MAKE) -C docs clean
	$(MAKE) -C docs html

docs-api:
	sphinx-apidoc -MfT -o docs/source camacq

docs-live:
	$(MAKE) -C docs clean
	$(MAKE) -C docs livehtml

format:
	black ./

lint:
	tox -e lint

test:
	pytest -v tests/

test-all:
	tox
