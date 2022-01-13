"""Test the template helper."""
from ruamel.yaml import YAML

from camacq.helper.template import make_template, render_template


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
    tmpl = make_template(center, data)
    variables = {"samples": center.samples}
    await center.samples.test.set_sample("plate", plate_name="test_plate")
    render = render_template(tmpl, variables)

    assert render["data"]["next_well_x"] == "0"
    assert render["data"]["next_well_y"] == "0"

    await center.samples.test.set_sample(
        "well",
        plate_name="test_plate",
        well_x=0,
        well_y=0,
        values={"well_img_ok": True},
    )

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
