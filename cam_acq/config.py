import logging
import yaml

_LOGGER = logging.getLogger(__name__)


def load_config_file(path):
    """ Parse a YAML configuration file. """
    try:
        with open(path, 'r') as yml_file:
            cfg = yaml.safe_load(yml_file)
        if not isinstance(cfg, dict):
            _LOGGER.error(
                'The configuration file %s does not contain a dictionary',
                os.path.basename(path))
            raise TypeError()  # or let it pass?
        return cfg
    except yaml.YAMLError:
        error = 'Error reading YAML configuration file {}'.format(path)
        _LOGGER.exception(error)
        raise yaml.YAMLError(error)  # or let it pass?

# for section in load_config_file('config.yml'):
#    print(section)
# print(cfg['logging'])
# print(cfg['other'])
