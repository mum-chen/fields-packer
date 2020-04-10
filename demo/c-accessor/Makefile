test: gen_lib
	gcc -o build/test -Ibuild -Itest test/test.c

gen_lib:
	mkdir -p build
	python3 accessor.py
