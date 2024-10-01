# Makefile
#
# You must run this after updating the code to ensure the documentation is updated as well
#

all: docs/index.html docs/quickdocs.css

docs/index.html: quickdocs.py Makefile pyproject.toml
	@test -d .venv || python3 -m venv .venv
	@echo Updating $@...
	(source .venv/bin/activate; python3 -m pip install pip --upgrade -r requirements.txt .; python3 -m quickdocs --withcss)
	@echo Done
	
docs/quickdocs.css: quickdocs.css
	cp quickdocs.css docs/quickdocs.css