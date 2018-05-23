"""Helper functions for camacq."""
import csv
import logging
import ntpath
import os
import re
from collections import defaultdict

from matrixscreener import experiment

from camacq.const import (BLUE, FIELD_NAME, GREEN, IMAGING_DIR, JOB_ID, RED,
                          WELL, WELL_NAME, WELL_NAME_CHANNEL, YELLOW)
from camacq.image import make_proj

_LOGGER = logging.getLogger(__name__)
DEFAULT_JOB_ID_GAIN = 2
DEFAULT_LAST_SEQ_GAIN = 31
MAX_PROJS = 'maxprojs'


def send(cam, commands):
    """Send each command in commands.

    Parameters
    ----------
    cam : instance
        CAM instance.
    commands : list
        List of list of commands as tuples.

    Returns
    -------
    list
        Return a list of OrderedDict with all received replies.

    Example
    -------
    ::

        send(cam, [[('cmd', 'deletelist')], [('cmd', 'startscan')]])
    """
    replies = []
    for cmd in commands:
        _LOGGER.debug('sending: %s', cmd)
        reply = cam.send(cmd)
        _LOGGER.debug('receiving: %s', reply)
        if reply:
            replies.extend(reply)
    return replies


def read_csv(path, index):
    """Read a csv file and return a dict of dicts.

    Parameters
    ----------
    path : str
        Path to csv file.
    index : str
        Index can be any of the column headers of the csv file.
        The column under index will be used as keys in the returned
        dict.

    Returns
    -------
    defaultdict(dict)
        Return a dict of dicts with the contents of the csv file,
        indicated by the index parameter. Each item in the
        dict will represent a row, with index as key, of the csv file.
    """
    csv_map = defaultdict(dict)
    with open(path) as file_handle:
        reader = csv.DictReader(file_handle)
        for row in reader:
            key = row.pop(index)
            csv_map[key].update(row)
    return csv_map


def write_csv(path, csv_map, header):
    """Write a dict of dicts as a csv file.

    Parameters
    ----------
    path : str
        Path to csv file.
    csv_map : dict(dict)
        The dict of dicts that should be written as a csv file.
    header : list
        List of strings with the wanted column headers of the csv file.
        The items in header should correspond to the index key of the primary
        dict and all the keys of the secondary dict.
    """
    with open(path, 'wb') as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=header)
        writer.writeheader()
        for index, cells in csv_map.iteritems():
            index_dict = {header[0]: index}
            index_dict.update(cells)
            writer.writerow(index_dict)


def find_image_path(relpath, root):
    """Parse the relpath from the server to find the file path from root.

    Convert from windows path to os path.
    """
    if not relpath:
        return
    paths = []
    while relpath:
        relpath, tail = ntpath.split(relpath)
        paths.append(tail)
    return str(os.path.join(root, *list(reversed(paths))))


def format_new_name(imgp, root=None, new_attr=None):
    """Create filename from image path and replace specific attribute id(s).

    Parameters
    ----------
    imgp : string
        Path to image.
    root : str
        Path to directory where path should start.
    new_attr : dict
        Dictionary which maps experiment attributes to new attribute ids.
        The new attribute ids will replace the old ids for the corresponding
        attributes.

    Returns
    -------
    str
        Return new path to image.
    """
    if root is None:
        root = get_field(imgp)

    path = 'U{}--V{}--E{}--X{}--Y{}--Z{}--C{}.ome.tif'.format(
        *(experiment.attribute_as_str(imgp, attr)
          for attr in ('U', 'V', 'E', 'X', 'Y', 'Z', 'C')))
    if new_attr:
        for attr, attr_id in new_attr.iteritems():
            path = re.sub(attr + r'\d\d', attr + attr_id, path)

    return os.path.normpath(os.path.join(root, path))


def rename_imgs(imgp, f_job):
    """Rename image and return new name."""
    if experiment.attribute(imgp, 'E') == f_job:
        new_name = format_new_name(imgp)
    elif (experiment.attribute(imgp, 'E') == f_job + 1 and
          experiment.attribute(imgp, 'C') == 0):
        new_name = format_new_name(imgp, new_attr={'C': '01'})
    elif (experiment.attribute(imgp, 'E') == f_job + 1 and
          experiment.attribute(imgp, 'C') == 1):
        new_name = format_new_name(imgp, new_attr={'C': '02'})
    elif experiment.attribute(imgp, 'E') == f_job + 2:
        new_name = format_new_name(imgp, new_attr={'C': '03'})
    else:
        return None
    os.rename(imgp, new_name)
    return new_name


