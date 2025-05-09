from unittest.mock import Mock

import pytest
from ipywidgets import Output, ToggleButton, VBox

from dss_custom_tools.jupyter_form import DownloadForm


@pytest.fixture
def mock_client():
    mock = Mock()
    mock.get_collections.return_value.collection_ids = ["dataset1", "dataset2"]
    mock.get_collection.return_value = Mock(
        form=[
            {
                "name": "var",
                "type": "StringListWidget",
                "label": "Variables",
                "details": {
                    "labels": {"t2m": "2m temperature", "u10": "10m wind"},
                    "values": ["t2m", "u10"],
                    "default": ["t2m"],
                    "columns": 2,
                },
            }
        ],
        apply_constraints=lambda sel: {"var": ["t2m", "u10"]},
        title="Test Dataset",
    )
    return mock


# @pytest.mark.skipif(not _IPYWIDGETS, reason="ipywidgets is not available")
def test_form_initialization(mock_client):
    form = DownloadForm(client=mock_client)
    assert form.client == mock_client
    assert isinstance(form.output, Output)
    assert form.collection_widget.options == ("dataset1", "dataset2")
    assert form.collection_id is None
    assert form.request == {}


# @pytest.mark.skipif(not _IPYWIDGETS, reason="ipywidgets is not available")
def test_collection_selection_triggers_build(mock_client):
    form = DownloadForm(client=mock_client)
    form.collection_widget.value = "dataset1"
    assert form.collection_id == "dataset1"
    assert "var" in form.widget_defs
    widget = form.widget_defs["var"]
    assert isinstance(widget, VBox)


# @pytest.mark.skipif(not _IPYWIDGETS, reason="ipywidgets is not available")
def test_widget_creation_from_metadata(mock_client):
    form = DownloadForm(client=mock_client)
    form._build_form("dataset1")

    widget = form.widget_defs["var"]
    assert hasattr(widget, "_get_value")

    # Simulate ToggleButton click
    gridbox = widget.children[1]
    buttons = gridbox.children
    assert isinstance(buttons[0], ToggleButton)

    buttons[0].value = True  # Simulate user clicking
    value = widget._get_value()
    assert value == ["t2m"]


# @pytest.mark.skipif(not _IPYWIDGETS, reason="ipywidgets is not available")
def test_static_form_parser_filters():
    form = [
        {
            "name": "format",
            "type": "LicenceWidget",  # Ignored
        },
        {
            "name": "valid",
            "type": "StringChoiceWidget",
            "label": "Choose one",
            "details": {"labels": {"a": "A", "b": "B"}, "values": ["a", "b"]},
        },
    ]
    parsed = DownloadForm._form_json_to_widgets_dict(form)
    assert "valid" in parsed
    assert parsed["valid"]["type"] == "radio"
    assert "format" not in parsed
