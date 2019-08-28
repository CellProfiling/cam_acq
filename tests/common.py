"""Provide common test utils."""
from pathlib import Path

GAIN_DATA_DIR = (Path(__file__).parent / 'fixtures/gain_data').resolve()
WELL_NAME = 'U01--V00'
FULL_WELL_NAME = f'chamber--{WELL_NAME}'
WELL_PATH = Path(GAIN_DATA_DIR) / 'slide' / FULL_WELL_NAME
IMAGE_PATH = (
    Path(WELL_PATH)
    / 'field--X00--Y00/image--U01--V00--E02--X00--Y00--Z00--C00.ome.tif')
