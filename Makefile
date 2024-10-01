# Makefile
#
# You must run this after updating the code to ensure the documentation is updated as well
#

docs/index.html: quickdocs.py quickdocs.css Makefile pyproject.toml
	@test -d .venv || python3 -m venv .venv
	@echo Updating $@...
	(source .venv/bin/activate; python3 -m pip install pip --upgrade -r requirements.txt .; python3 -m quickdocs --withcss)
	@echo Done
	