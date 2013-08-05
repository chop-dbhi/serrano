docs:
	@sphinx-apidoc --force -o docs/api serrano
	@make -C docs html

.PHONY: docs
