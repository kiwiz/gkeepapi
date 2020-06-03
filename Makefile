.PHONY: lint test coverage build clean upload all

lint:
	pylint gkeepapi

test:
	python3 -m unittest discover

coverage:
	coverage run --source gkeepapi -m unittest discover
	coverage report
	coverage html

build: gkeepapi/*.py
	python3 setup.py bdist_wheel

clean:
	rm -f dist/*.whl

upload:
	twine upload dist/*.whl

all: build upload
