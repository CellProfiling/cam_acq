"""Handle renaming of an image."""
import logging
import os

import voluptuous as vol

from camacq.helper import BASE_ACTION_SCHEMA

_LOGGER = logging.getLogger(__name__)
ACTION_RENAME_IMAGE = "rename_image"


async def setup_module(center, config):
    """Set up image rename plugin.

    Parameters
    ----------
    center : Center instance
        The Center instance.
    config : dict
        The config dict.
    """

    async def handle_action(**kwargs):
        """Handle the action call to rename an image.

        Parameters
        ----------
        **kwargs
            Arbitrary keyword arguments. These will be passed to the
            action function when an action is called.
        """
        sample_name = kwargs["sample"]
        old_path = kwargs["old_path"]
        new_path = kwargs.get("new_path")
        new_name = kwargs.get("new_name")

        if new_name:
            old_dir = os.path.dirname(old_path)
            new_path = os.path.join(old_dir, new_name)
        if not new_path:
            return
        result = await center.add_executor_job(rename_image, old_path, new_path)
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
            image.name, path=new_path, values=image.values, **image_attrs
        )

    rename_image_action_schema = BASE_ACTION_SCHEMA.extend(
        {
            vol.Required("sample"): vol.All(vol.Coerce(str), vol.In(center.samples)),
            vol.Required("old_path"): vol.Coerce(str),
            vol.Exclusive("new_path", "new_file"): vol.Coerce(str),
            vol.Exclusive("new_name", "new_file"): vol.Coerce(str),
        }
    )

    center.actions.register(
        "rename_image", ACTION_RENAME_IMAGE, handle_action, rename_image_action_schema,
    )


def rename_image(old_path, new_path):
    """Rename image at old_path to new_path.

    Parameters
    ----------
    old_path : str
        The absolute path to the existing image.
    new_path : str
        The absolute path to the renamed image.

    """
    renamed = False
    if os.path.exists(new_path):
        try:
            os.remove(new_path)
        except OSError as exc:
            _LOGGER.error("Failed to remove existing image: %s", exc)
            return renamed
    try:
        os.rename(old_path, new_path)
        renamed = True
    except FileNotFoundError as exc:
        _LOGGER.error("File not found: %s", exc)
    except OSError as exc:
        _LOGGER.error("Failed to rename image: %s", exc)
    return renamed
