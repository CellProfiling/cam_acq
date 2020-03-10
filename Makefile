# Inspired by https://github.com/arve0/leicacam/blob/master/Makefile
.PHONY: help build clean clean-pyc lint test test-all coverage docs docs-api

help:
	@echo "build - build a distribution"
	@echo "check-format - check code format with black code formatter"
	@echo "clean - run all clean operations"
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "coverage - check code coverage with pytest-cov plugin"
	@echo "docs - generate Sphinx HTML documentation"
	@echo "docs-api - generate camacq rst file for Sphinx HTML documentation"
	@echo "docs-live - rebuild the documentation when a change is detected"
	@echo "format - format code with black code formatter"
	@echo "lint - check style with flake8, pylint and pydocstyle"
	@echo "release - package and upload a release to PyPI"
	@echo "test-release - package and upload a release to test PyPI"
	@echo "test - run tests quickly with the default Python"
	@echo "test-all - run tests on every Python version with tox"

build:
	python setup.py sdist bdist_wheel

check-format:
	black --check ./

clean: clean-build clean-pyc

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info

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

release: clean build
	twine upload dist/*

test-release: clean build
	twine upload --repository-url https://test.pypi.org/legacy/ dist/*

test:
	pytest -v tests/

test-all:
	tox
