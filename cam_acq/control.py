import argparse
import os
import re
import socket
import subprocess
from pkg_resources import resource_string
from socket_client import Client
from command import Command


# FIXME: Get list item instead of string from the return of functions in
# the classes in the image.py module.
class Control(object):

    def __init__(self):
        self.imaging_dir = None
        self.working_dir = None
        self.init_gain = None
        self.last_well = None
        self.last_field = None
        self.coord_file = None
        self.host = None
        self.input_gain = None
        self.template_file = None
        self.template = None
        self.end_10x = None
        self.end_40x = None
        self.end_63x = None
        self.first_job = None
        self.gain_only = None
        self.r_script = resource_string(__name__, 'gain.r')
        # Create socket
        self.sock = Client()
        # Port number
        port = 8895
        self.stop_com = Command().stop_com()
        self.pattern = None
        self.pattern_g = None
        self.job_list = None
        self.coords = None

        # Job and pattern variables and names
        af_job_10x = 'af10xcam'
        afr_10x = '200'
        afs_10x = '41'
        af_job_40x = 'af40x'
        afr_40x = '105'
        afs_40x = '106'
        af_job_63x = 'af63x'
        afr_63x = '50'
        afs_63x = '51'
        g_job_10x = 'gain10x'
        g_job_40x = 'gain40x'
        g_job_63x = 'gain63x'
        pattern_g_10x = 'pattern7'
        pattern_g_40x = 'pattern8'
        pattern_g_63x = 'pattern9'
        job_10x = ['job22', 'job23', 'job24']
        pattern_10x = 'pattern10'
        job_40x = ['job7', 'job8', 'job9']
        pattern_40x = 'pattern2'
        job_63x = ['job10', 'job11', 'job12']
        pattern_63x = 'pattern3'
        job_dummy_10x = 'dummy10x'
        pattern_dummy_10x = 'pdummy10x'
        pattern_dummy_40x = 'pdummy40x'

    def check_dir_arg(self, path):
        # remove if not needed
        try:
            os.path.isdir(path)
        except:
            raise ArgumentTypeError(
                'String {} is not a path to a directory'.format(path))

    def check_file_arg(self, path):
        # remove if not needed
        try:
            os.path.isfile(path)
        except:
            raise ArgumentTypeError(
                'String {} is not a path to a file'.format(path))

    def check_field_well_arg(self, v):
        try:
            return re.match("^U\d\d--V\d\d$", v).group(0)
        except:
            raise ArgumentTypeError(
                'String {} does not match required format'.format(v))

    def check_ip_arg(self, addr):
        try:
            socket.inet_aton(addr)
            # legal
        except socket.error:
            # not legal
            raise ArgumentTypeError(
                'String {} is not a valid ip address'.format(addr))

    def parse_command_line(self, argv):
        """Parse the provided command line."""
        parser = argparse.ArgumentParser(
            description='Control a Leica microscope through CAM interface.')
        parser.add_argument(
            'i',
            'image-dir',
            dest='imaging_dir',
            type=dir,
            help='the path to the directory where images are exported')
        parser.add_argument(
            # TODO: Replace this with resource api call for all data files
            # instead of looking in the working dir.
            # foo_config = resource_string(__name__, 'foo.conf')
            '-w',
            '--working-dir',
            dest='working_dir',
            type=dir,
            default=os.path.dirname(os.path.abspath(__file__)),
            help='the path to the working directory of this program')
        parser.add_argument(
            '-g',
            '--init-gain',
            dest='init_gain',
            type=file,
            help='the path to the csv file with start gain values')
        parser.add_argument(
            '-W',
            '--last-well',
            dest='last_well',
            type=check_field_well_arg,
            default='U11--V07',
            help='the id of the last well in the experiment, e.g. U11--V07')
        parser.add_argument(
            '-F',
            '--last-field',
            dest='last_field',
            type=check_field_well_arg,
            default='X01--Y01',
            help='the id of the last field in each well, e.g. X01--Y01')
        parser.add_argument(
            '-c',
            '--coord-file',
            dest='coord_file',
            type=file,
            help='the path to the csv file with selected coordinates')
        parser.add_argument(
            'H',
            'host',
            type=check_ip_arg,
            help='the ip address of the host server, i.e. the microscope')
        args = parser.parse_args(argv[1:])
        if args.imaging_dir:
            self.imaging_dir = os.path.normpath(args.imaging_dir)
        if args.working_dir:
            self.working_dir = os.path.normpath(args.working_dir)
        if args.init_gain is None:
            self.init_gain = os.path.normpath(
                os.path.join(working_dir, '10x_gain.csv'))
        else:
            self.init_gain = os.path.normpath(args.init_gain)
        if args.coord_file:
            self.coord_file = os.path.normpath(args.coord_file)
        print(self.imaging_dir)
        # FIXME: Finish adding arguments

    def parse_reply(self, reply, root):
        """Function to parse the reply from the server to find the
        correct file path."""
        reply = reply.replace('/relpath:', '')
        paths = reply.split('\\')
        for path in paths:
            root = os.path.join(root, path)
        return root

    # FIXME: Add send_com and get_csvs functions.

    def gen_csvs(self, line, gain_dict):
        # empty lists for keeping csv file base path names
        # and corresponding well names
        filebases = []
        fin_wells = []
        # Parse reply, check well (UV), field (XY).
        # Get well path.
        # Get all image paths in well.
        # Make a max proj per channel and well.
        # Save meta data and image max proj.
        if 'image' in line:
            root = parse_reply(line, self.imaging_dir)
            img = File(root)
            img_name = img.get_name('image--.*.tif')
            field_name = img.get_name('X\d\d--Y\d\d')
            channel = img.get_name('C\d\d')
            field_path = img.get_dir()
            well_path = Directory(field_path).get_dir()
            if (field_name == self.last_field and channel == 'C31'):
                if self.end_63x:
                    self.sock.send(stop_com)
                ptime = time.time()
                get_imgs(well_path,
                         well_path,
                         'E02',
                         img_save=False
                         )
                print(str(time.time() - ptime) + ' secs')
                # get all CSVs and wells
                csv_result = get_csvs(well_path,
                                      filebases,
                                      fin_wells,
                                      )
                filebases = csv_result['bases']
                fin_wells = csv_result['wells']
        return {'filebases': filebases, 'fin_wells': fin_wells}

    def gen_com(self, green_sorted, medians):
        dx = 0
        dy = 0
        # Lists for storing command strings.
        com_list = []
        end_com_list = []
        for gain, wells in green_sorted.iteritems():
            com = Command()
            end_com = []
            channels = [gain,
                        medians['blue'],
                        medians['yellow'],
                        medians['red']
                        ]
            com = set_gain(com, channels, self.job_list)
            if self.coords is None:
                self.coords = {}
            for well in sorted(wells):
                for i in range(2):
                    for j in range(2):
                        # Only add selected fovs from file (arg) to cam list
                        fov = '{}--X0{}--Y0{}'.format(well, j, i)
                        if fov in self.coords.keys():
                            dx = self.coords[fov][0]
                            dy = self.coords[fov][1]
                            fov_is = True
                        elif not self.coords:
                            fov_is = True
                        else:
                            fov_is = False
                        if fov_is:
                            com.cam_com(self.pattern,
                                        well,
                                        'X0{}--Y0{}'.format(j, i),
                                        dx,
                                        dy
                                        )
                            end_com = ['CAM',
                                       well,
                                       'E0' + str(self.first_job + 2),
                                       'X0{}--Y0{}'.format(j, i)
                                       ]
            # Store the commands in lists.
            com_list.append(com.com)
            end_com_list.append(end_com)
        return {'com': com_list, 'end_com': end_com_list}

    def main(self, argv):
        """Main function"""

        # Parse command line arguments
        parse_command_line(argv)

        # Booleans etc to control flow.
        stage1 = True
        stage3 = True
        stage4 = False
        stage5 = False
        if self.end_10x:
            self.end_40x = False
            self.end_63x = False
            self.pattern_g = pattern_g_10x
            self.job_list = job_10x
            self.pattern = pattern_10x
        elif self.end_40x:
            self.end_10x = False
            self.end_63x = False
            self.pattern_g = pattern_g_40x
            self.job_list = job_40x
            self.pattern = pattern_40x
        if self.coord_file:
            self.end_63x = True
            self.coords = read_csv(self.coord_file, 'fov', ['dxPx', 'dyPx'])
        if self.end_63x:
            self.end_10x = False
            self.end_40x = False
            stage3 = False
            stage4 = True
            self.pattern_g = pattern_g_63x
            self.job_list = job_63x
            self.pattern = pattern_63x
        if self.gain_only:
            stage3 = False
            stage4 = False
        if self.input_gain:
            stage1 = False
        # Get wells for imaging, either from template file or default plate
        wells = []
        if self.template_file:
            self.template = read_csv(
                self.template_file, 'gain_from_well', ['well'])
            self.last_well = sorted(self.template.keys())[-1]
            # Selected wells from template file.
            wells = sorted(self.template.keys())
        else:
            # All wells.
            for u in range(int(com.get_wfx(self.last_well))):
                for v in range(int(com.get_wfy(self.last_well))):
                    wells.append('U0' + str(u) + '--V0' + str(v))
        # Lists and strings for storing command strings.
        com_list = []
        end_com_list = []
        com = Command()
        end_com = []
        # Selected objective gain job cam command in wells.
        for well in wells:
            for i in range(2):
                com.cam_com(self.pattern_g,
                            well,
                            'X0{}--Y0{}'.format(i, i),
                            '0',
                            '0'
                            )
                end_com = ['CAM',
                           well,
                           'E0' + str(2),
                           'X0{}--Y0{}'.format(i, i)
                           ]
            com_list.append(com.com)
            end_com_list.append(end_com)
            com = Command()
        # Concatenate commands to one string if dry objective
        if self.end_10x or self.end_40x:
            com.com = ''.join(com_list)
            com_list = []
            com_list.append(com.com)
            end_com_list = []
            end_com_list.append(end_com)
        # Connect to server
        self.sock.connect(host, port)
        # FIXME: Finish main function
