PYTHON ?= python

# TODO: list every target that isn't a real file
.PHONY: setup pipeline test dashboard

# TODO: install everything in requirements.txt (use $(PYTHON) -m pip ...)
setup: 
	$(PYTHON) -m pip install -r requirements.txt

# TODO: run the 4 scripts in order: Part 1 -> Part 2 -> Part 3 -> Part 4
pipeline: 
	$(PYTHON) load_data.py
	$(PYTHON) cell_frequencies.py
	$(PYTHON) statistical_analysis.py
	$(PYTHON) subset_analysis.py

# TODO: run the test suite
test:
	$(PYTHON) -m pytest -v

# Starts the Streamlit dashboard (dashboard.py is built in the next milestone).
# --server.address 0.0.0.0 lets Codespaces forward the port to your browser.
dashboard:
	$(PYTHON) -m streamlit run dashboard.py --server.address 0.0.0.0 --server.port 8501