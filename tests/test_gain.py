"""Test gain calculation."""
import os
import pprint
import re

from matrixscreener.experiment import attributes, glob
from pkg_resources import resource_filename
from pytest import approx

from camacq.config import DEFAULT_CONFIG_TEMPLATE, load_config_file
from camacq.const import IMAGING_DIR, JOB_ID, WELL_NAME, WELL_NAME_CHANNEL
from camacq.helper import get_imgs, save_histogram
from camacq.image import make_proj
from camacq.plugins.gain import calc_gain

GAIN_DATA_DIR = os.path.join(
    os.path.dirname(__file__), '../tests/fixtures/gain_data')
WELL_PATH = os.path.join(GAIN_DATA_DIR, 'slide/chamber--U01--V00')
IMAGE_PATH = os.path.join(
    WELL_PATH,
    'field--X00--Y00/image--U01--V00--E02--X00--Y00--Z00--C00.ome.tif')


def test_gain():
    """Run gain calculation test."""
    default_config_template = resource_filename(
        'camacq', DEFAULT_CONFIG_TEMPLATE)
    config = load_config_file(default_config_template)
    config[IMAGING_DIR] = GAIN_DATA_DIR
    pprint.pprint(config)
    images = get_imgs(WELL_PATH, search=JOB_ID.format(2))
    for c_id, proj in make_proj(images).iteritems():
        img_attr = attributes(proj.path)
        save_path = os.path.normpath(os.path.join(
            WELL_PATH, (WELL_NAME_CHANNEL + '.ome.csv').format(
                img_attr.u, img_attr.v, int(c_id))))
        save_histogram(save_path, proj)
    # get all CSVs in well at wellp
    csvs = glob(os.path.join(os.path.normpath(WELL_PATH), '*.ome.csv'))
    fbs = []
    wells = []
    for csvp in csvs:
        csv_attr = attributes(csvp)
        # Get the filebase from the csv path.
        fbs.append(re.sub(r'C\d\d.+$', '', csvp))
        #  Get the well from the csv path.
        well_name = WELL_NAME.format(csv_attr.u, csv_attr.v)
        wells.append(well_name)
    gain_dict = calc_gain(config, fbs, wells)
    pprint.pprint(gain_dict)
    gain_dict['U01--V00'] = {
        k: int(v) for k, v in gain_dict['U01--V00'].iteritems()}
    solution = {
        'U01--V00': {
            'blue': 480, 'green': 740, 'red': 819, 'yellow': 805}}
    assert gain_dict['U01--V00'] == approx(solution['U01--V00'], abs=10)
