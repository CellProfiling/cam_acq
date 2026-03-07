"""Handle renaming of an image."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import voluptuous as vol

from camacq.helper import BASE_ACTION_SCHEMA, has_at_least_one_key

if TYPE_CHECKING:
    from camacq.control import Center

_LOGGER = logging.getLogger(__name__)
ACTION_RENAME_IMAGE = "rename_image"


async def setup_module(center: Center, config: dict[str, Any]) -> None:
    """Set up image rename plugin.

    Parameters
    ----------
    center : Center instance
        The Center instance.
    config : dict
        The config dict.

    """

    async def handle_action(**kwargs: Any) -> None:
        """Handle the action call to rename an image.

        Parameters
        ----------
        **kwargs
            Arbitrary keyword arguments. These will be passed to the
            action function when an action is called.

        """
        sample_name: str = kwargs["sample"]
        old_path = Path(kwargs["old_path"])
        new_path: Path | str | None = kwargs.get("new_path")
        new_name: str | None = kwargs.get("new_name")

        if new_name:
            old_dir = old_path.parent
            new_path = old_dir / new_name

        if new_path is None:
            _LOGGER.error("new_path is required")
            return

        new_path_resolved = Path(new_path)  # make sure new_path is a Path instance

        result = await center.add_executor_job(
            rename_image, old_path, new_path_resolved
        )
        if not result:
            return
        sample = center.samples[sample_name]
        image = sample.images.pop(old_path, None)
        if image is None:
            return
        image_attrs = image.__dict__.copy()
        image_attrs.pop("_path")
        image_attrs.pop("_values")
        await sample.set_sample(
            image.name, path=new_path_resolved, values=image.values, **image_attrs
        )

    rename_image_action_schema = vol.All(
        BASE_ACTION_SCHEMA.extend(
            {
                vol.Required("sample"): vol.All(
                    vol.Coerce(str), vol.In(center.samples)
                ),
                vol.Required("old_path"): vol.Coerce(str),
                vol.Exclusive("new_path", "new_file"): vol.Coerce(str),
                vol.Exclusive("new_name", "new_file"): vol.Coerce(str),
            }
        ),
        has_at_least_one_key("new_path", "new_name"),
    )

    center.actions.register(
        "rename_image",
        ACTION_RENAME_IMAGE,
        handle_action,
        rename_image_action_schema,
    )


def rename_image(old_path: Path, new_path: Path) -> bool:
    """Rename image at old_path to new_path.

    Parameters
    ----------
    old_path : str
        The absolute path to the existing image.
    new_path : str
        The absolute path to the renamed image.

    """
    renamed = False
    try:
        old_path.replace(new_path)
    except FileNotFoundError as exc:
        _LOGGER.error("File not found: %s", exc)
    except OSError as exc:
        _LOGGER.error("Failed to rename image: %s", exc)
    else:
        renamed = True
    return renamed
