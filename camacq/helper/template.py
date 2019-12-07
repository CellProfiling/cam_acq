"""Handle templates."""
import jinja2
from jinja2.sandbox import ImmutableSandboxedEnvironment

from camacq.exceptions import TemplateError
from camacq.plugins.sample.helper import next_well_xy

TEMPLATE_ENV_DATA = "template_env"


def get_env(center):
    """Get the template environment."""
    if TEMPLATE_ENV_DATA not in center.data:
        env = ImmutableSandboxedEnvironment()
        template_functions = TemplateFunctions(center)
        env = _set_global(env, "next_well_xy", template_functions.next_well_xy)
        env = _set_global(env, "next_well_x", template_functions.next_well_x)
        env = _set_global(env, "next_well_y", template_functions.next_well_y)
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
        raise TemplateError(exc)
    return rendered


class TemplateFunctions:
    """Group template functions."""

    def __init__(self, center):
        """Set up instance."""
        self._center = center

    def next_well_xy(self, plate_name, x_wells=12, y_wells=8):
        """Return the next not done well for the given plate x, y format."""
        return next_well_xy(self._center.sample, plate_name, x_wells, y_wells)

    def next_well_x(self, plate_name, x_wells=12, y_wells=8):
        """Return the next well x coordinate for the plate x, y format."""
        x_well, _ = self.next_well_xy(plate_name, x_wells=x_wells, y_wells=y_wells)
        return x_well

    def next_well_y(self, plate_name, x_wells=12, y_wells=8):
        """Return the next well x coordinate for the plate x, y format."""
        _, y_well = self.next_well_xy(plate_name, x_wells=x_wells, y_wells=y_wells)
        return y_well
