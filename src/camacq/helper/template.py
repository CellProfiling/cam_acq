"""Handle templates."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import jinja2
from jinja2.sandbox import ImmutableSandboxedEnvironment

from camacq.exceptions import TemplateError
from camacq.plugins.leica.sample import LeicaSample, next_well_xy
from camacq.plugins.sample import get_matched_samples

if TYPE_CHECKING:
    from camacq.control import Center
    from camacq.plugins.sample import Sample

TEMPLATE_ENV_DATA = "template_env"


def get_env(center: Center) -> ImmutableSandboxedEnvironment:
    """Get the template environment."""
    if TEMPLATE_ENV_DATA not in center.data:
        env = ImmutableSandboxedEnvironment()
        env = _set_global(env, "next_well_xy", template_next_well_xy)
        env = _set_global(env, "next_well_x", template_next_well_x)
        env = _set_global(env, "next_well_y", template_next_well_y)
        env = _set_global(env, "matched_samples", get_matched_samples)
        center.data[TEMPLATE_ENV_DATA] = env
    return center.data[TEMPLATE_ENV_DATA]


def _set_global(
    env: ImmutableSandboxedEnvironment, func_name: str, func: Any
) -> ImmutableSandboxedEnvironment:
    """Set a template environment global function."""
    env.globals[func_name] = func
    return env


def make_template(center: Center, data: Any) -> Any:
    """Make templated data."""
    if isinstance(data, dict):
        return {key: make_template(center, val) for key, val in data.items()}

    if isinstance(data, list):
        return [make_template(center, val) for val in data]

    env = get_env(center)
    return env.from_string(str(data))


def render_template(data: Any, variables: dict[str, Any]) -> Any:
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


def template_next_well_xy(
    sample: Sample, plate_name: str, x_wells: int = 12, y_wells: int = 8
) -> tuple[int | None, int | None]:
    """Return the next not done well for the given plate x, y format."""
    return next_well_xy(sample, plate_name, x_wells, y_wells)  # type: ignore[arg-type]


def template_next_well_x(
    sample: LeicaSample, plate_name: str, x_wells: int = 12, y_wells: int = 8
) -> int | None:
    """Return the next well x coordinate for the plate x, y format."""
    x_well, _ = next_well_xy(
        sample,
        plate_name,
        x_wells=x_wells,
        y_wells=y_wells,
    )
    return x_well


def template_next_well_y(
    sample: LeicaSample, plate_name: str, x_wells: int = 12, y_wells: int = 8
) -> int | None:
    """Return the next well x coordinate for the plate x, y format."""
    _, y_well = next_well_xy(
        sample,
        plate_name,
        x_wells=x_wells,
        y_wells=y_wells,
    )
    return y_well
