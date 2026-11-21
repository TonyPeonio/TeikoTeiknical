PYTHON ?= python

# TODO: list every target that isn't a real file
.PHONY: 

# TODO: install everything in requirements.txt (use $(PYTHON) -m pip ...)
setup: $(PYTHON) -m pip install -r requirements.txt

# TODO: run the 4 scripts in order: Part 1 -> Part 2 -> Part 3 -> Part 4
pipeline: 
python load_data.py
python cell_frequencies.py
python statistical_analysis.py
python subset_analysis.py

# TODO: run the test suite
test:
python -m pytest -v

# Starts the Streamlit dashboard (dashboard.py is built in the next milestone).
# --server.address 0.0.0.0 lets Codespaces forward the port to your browser.
dashboard:
	$(PYTHON) -m streamlit run dashboard.py --server.address 0.0.0.0 --server.port 8501