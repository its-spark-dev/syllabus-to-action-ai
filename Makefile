PYTHON ?= python3

.PHONY: setup run run-dashboard verify

setup:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) -m streamlit run app.py

run-dashboard:
	$(PYTHON) -m streamlit run dashboard_app.py

verify:
	$(PYTHON) -m compileall app.py dashboard_app.py ai parser planner data
	$(PYTHON) - <<'PY'
from importlib import import_module
for mod in [
    'ai.engine',
    'parser.syllabus_parser',
    'planner.weekly_planner',
]:
    import_module(mod)
print('ok: imports')
PY

