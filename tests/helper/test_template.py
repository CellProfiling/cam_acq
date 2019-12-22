"""Test the template helper."""
import pytest
from ruamel.yaml import YAML

from camacq.helper.template import make_template, render_template

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio  # pylint: disable=invalid-name


async def test_next_well(center, sample):
    """Test next well template function."""
    data = """
        data:
          next_well_x: >
            {{next_well_x(samples.test, 'test_plate')}}
          next_well_y: >
            {{next_well_y(samples.test, 'test_plate')}}
    """

    data = YAML(typ="safe").load(data)
    center.samples.test.set_plate("test_plate")
    tmpl = make_template(center, data)
    variables = {"samples": center.samples}
    render = render_template(tmpl, variables)
    assert render["data"]["next_well_x"] == "0"
    assert render["data"]["next_well_y"] == "0"

    center.samples.test.set_well("test_plate", 0, 0)
    center.samples.test.set_field("test_plate", 0, 0, 0, 0, img_ok=True)

    render = render_template(tmpl, variables)
    assert render["data"]["next_well_x"] == "0"
    assert render["data"]["next_well_y"] == "1"


async def test_next_well_no_plate(center, sample):
    """Test next well template function without plate."""
    data = """
        data:
          next_well_x: >
            {{next_well_x(samples.test, 'test_plate')}}
          next_well_y: >
            {{next_well_y(samples.test, 'test_plate')}}
    """

    data = YAML(typ="safe").load(data)
    tmpl = make_template(center, data)
    variables = {"samples": center.samples}
    render = render_template(tmpl, variables)
    assert render["data"]["next_well_x"] == "None"
    assert render["data"]["next_well_y"] == "None"
