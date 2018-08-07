lint:
	pylint gkeepapi

build: gkeepapi/*.py
	python setup.py bdist_wheel --universal

clean:
	rm -f dist/*.whl

upload:
	twine upload dist/*.whl

all: build upload