def get_field(path):
    """Get path to well from image path."""
    return experiment.Experiment(path).dirname  # pylint: disable=no-member


def get_well(path):
    """Get path to well from image path."""
    # pylint: disable=no-member
    return experiment.Experiment(get_field(path)).dirname


def get_imgs(path, img_type='tif', search=''):
    """Get all images below path."""
    if search:
        search = '{}*'.format(search)
    patterns = [
        'slide',
        'chamber',
        'field',
        'image',
    ]
    for pattern in patterns:
        if pattern not in path:
            path = os.path.join(path, '{}--*'.format(pattern))
    return experiment.glob('{}{}.{}'.format(path, search, img_type))


def save_gain(save_dir, saved_gains):
    """Save a csv file with gain values per image channel."""
    header = [WELL, GREEN, BLUE, YELLOW, RED]
    path = os.path.normpath(
        os.path.join(save_dir, 'output_gains.csv'))
    write_csv(path, saved_gains, header)


def save_histogram(path, image):
    """Save the histogram of an image to path."""
    rows = {box: {'count': count}
            for box, count in enumerate(image.histogram[0])}
    write_csv(path, rows, ['bin', 'count'])


def handle_imgs(path, imdir, job_id, f_job=2, img_save=True, histo_save=True):
    """Handle acquired images, do renaming, make max projections."""
    # pylint: disable=too-many-arguments
    # Get all image paths in well or field, depending on path and
    # job_id variable.
    imgs = get_imgs(path, search=JOB_ID.format(job_id))
    new_paths = []
    _LOGGER.info('Handling images...')
    for imgp in imgs:
        _LOGGER.debug('IMAGE PATH: %s', imgp)
        new_name = rename_imgs(imgp, f_job)
        _LOGGER.debug('NEW NAME: %s', new_name)
        if new_name:
            new_paths.append(new_name)
    if not new_paths or not img_save and not histo_save:
        return
    new_dir = os.path.normpath(os.path.join(imdir, MAX_PROJS))
    if img_save and not os.path.exists(new_dir):
        os.makedirs(new_dir)
    if img_save:
        _LOGGER.info('Saving images...')
    if histo_save:
        _LOGGER.info('Calculating histograms...')
    # Make a max proj per channel.
    for c_id, proj in make_proj(new_paths).iteritems():
        if img_save:
            save_path = format_new_name(proj.path, root=new_dir,
                                        new_attr={'C': c_id})
            # Save meta data and image max proj.
            proj.save(save_path)
        if histo_save:
            img_attr = experiment.attributes(new_paths[-1])
            save_path = os.path.normpath(os.path.join(
                imdir, (WELL_NAME_CHANNEL + '.ome.csv').format(
                    img_attr.u, img_attr.v, int(c_id))))
            save_histogram(save_path, proj)


def get_csvs(event):
    """Find correct csv files and get their base names."""
    # empty lists for keeping csv file base path names
    # and corresponding well names
    fbs = []
    wells = []
    imgp = find_image_path(event.rel_path, event.center.config[IMAGING_DIR])
    if not imgp:
        return fbs, wells
    _LOGGER.debug('IMAGE PATH: %s', imgp)
    img_attr = experiment.attributes(imgp)
    # This means only ever one well at a time.
    well_name = WELL_NAME.format(img_attr.u, img_attr.v)
    well = event.center.gains.wells.get(well_name)
    last_gain_field = next(
        (field_name for field_name in reversed(sorted(well.fields.iterkeys()))
         if well.fields[field_name].gain_field), None)
    if (FIELD_NAME.format(img_attr.x, img_attr.y) ==
            last_gain_field and
            img_attr.c == DEFAULT_LAST_SEQ_GAIN):
        wellp = get_well(imgp)
        handle_imgs(wellp, wellp, DEFAULT_JOB_ID_GAIN, img_save=False)
        # get all CSVs in well at wellp
        csvs = experiment.glob(
            os.path.join(os.path.normpath(wellp), '*.ome.csv'))
        for csvp in csvs:
            csv_attr = experiment.attributes(csvp)
            # Get the filebase from the csv path.
            fbs.append(re.sub(r'C\d\d.+$', '', csvp))
            #  Get the well from the csv path.
            well_name = WELL_NAME.format(csv_attr.u, csv_attr.v)
            wells.append(well_name)
    return fbs, wells
