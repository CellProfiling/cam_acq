"""Control the microscope."""
import logging
import os
import re
import time
from collections import defaultdict

from matrixscreener.cam import CAM
from matrixscreener.experiment import attribute, attributes, glob

from camacq.command import camstart_com, del_com
from camacq.const import (BLUE, END_10X, END_40X, END_63X, FIELD_NAME,
                          GAIN_ONLY, GREEN, INPUT_GAIN, JOB_ID, RED, WELL,
                          WELL_NAME, WELL_NAME_CHANNEL, YELLOW)
from camacq.gain import GainMap
from camacq.helper import (find_image_path, format_new_name, get_field,
                           get_imgs, get_well, read_csv, rename_imgs,
                           save_histogram, send, write_csv)
from camacq.image import make_proj

_LOGGER = logging.getLogger(__name__)

# #RFE:0 Assign job vars by config file, trello:UiavT7yP
# #RFE:10 Assign job vars by parsing the xml/lrp-files, trello:d7eWnJC5
PATTERN_G_10X = 'pattern7'
PATTERN_G_40X = 'pattern8'
PATTERN_G_63X = 'pattern9'
JOB_10X = ['job22', 'job23', 'job24']
PATTERN_10X = 'pattern10'
JOB_40X = ['job7', 'job8', 'job9']
PATTERN_40X = 'pattern2'
JOB_63X = ['job10', 'job11', 'job12']
PATTERN_63X = 'pattern3'
STAGE1_DEFAULT = True
STAGE2_DEFAULT = True
STAGE3_DEFAULT = False
JOB_INFO = 'job_info'
MAX_PROJS = 'maxprojs'
DEFAULT_LAST_FIELD_GAIN = 'X01--Y01'
DEFAULT_LAST_SEQ_GAIN = 31
DEFAULT_JOB_ID_GAIN = 2
REL_IMAGE_PATH = 'relpath'
SCAN_FINISHED = 'scanfinished'
STAGE1 = 'stage1'
STAGE2 = 'stage2'
STAGE3 = 'stage3'


def handle_imgs(path, imdir, job_id, f_job=2, img_save=True,
                histo_save=True):
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
    if not os.path.exists(new_dir):
        os.makedirs(new_dir)
    if img_save:
        _LOGGER.info('Saving images...')
    if histo_save:
        _LOGGER.info('Calculating histograms')
    # Make a max proj per channel.
    for c_id, proj in make_proj(new_paths).iteritems():
        if img_save:
            save_path = format_new_name(proj.path, root=new_dir,
                                        new_attr={'C': c_id})
            # Save meta data and image max proj.
            proj.save(save_path)
        if histo_save:
            img_attr = attributes(proj.path)
            save_path = os.path.normpath(os.path.join(
                imdir, (WELL_NAME_CHANNEL + '.ome.csv').format(
                    img_attr.u, img_attr.v, int(c_id))))
            save_histogram(save_path, proj)


