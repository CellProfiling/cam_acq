"""Handle renaming of an image."""
import logging
import os

import voluptuous as vol

from camacq.helper import BASE_ACTION_SCHEMA

_LOGGER = logging.getLogger(__name__)
ACTION_RENAME_IMAGE = 'rename_image'
RENAME_IMAGE_ACTION_SCHEMA = BASE_ACTION_SCHEMA.extend({
    vol.Required('old_path'): vol.Coerce(str),
    vol.Exclusive('new_path', 'new_file'): vol.Coerce(str),
    vol.Exclusive('new_name', 'new_file'): vol.Coerce(str),
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
        new_name = kwargs.get('new_name')

        rename_image(old_path, new_path=new_path, new_name=new_name)
        image = center.sample.get_image(old_path)
        center.sample.remove_image(old_path)
        center.sample.set_image(
            new_path, image.channel_id, image.field_x, image.field_y,
            image.well_x, image.well_y)

    center.actions.register(
        'plugins.rename_image', ACTION_RENAME_IMAGE, handle_action,
        RENAME_IMAGE_ACTION_SCHEMA)


def rename_image(old_path, new_path=None, new_name=None):
    """Rename image at old_path to new_path.

    Parameters
    ----------
    old_path : str
        The absolute path to the existing image.
    new_path : str
        The absolute path to the renamed image.
    new_name : str
        The file name (basename) of the renamed image in the old directory.

    """
    if new_name:
        old_dir = os.path.dirname(old_path)
        new_path = os.path.join(old_dir, new_name)
    if os.path.exists(new_path):
        try:
            os.remove(new_path)
        except OSError as exc:
            _LOGGER.error('Failed to remove existing image: %s', exc)
    try:
        os.rename(old_path, new_path)
    except FileNotFoundError as exc:
        _LOGGER.error('File not found: %s', exc)
