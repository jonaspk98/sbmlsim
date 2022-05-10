import pytest

from sbmlsim.plot.plotting import ColorType, Style


color_data = [
    # not supporting one-characters
    # ("r", "#ff0000ff", 1.0),  # depend on mpl settings and version
    # ("g", "#008000ff", 1.0),  # depend on mpl settings and version
    # ("b", "#0000ffff", 1.0),  # depend on mpl settings and version
    ("white", "#ffffffff", 1.0),
    ("black", "#000000ff", 1.0),
    ("#1234ff44", "#1234ff44", 1.0),
    ("#1234ff", "#1234ffff", 1.0),
    ("#56784a", "#56784a00", 0.0),
]


@pytest.mark.parametrize("color, hex, alpha", color_data)
def test_parse_color(color, hex, alpha):
    c = ColorType.parse_color(color, alpha=alpha)
    assert c.color == hex