class Control(object):
    """Represent a control center for the microscope."""

    def __init__(self, args):
        """Set up instance."""
        self.args = args
        self.cam = CAM(self.args.host)
        self.cam.delay = 0.2
        # dicts of lists to store wells with gain values for
        # the four channels.
        self.saved_gains = defaultdict(dict)

    def get_csvs(self, img_ref):
        """Find correct csv files and get their base names."""
        # empty lists for keeping csv file base path names
        # and corresponding well names
        fbs = []
        wells = []
        imgp = find_image_path(img_ref, self.args.imaging_dir)
        _LOGGER.debug('IMAGE PATH: %s', imgp)
        img_attr = attributes(imgp)
        # This means only ever one well at a time.
        if (FIELD_NAME.format(img_attr.X, img_attr.Y) ==
                DEFAULT_LAST_FIELD_GAIN and
                img_attr.c == DEFAULT_LAST_SEQ_GAIN):
            if (self.args.end_63x or
                    WELL_NAME.format(img_attr.U, img_attr.V) ==
                    self.args.last_well):
                _LOGGER.debug('Stop scan after gain in well: %s',
                              self.cam.stop_scan())
            wellp = get_well(imgp)
            handle_imgs(wellp, wellp, DEFAULT_JOB_ID_GAIN, img_save=False)
            # get all CSVs in well at wellp
            csvs = glob(os.path.join(os.path.normpath(wellp), '*.ome.csv'))
            for csvp in csvs:
                csv_attr = attributes(csvp)
                # Get the filebase from the csv path.
                fbs.append(re.sub(r'C\d\d.+$', '', csvp))
                #  Get the well from the csv path.
                well_name = WELL_NAME.format(csv_attr.U, csv_attr.V)
                wells.append(well_name)
        return {'bases': fbs, 'wells': wells}

    def save_gain(self, saved_gains):
        """Save a csv file with gain values per image channel."""
        header = [WELL, GREEN, BLUE, YELLOW, RED]
        path = os.path.normpath(
            os.path.join(self.args.imaging_dir, 'output_gains.csv'))
        write_csv(path, saved_gains, header)

    def send_com(self, gain_dict, gmap, com_list, end_com_list, stage1=None,
                 stage2=None, stage3=None):
        """Send commands to the CAM server."""
        # pylint: disable=too-many-arguments, too-many-locals
        # pylint: disable=too-many-branches, too-many-statements
        for com, end_com in zip(com_list, end_com_list):
            # Send CAM list for the gain job to the server during stage1.
            # Send gain change command to server in the four channels
            # during stage2 and stage3.
            # Send CAM list for the experiment jobs to server (stage2/stage3).
            _LOGGER.debug('Delete list: %s', del_com())
            _LOGGER.debug('Delete list reply: %s', self.cam.send(del_com()))
            time.sleep(2)
            send(self.cam, com)
            time.sleep(2)
            # Start scan.
            _LOGGER.debug('Start scan: %s', self.cam.start_scan())
            time.sleep(7)  # Wait for it to change objective and start.
            # Start CAM scan.
            _LOGGER.debug('Start CAM scan: %s', camstart_com())
            _LOGGER.debug('Start CAM scan reply: %s',
                          self.cam.send(camstart_com()))
            _LOGGER.info('Waiting for images...')
            stage4 = True
            while stage4:
                replies = self.cam.receive()
                if replies is None:
                    time.sleep(0.02)  # Short sleep to not burn 100% CPU.
                    continue
                for reply in replies:
                    if stage1 and reply.get(REL_IMAGE_PATH):
                        _LOGGER.info('Stage1')
                        _LOGGER.debug('REPLY: %s', reply)
                        csv_result = self.get_csvs(reply.get(REL_IMAGE_PATH))
                        gain_dict = gmap.calc_gain(csv_result, gain_dict)
                        _LOGGER.debug('GAIN DICT: %s', gain_dict)
                        self.saved_gains.update(gain_dict)
                        if not self.saved_gains:
                            continue
                        _LOGGER.debug('SAVED_GAINS: %s', self.saved_gains)
                        self.save_gain(self.saved_gains)
                        gmap.distribute_gain(gain_dict)
                    elif reply.get(REL_IMAGE_PATH):
                        if stage2:
                            _LOGGER.info('Stage2')
                            img_saving = False
                        if stage3:
                            _LOGGER.info('Stage3')
                            img_saving = False
                        imgp = find_image_path(
                            reply[REL_IMAGE_PATH], self.args.imaging_dir)
                        img_attr = attributes(imgp)
                        well = gmap.wells.get(
                            WELL_NAME.format(img_attr.u, img_attr.v))
                        if not well:
                            continue
                        field = well.fields.get(
                            FIELD_NAME.format(img_attr.x, img_attr.y))
                        if not field:
                            continue
                        well.fields[FIELD_NAME.format(
                            img_attr.x, img_attr.y)] = field._replace(
                                img_ok=True)
                        fieldp = get_field(imgp)
                        handle_imgs(fieldp,
                                    self.args.imaging_dir,
                                    attribute(imgp, 'E'),
                                    f_job=self.args.first_job,
                                    img_save=img_saving,
                                    histo_save=False)
                    if all(test in reply.get(REL_IMAGE_PATH, [])
                           for test in end_com):
                        stage4 = False
            reply = self.cam.stop_scan()
            _LOGGER.debug('STOP SCAN: %s', reply)
            begin = time.time()
            while not reply or SCAN_FINISHED not in reply[-1].values():
                reply = self.cam.receive()
                _LOGGER.debug('SCAN FINISHED reply: %s', reply)
                if time.time() - begin > 20.0:
                    break
            time.sleep(1)  # Wait for it to come to complete stop.
            if gain_dict and stage1:
                com_data = gmap.get_com(self.args.x_fields, self.args.y_fields)
                # Reset gain_dict for each iteration.
                gain_dict = defaultdict(dict)
                self.send_com(gain_dict, gmap, com_data['com'],
                              com_data['end_com'], stage1=False, stage2=stage2,
                              stage3=stage3)

    def control(self):
        """Control the flow."""
        # Booleans etc to control flow.
        stage1 = STAGE1_DEFAULT
        stage2 = STAGE2_DEFAULT
        stage3 = STAGE3_DEFAULT
        gain_dict = defaultdict(dict)
        flow_map = {
            END_10X: {
                JOB_INFO: (JOB_10X, PATTERN_G_10X, PATTERN_10X),
            },
            END_40X: {
                JOB_INFO: (JOB_40X, PATTERN_G_40X, PATTERN_40X),
            },
            END_63X: {
                JOB_INFO: (JOB_63X, PATTERN_G_63X, PATTERN_63X),
                STAGE2: False,
                STAGE3: True,
            },
            GAIN_ONLY: {
                STAGE2: False,
                STAGE3: False,
            },
            INPUT_GAIN: {
                STAGE1: False,
            },
        }
        for attr, settings in flow_map.iteritems():
            if getattr(self.args, attr, None):
                stage1 = settings.get(STAGE1, stage1)
                stage2 = settings.get(STAGE2, stage2)
                stage3 = settings.get(STAGE3, stage3) if not \
                    self.args.gain_only else flow_map[GAIN_ONLY][STAGE3]
                if JOB_INFO in settings:
                    job_info = settings[JOB_INFO]
                if INPUT_GAIN in attr:
                    gain_dict = read_csv(self.args.input_gain, WELL)

        # make Gain object
        gmap = GainMap(self.args, job_info)

        if self.args.input_gain:
            gmap.distribute_gain(gain_dict)
            com_data = gmap.get_com(self.args.x_fields, self.args.y_fields)
        else:
            com_data = gmap.get_init_com()

        if stage1 or stage2 or stage3:
            self.send_com(gain_dict, gmap, com_data['com'],
                          com_data['end_com'], stage1=stage1, stage2=stage2,
                          stage3=stage3)

        _LOGGER.info('Experiment finished!')
