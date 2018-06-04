"""Handle default gain feedback plugin."""
import logging
import os
from builtins import range  # pylint: disable=redefined-builtin
from collections import defaultdict, namedtuple
from itertools import groupby

import matplotlib
import pandas as pd
import voluptuous as vol
from future import standard_library
from scipy.optimize import curve_fit

from camacq.const import CHANNEL_ID, CONF_PLUGINS, WELL, WELL_NAME
from camacq.helper import BASE_ACTION_SCHEMA, write_csv
from camacq.image import make_proj
from camacq.sample import Channel

matplotlib.use('AGG')  # use noninteractive default backend
# pylint: disable=wrong-import-order, wrong-import-position, ungrouped-imports
import matplotlib.pyplot as plt  # noqa: E402

standard_library.install_aliases()

_LOGGER = logging.getLogger(__name__)
BOX = 'box'
COUNT = 'count'
VALID = 'valid'
CONF_CHANNEL = 'channel'
CONF_CHANNELS = 'channels'
CONF_GAIN = 'gain'
CONF_INIT_GAIN = 'init_gain'
COUNT_CLOSE_TO_ZERO = 2
SAVED_GAINS = 'saved_gains'

ACTION_CALC_GAIN = 'calc_gain'
CALC_GAIN_ACTION_SCHEMA = BASE_ACTION_SCHEMA.extend({
    vol.Required('well_x'): vol.Coerce(int),
    vol.Required('well_y'): vol.Coerce(int),
    vol.Required('plate_name'): vol.Coerce(str),
    'images': [vol.Coerce(str)],
    # pylint: disable=no-value-for-parameter
    vol.Optional('make_plots', default=False): vol.Boolean(),
    vol.Optional('save_path', default=''): vol.Coerce(str),
})

GAIN = 'gain'
Data = namedtuple('Data', [BOX, GAIN, VALID])  # pylint: disable=invalid-name


def setup_module(center, config):
    """Set up gain calculation plugin."""
    def handle_calc_gain(**kwargs):
        """Handle call to calc_gain action."""
        well_x = kwargs.get('well_x')
        well_y = kwargs.get('well_y')
        plate_name = kwargs.get('plate_name')
        paths = kwargs.get('images')  # list of paths to calculate gain for
        if not paths:
            well = center.sample.get_well(plate_name, well_x, well_y)
            if not well:
                return
            images = {
                image.channel_id: path for path, image in well.images.items()}
        else:
            images = {
                image.channel_id: path
                for path, image in center.sample.images.items()
                if path in paths}
        plot = kwargs.get('make_plots')
        save_path = kwargs.get('save_path')  # path to save plots
        projs = make_proj(images)
        calc_gain(center, plate_name, well_x, well_y, projs, plot, save_path)

    center.actions.register(
        'plugins.gain', ACTION_CALC_GAIN, handle_calc_gain,
        CALC_GAIN_ACTION_SCHEMA)


def calc_gain(
        center, plate_name, well_x, well_y, projs, plot=True, save_path=''):
    """Calculate gain values for the well."""
    # pylint: disable=too-many-arguments
    gain_conf = center.config[CONF_PLUGINS][CONF_GAIN]
    if CONF_CHANNELS not in gain_conf:
        _LOGGER.error(
            'Missing config section %s in %s:%s',
            CONF_CHANNELS, CONF_PLUGINS, CONF_GAIN)
        return
    init_gain = [
        Channel(channel[CONF_CHANNEL], gain=gain)
        for channel in gain_conf[CONF_CHANNELS]
        for gain in channel[CONF_INIT_GAIN]]

    gains = _calc_gain(projs, init_gain, plot=plot, save_path=save_path)
    _LOGGER.info('Calculated gains: %s', gains)
    if SAVED_GAINS not in center.data:
        center.data[SAVED_GAINS] = defaultdict(dict)
    center.data[SAVED_GAINS].update({WELL_NAME.format(well_x, well_y): gains})
    _LOGGER.debug('All calculated gains: %s', center.data[SAVED_GAINS])
    if plot:
        save_dir = gain_conf.get('save_dir', '/temp')
        save_gain(save_dir, center.data[SAVED_GAINS], [WELL] + list(gains))
    well = center.sample.get_well(plate_name, well_x, well_y)
    if well:
        # Set existing channel gain to generate event.
        for channel_name, channel in well.channels.items():
            center.sample.set_channel(
                plate_name, well_x, well_y, channel_name, overwrite=True,
                gain=channel.gain)
    # Set new channel gain, only if not existing.
    for channel_name, gain in gains.items():
        center.sample.set_channel(
            plate_name, well_x, well_y, channel_name, gain=gain)


