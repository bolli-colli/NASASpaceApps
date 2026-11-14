"""End-to-end tests of the Streamlit app with artificial data in a temporary cache."""

import importlib.util

import pytest
from streamlit.testing.v1 import AppTest

from earth_trail_detective.config import DATA_DIR_VARIABLE, PROJECT_ROOT
from earth_trail_detective.infrastructure.parquet_repository import ParquetSeriesRepository
from earth_trail_detective.presentation.main import MODE_RESEARCHER

APP = str(PROJECT_ROOT / "app.py")
TIMEOUT = 60
DEMO_REGIONS = ("ohio_valley", "indo_gangetic_plain", "northern_hemisphere")


def _load_generator():
    """Import ``scripts/make_synthetic_cache.py`` (scripts are not a package)."""
    path = PROJECT_ROOT / "scripts" / "make_synthetic_cache.py"
    spec = importlib.util.spec_from_file_location("make_synthetic_cache", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def app(tmp_path, monkeypatch, catalog) -> AppTest:
    """The app, started on a temporary cache filled with artificial series."""
    generator = _load_generator()
    repository = ParquetSeriesRepository(tmp_path)
    for variable in catalog.variables():
        if variable.derivation is None:
            for region_id in DEMO_REGIONS:
                region = catalog.region(region_id)
                repository.save(variable, region, generator.synthetic_series(variable, region))
    monkeypatch.setenv(DATA_DIR_VARIABLE, str(tmp_path))
    from earth_trail_detective.presentation.main import _container

    _container.clear()  # do not reuse a container wired to another directory
    return AppTest.from_file(APP, default_timeout=TIMEOUT).run()


def _text(app: AppTest) -> str:
    """All visible text of the page."""
    elements = [*app.markdown, *app.caption, *app.info, *app.success, *app.error, *app.header]
    return "\n".join(str(element.value) for element in elements)


def test_demo_a1_shows_two_regions_cards_and_honest_labels(app):
    app.sidebar.button[0].click().run()
    assert not app.exception
    text = _text(app)
    assert "ARTIFICIAL DATA" in text  # synthetic data is never shown unmarked
    assert "Trail ends here" in text
    assert "Correlation is not causation" in text
    assert "**What?**" in text and "**Significant?**" in text
    assert len(app.get("plotly_chart")) >= 8  # at least 4 steps x 2 regions
    assert len(app.get("download_button")) == 2


def test_student_form_leads_to_a_result(app):
    app.button[0].click().run()  # submit the guided form with its defaults
    assert not app.exception
    assert len(app.get("plotly_chart")) >= 4


def test_researcher_form_validates_and_analyses(app):
    app.sidebar.radio[0].set_value(MODE_RESEARCHER).run()
    app.button[0].click().run()  # nothing selected yet
    assert "Choose at least one variable" in _text(app)
    app.multiselect[0].select(app.multiselect[0].options[0])
    app.button[0].click().run()
    assert not app.exception
    assert len(app.get("plotly_chart")) == 1


def test_validation_demo_shows_the_reference_check(app):
    app.sidebar.selectbox[0].select_index(2).run()  # demo V
    app.sidebar.button[0].click().run()
    assert not app.exception
    assert "Check against the known trend" in _text(app)
