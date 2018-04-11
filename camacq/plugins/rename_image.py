"""Handle renaming of an image."""
import logging
import os

import voluptuous as vol

from camacq.helper import BASE_ACTION_SCHEMA

_LOGGER = logging.getLogger(__name__)
ACTION_RENAME_IMAGE = 'rename_image'
RENAME_IMAGE_ACTION_SCHEMA = BASE_ACTION_SCHEMA.extend({
    vol.Required('old_path'): vol.Coerce(str),
    vol.Required('new_path'): vol.Coerce(str),
})


def setup_module(center, config):
    """Set up image rename plugin.

    Parameters
    ----------
    center : Center instance
        The Center instance.
    config : dict
        The config dict.
    """
    def handle_action(**kwargs):
        """Handle the action call to rename an image.

        Parameters
        ----------
        **kwargs
            Arbitrary keyword arguments. These will be passed to the
            action function when an action is called.
        """
        old_path = kwargs.get('old_path')
        new_path = kwargs.get('new_path')

        rename_image(old_path, new_path)
        image = center.sample.get_image(old_path)
        center.sample.remove_image(old_path)
        center.sample.set_image(
            new_path, image.channel_id, image.field_x, image.field_y,
            image.well_x, image.well_y)

    center.actions.register(
        'plugins.rename_image', ACTION_RENAME_IMAGE, handle_action,
        RENAME_IMAGE_ACTION_SCHEMA)


def rename_image(old_path, new_path):
    """Rename image at old_path to new_path.

    Parameters
    ----------
    old_path : str
        The absolute path to the existing image.
    new_path : str
        The absolute path to the renamed image.

    """
    if os.path.exists(new_path):
        os.remove(new_path)
    os.rename(old_path, new_path)
