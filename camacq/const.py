"""Store common constants."""


CONFIG_DIR = 'config_dir'
COORD_FILE = 'coord_file'
JOB_ID = '--E{:02d}'
WELL_U_ID = '--U{:02d}'
WELL_V_ID = '--V{:02d}'
FIELD_X_ID = '--X{:02d}'
FIELD_Y_ID = '--Y{:02d}'
CHANNEL_ID = '--C{:02d}'
WELL_NAME = (WELL_U_ID + WELL_V_ID)[2:]
FIELD_NAME = (FIELD_X_ID + FIELD_Y_ID)[2:]
FIRST_JOB = 'first_job'
FOV_NAME = WELL_NAME + '--' + FIELD_NAME
HOST = 'host'
IMAGING_DIR = 'imaging_dir'
INIT_GAIN = 'init_gain'
LAST_FIELD = 'last_field'
LAST_WELL = 'last_well'
LOG_LEVEL = 'log_level'
WELL = 'well'
WELL_NAME_CHANNEL = (WELL_U_ID + WELL_V_ID + CHANNEL_ID)[2:]
GREEN = 'green'
BLUE = 'blue'
YELLOW = 'yellow'
RED = 'red'
GAIN_ONLY = 'gain_only'
INPUT_GAIN = 'input_gain'
END_10X = 'end_10x'
END_40X = 'end_40x'
END_63X = 'end_63x'
TEMPLATE_FILE = 'template_file'
FIELDS_X = 'fields_x'
FIELDS_Y = 'fields_y'
