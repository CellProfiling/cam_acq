"""Test the template helper."""
import pytest
from ruamel.yaml import YAML

from camacq.helper.template import make_template, render_template

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio  # pylint: disable=invalid-name


async def test_next_well(center):
    """Test next well template function."""
    data = """
        data:
          next_well_x: >
            {{next_well_x('test_plate')}}
          next_well_y: >
            {{next_well_y('test_plate')}}
    """

    data = await center.add_executor_job(YAML(typ="safe").load, data)
    center.sample.set_plate("test_plate")
    tmpl = make_template(center, data)
    render = render_template(tmpl, {})
    assert render["data"]["next_well_x"] == "0"
    assert render["data"]["next_well_y"] == "0"

    center.sample.set_well("test_plate", 0, 0)
    center.sample.set_field("test_plate", 0, 0, 0, 0, img_ok=True)

    render = render_template(tmpl, {})
    assert render["data"]["next_well_x"] == "0"
    assert render["data"]["next_well_y"] == "1"


async def test_next_well_no_plate(center):
    """Test next well template function without plate."""
    data = """
        data:
          next_well_x: >
            {{next_well_x('test_plate')}}
          next_well_y: >
            {{next_well_y('test_plate')}}
    """

    data = await center.add_executor_job(YAML(typ="safe").load, data)
    tmpl = make_template(center, data)
    render = render_template(tmpl, {})
    assert render["data"]["next_well_x"] == "None"
    assert render["data"]["next_well_y"] == "None"
