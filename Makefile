.PHONY: lint test coverage build clean upload all

lint:
	pylint gkeepapi

test:
	python -m unittest discover

coverage:
	coverage run --source gkeepapi -m unittest discover
	coverage report
	coverage html

build: gkeepapi/*.py
	python setup.py bdist_wheel --universal

clean:
	rm -f dist/*.whl

upload:
	twine upload dist/*.whl

all: build upload
