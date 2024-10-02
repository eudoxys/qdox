# Makefile
#
# You must run this after updating the code to ensure the documentation is updated as well
#

docs/index.html: qdox.py qdox.css Makefile pyproject.toml .venv/bin/activate
	@echo Updating $@...
	@(source .venv/bin/activate; pylint qdox.py || true)
	@(source .venv/bin/activate; python3 -m qdox --withcss)

.venv/bin/activate:
	@test -d .venv || python3 -m venv .venv
	@(source .venv/bin/activate; python3 -m pip install pip --upgrade -r requirements.txt .)
