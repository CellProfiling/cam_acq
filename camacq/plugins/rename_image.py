"""Handle renaming of an image."""
import logging
import os

from matrixscreener.experiment import attribute

from camacq.api.leica.helper import format_new_name

_LOGGER = logging.getLogger(__name__)
ACTION_RENAME_IMAGE = 'rename_image'


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
        path = kwargs.get('path')
        first_job_id = kwargs.get('first_job_id')
        new_name = rename_image(path, first_job_id)

        if new_name:
            image = center.sample.get_image(path)
            center.sample.remove_image(path)
            center.sample.set_image(
                new_name, image.channel_id, image.field_x, image.field_y,
                image.well_x, image.well_y)

    center.actions.register(__name__, ACTION_RENAME_IMAGE, handle_action)


def rename_image(path, first_job_id):
    """Rename image at path and return new path to image.

    Renaming is done according to a specific pattern.

    Parameters
    ----------
    path : str
        The absolute path to the image.
    first_job_id : int
        An integer specifying the id of the first job of a group of
        jobs that acquire the images for the experiment.

    Returns
    -------
    str
        Return the new path to the renamed image.
    """
    _LOGGER.debug('Image path: %s', path)
    image_name = os.path.basename(path)
    if not image_name.startswith('image'):
        return None
    if attribute(path, 'E') == first_job_id:
        new_name = format_new_name(path)
    elif (attribute(path, 'E') == first_job_id + 1 and
          attribute(path, 'C') == 0):
        new_name = format_new_name(path, new_attr={'C': '01'})
    elif (attribute(path, 'E') == first_job_id + 1 and
          attribute(path, 'C') == 1):
        new_name = format_new_name(path, new_attr={'C': '02'})
    elif attribute(path, 'E') == first_job_id + 2:
        new_name = format_new_name(path, new_attr={'C': '03'})
    else:
        return None
    if os.path.exists(new_name):
        os.remove(new_name)
    os.rename(path, new_name)
    _LOGGER.debug('New image path: %s', new_name)
    return new_name
