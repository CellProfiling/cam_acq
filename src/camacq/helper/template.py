"""Handle templates."""

import jinja2
from jinja2.sandbox import ImmutableSandboxedEnvironment

from camacq.exceptions import TemplateError
from camacq.plugins.leica.sample import next_well_xy
from camacq.plugins.sample import get_matched_samples

TEMPLATE_ENV_DATA = "template_env"


def get_env(center):
    """Get the template environment."""
    if TEMPLATE_ENV_DATA not in center.data:
        env = ImmutableSandboxedEnvironment()
        env = _set_global(env, "next_well_xy", template_next_well_xy)
        env = _set_global(env, "next_well_x", template_next_well_x)
        env = _set_global(env, "next_well_y", template_next_well_y)
        env = _set_global(env, "matched_samples", get_matched_samples)
        center.data[TEMPLATE_ENV_DATA] = env
    return center.data[TEMPLATE_ENV_DATA]


def _set_global(env, func_name, func):
    """Set a template environment global function."""
    env.globals[func_name] = func
    return env


def make_template(center, data):
    """Make templated data."""
    if isinstance(data, dict):
        return {key: make_template(center, val) for key, val in data.items()}

    if isinstance(data, list):
        return [make_template(center, val) for val in data]

    env = get_env(center)
    return env.from_string(str(data))


def render_template(data, variables):
    """Render templated data."""
    if isinstance(data, dict):
        return {key: render_template(val, variables) for key, val in data.items()}

    if isinstance(data, list):
        return [render_template(val, variables) for val in data]

    try:
        rendered = data.render(variables)
    except jinja2.TemplateError as exc:
        raise TemplateError(exc) from exc
    return rendered


def template_next_well_xy(sample, plate_name, x_wells=12, y_wells=8):
    """Return the next not done well for the given plate x, y format."""
    return next_well_xy(sample, plate_name, x_wells, y_wells)


def template_next_well_x(sample, plate_name, x_wells=12, y_wells=8):
    """Return the next well x coordinate for the plate x, y format."""
    x_well, _ = next_well_xy(sample, plate_name, x_wells=x_wells, y_wells=y_wells)
    return x_well


def template_next_well_y(sample, plate_name, x_wells=12, y_wells=8):
    """Return the next well x coordinate for the plate x, y format."""
    _, y_well = next_well_xy(sample, plate_name, x_wells=x_wells, y_wells=y_wells)
    return y_well
