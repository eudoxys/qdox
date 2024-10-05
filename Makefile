# Makefile
#
# You must run this after updating the code to ensure the documentation is updated as well
#

VENV=".venv/bin/activate"

docs/index.html: src/qdox/main.py src/qdox/__init__.py src/qdox/qdox.css Makefile pyproject.toml $(VENV)
	@echo Updating $@...
	(source .venv/bin/activate; pylint $< || true)
	(source .venv/bin/activate; python3 -m pip install .)
	(source .venv/bin/activate; qdox --withcss --debug)

$(VENV):
	@echo Creating $@...
	test -d .venv || python3 -m venv `echo $@ | cut -d/ -f1`
	(source $@; python3 -m pip install pip --upgrade -r requirements.txt .)
