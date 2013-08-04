docs:
	@sphinx-apidoc --force -o docs/api serrano
	@make -C docs -f Makefile html

.PHONY: docs