def _power_func(inp, alpha, beta):
    """Return the value of function of inp, alpha and beta."""
    return alpha * inp**beta


def _check_upward(points):
    """Return a function that checks if points move upward."""
    def wrapped(point):
        """Return True if trend is upward.

        The calculation is done for a point with neighbouring points.
        """
        idx, item = point
        valid = item.valid and item.box <= 600
        prev = next_ = True
        if idx > 0:
            prev = item.box >= points[idx - 1].box
        if idx < len(points) - 1:
            next_ = item.box <= points[idx + 1].box
        return valid and (prev or next_)
    return wrapped


def _create_plot(path, x_data, y_data, coeffs, label):
    """Plot and save plot to path."""
    plt.ioff()
    plt.clf()
    plt.yscale('log')
    plt.xscale('log')
    plt.plot(
        x_data, y_data, 'bo',
        x_data, _power_func(x_data, *coeffs), 'g-', label=label)
    plt.savefig(path)


def _calc_gain(projs, init_gain, plot=True, save_path=''):
    """Calculate gain values for the well.

    Do the actual math.
    """
    # pylint: disable=too-many-locals
    box_vs_gain = {}

    for c_id, proj in projs.items():
        channel = init_gain[c_id]
        if channel.name not in box_vs_gain:
            box_vs_gain[channel.name] = []
        hist_data = pd.DataFrame({
            BOX: list(range(len(proj.histogram[0]))),
            COUNT: proj.histogram[0]})
        # Handle all zero pixels
        non_zero_hist_data = hist_data[
            (hist_data[COUNT] > 0) & (hist_data[BOX] > 0)]
        if non_zero_hist_data.empty:
            continue
        # Find the max box holding pixels
        box_max_count = non_zero_hist_data[BOX].iloc[-1]
        # Select only histo data where count is > 0 and 255 > box > 0.
        # Only use values in interval 10-100 and
        # > (max box holding pixels - 175).
        roi = hist_data[
            (hist_data[COUNT] > 0) & (hist_data[BOX] > 0) &
            (hist_data[BOX] < 255) & (hist_data[COUNT] >= 10) &
            (hist_data[COUNT] <= 100) &
            (hist_data[BOX] > (box_max_count - 175))]
        if roi.shape[0] < 3:
            continue
        x_data = roi[COUNT].astype(float).values
        y_data = roi[BOX].astype(float).values
        coeffs, _ = curve_fit(_power_func, x_data, y_data, p0=(1000, -1))
        if plot:
            _save_path = '{}{}.ome.png'.format(
                save_path, CHANNEL_ID.format(c_id))
            _create_plot(
                _save_path, hist_data[COUNT], hist_data[BOX], coeffs,
                'count-box')
        # Find box value where count is close to zero.
        # Store that box value and it's corresponding gain value.
        # Store boolean saying if second slope coefficient is negative.
        box_vs_gain[channel.name].append(Data._make((
            _power_func(COUNT_CLOSE_TO_ZERO, *coeffs),
            channel.gain, coeffs[1] < 0)))

    gains = {}
    for channel, points in box_vs_gain.items():
        # Sort points with ascending gain, to allow grouping.
        points = sorted(points, key=lambda item: item.gain)
        long_group = []
        for key, group in groupby(enumerate(points), _check_upward(points)):
            # Find the group with the most points and use that below.
            stored_group = list(group)
            if key and len(stored_group) > len(long_group):
                long_group = stored_group

        # Curve fit the longest group with power function.
        # Plot the points and the fit.
        # Return the calculated gains at bin 255, using fit function.
        if len(long_group) < 3:
            gains[channel] = None
            continue
        coeffs, _ = curve_fit(
            _power_func, [p[1].box for p in long_group],
            [p[1].gain for p in long_group], p0=(1, 1))
        if plot:
            _save_path = '{}_{}.png'.format(save_path, channel)
            _create_plot(
                _save_path, [p.box for p in points],
                [p.gain for p in points], coeffs, 'box-gain')
        gains[channel] = _power_func(255, *coeffs)

    return gains


def save_gain(save_dir, saved_gains, header):
    """Save a csv file with gain values per image channel."""
    path = os.path.normpath(
        os.path.join(save_dir, 'output_gains.csv'))
    write_csv(path, saved_gains, header)
