import dss_custom_tools


def test_version() -> None:
    assert dss_custom_tools.__version__ != "999"
