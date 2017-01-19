"""Control the microscope."""
import logging
import os
import re
import time
from collections import defaultdict

from matrixscreener.cam import CAM
from matrixscreener.experiment import attribute_as_str, attributes, glob

from command import camstart_com, del_com
from gain import Gain
from helper import (find_image_path, format_new_name, get_field, get_imgs,
                    get_well, read_csv, rename_imgs, save_histogram, send,
                    write_csv)
from image import make_proj

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


def handle_imgs(path, imdir, job_order, f_job=2, img_save=True,
                histo_save=True):
    """Handle acquired images, do renaming, make max projections."""
    # Get all image paths in well or field, depending on path and
    # job_order variable.
    imgs = get_imgs(path, search='E{}'.format(job_order))
    new_paths = []
    _LOGGER.info('Handling images...')
    for imgp in imgs:
        _LOGGER.debug('IMAGE PATH: %s', imgp)
        new_name = rename_imgs(imgp, f_job)
        _LOGGER.debug('NEW NAME: %s', new_name)
        if new_name:
            new_paths.append(new_name)
    new_dir = os.path.normpath(os.path.join(imdir, 'maxprojs'))
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
                imdir, 'U{}--V{}--C{}.ome.csv'.format(
                    img_attr.U, img_attr.V, c_id)))
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
        self.saved_gains = defaultdict(list)

    def get_csvs(self, img_ref):
        """Find correct csv files and get their base names."""
        # empty lists for keeping csv file base path names
        # and corresponding well names
        fbs = []
        wells = []
        imgp = find_image_path(img_ref, self.args.imaging_dir)
        _LOGGER.debug('IMAGE PATH: %s', imgp)
        img_attr = attributes(imgp)
        if ('X{}--Y{}'.format(img_attr.X, img_attr.Y) ==
                'X01--Y01' and img_attr.c == 31):
            if (self.args.end_63x or
                    'U{}--V{}'.format(img_attr.U, img_attr.V) ==
                    self.args.last_well):
                _LOGGER.debug('Stop scan after gain in well: %s',
                              self.cam.stop_scan())
            wellp = get_well(imgp)
            handle_imgs(wellp, wellp, '02', img_save=False)
            # get all CSVs in well at wellp
            csvs = glob(os.path.join(os.path.normpath(wellp), '*.ome.csv'))
            for csvp in csvs:
                csv_attr = attributes(csvp)
                # Get the filebase from the csv path.
                fbs.append(re.sub(r'C\d\d.+$', '', csvp))
                #  Get the well from the csv path.
                well_name = 'U{}--V{}'.format(csv_attr.U, csv_attr.V)
                wells.append(well_name)
        return {'bases': fbs, 'wells': wells}

    def save_gain(self, saved_gains):
        """Save a csv file with gain values per image channel."""
        header = ['well', 'green', 'blue', 'yellow', 'red']
        path = os.path.normpath(
            os.path.join(self.args.imaging_dir, 'output_gains.csv'))
        write_csv(path, saved_gains, header)

    # #FIXME:20 Function send_com is too complex, trello:S4Df369p
    def send_com(self, gain_dict, gobj, com_list, end_com_list, stage1=None,
                 stage2=None, stage3=None):
        """Send commands to the CAM server."""
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
                    time.sleep(0.02)
                    continue
                for reply in replies:
                    if stage1 and reply.get('relpath'):
                        _LOGGER.info('Stage1')
                        _LOGGER.debug('REPLY: %s', reply)
                        csv_result = self.get_csvs(reply.get('relpath'))
                        gain_dict = gobj.calc_gain(csv_result, gain_dict)
                        _LOGGER.debug('GAIN DICT: %s', gain_dict)
                        self.saved_gains.update(gain_dict)
                        if not self.saved_gains:
                            continue
                        _LOGGER.debug('SAVED_GAINS: %s', self.saved_gains)
                        self.save_gain(self.saved_gains)
                        gain_result = gobj.distribute_gain(gain_dict)
                        com_data = gobj.get_com(self.args.x_fields,
                                                self.args.y_fields,
                                                gain_result)
                    elif reply.get('relpath'):
                        if stage2:
                            _LOGGER.info('Stage2')
                            img_saving = False
                        if stage3:
                            _LOGGER.info('Stage3')
                            img_saving = False
                        imgp = find_image_path(
                            reply['relpath'], self.args.imaging_dir)
                        fieldp = get_field(imgp)
                        handle_imgs(fieldp,
                                    self.args.imaging_dir,
                                    attribute_as_str(imgp, 'E'),
                                    f_job=self.args.first_job,
                                    img_save=img_saving,
                                    histo_save=False)
                    if all(test in reply.get('relpath', [])
                           for test in end_com):
                        stage4 = False
            reply = self.cam.stop_scan()
            _LOGGER.debug('STOP SCAN: %s', reply)
            begin = time.time()
            while not reply or 'scanfinished' not in reply[-1].values():
                reply = self.cam.receive()
                _LOGGER.debug('SCAN FINISHED reply: %s', reply)
                if time.time() - begin > 20.0:
                    break
            time.sleep(1)  # Wait for it to come to complete stop.
            if gain_dict and stage1:
                # Reset gain_dict for each iteration.
                gain_dict = defaultdict(list)
                self.send_com(gain_dict, gobj, com_data['com'],
                              com_data['end_com'], stage1=False, stage2=stage2,
                              stage3=stage3)

    def control(self):
        """Control the flow."""
        # Booleans etc to control flow.
        gain_dict = defaultdict(list)
        stage1 = True
        stage2 = True
        stage3 = False
        if self.args.end_10x:
            pattern_g = PATTERN_G_10X
            job_list = JOB_10X
            pattern = PATTERN_10X
        elif self.args.end_40x:
            pattern_g = PATTERN_G_40X
            job_list = JOB_40X
            pattern = PATTERN_40X
        elif self.args.end_63x:
            stage2 = False
            stage3 = True
            pattern_g = PATTERN_G_63X
            job_list = JOB_63X
            pattern = PATTERN_63X
        if self.args.gain_only:
            stage2 = False
            stage3 = False
        if self.args.input_gain:
            stage1 = False
            gain_dict = read_csv(self.args.input_gain, 'well',
                                 ['green', 'blue', 'yellow', 'red'])

        # make Gain object
        gobj = Gain(self.args, job_list, pattern_g, pattern)

        if self.args.input_gain:
            gain_result = gobj.distribute_gain(gain_dict)
            com_data = gobj.get_com(
                self.args.x_fields, self.args.y_fields, gain_result)
        else:
            com_data = gobj.get_init_com()

        if stage1 or stage2 or stage3:
            self.send_com(gain_dict, gobj, com_data['com'],
                          com_data['end_com'], stage1=stage1, stage2=stage2,
                          stage3=stage3)

        _LOGGER.info('Experiment finished!')
