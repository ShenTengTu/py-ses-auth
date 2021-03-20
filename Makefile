.PHONY: install-dev sdist sdist-clean upload-pypi upload-testpypi

## Install package in development mode.
install-dev:
	@pip install --editable .
## Build source distribution.
sdist:
	@python setup.py sdist
## Clean source distribution.
sdist-clean:
	@rm -rf ./dist ./*egg-info
## Upload distribution to PyPI.
upload-pypi:
	@twine upload --repository pypi dist/*
## Upload distribution to test PyPI.
upload-testpypi:
	@twine upload --repository testpypi dist/*