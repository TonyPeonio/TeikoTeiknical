"""Smoke test: the dashboard script runs top to bottom without raising an error.

Streamlit's AppTest runs the app in memory (no browser, no server).
It needs the real cell-count.db, so the test is skipped if the pipeline
hasn't been run yet.
"""

import os

import pytest
from streamlit.testing.v1 import AppTest

pytestmark = pytest.mark.skipif(
    not os.path.exists("cell-count.db"), reason="run `make pipeline` first")


def test_dashboard_runs_without_errors():
    app = AppTest.from_file("dashboard.py", default_timeout=60).run()

    assert not app.exception
    assert len(app.tabs) == 3
    # The Part 4 B-cell answer is on the page.
    assert any(m.value == "10206.15" for m in app.metric)
