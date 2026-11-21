PYTHON ?= python

# TODO: list every target that isn't a real file
.PHONY: setup pipeline test dashboard

setup: 
	$(PYTHON) -m pip install -r requirements.txt

pipeline: 
	$(PYTHON) load_data.py
	$(PYTHON) cell_frequencies.py
	$(PYTHON) statistical_analysis.py
	$(PYTHON) subset_analysis.py

test:
	$(PYTHON) -m pytest -v

# --server.address 0.0.0.0 lets Codespaces forward the port to your browser.
dashboard:
	$(PYTHON) -m streamlit run dashboard.py --server.headless true --server.address 0.0.0.0 --server.port 8501