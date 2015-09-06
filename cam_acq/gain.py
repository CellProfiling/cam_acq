from collections import OrderedDict
from collections import defaultdict
import numpy as np


class Gain(object):

    """Gain class

    Attributes:
        gain_dict: A defaultdict of lists where the keys are the wells and each
        list (value) contains the gain values of the (four) channels.
    """

    def __init__(self, gain_dict, imaging_dir, init_gain, r_script,
                 end_63x=None, template=None):
        self.gain_dict = gain_dict
        self.imaging_dir = imaging_dir
        self.init_gain = init_gain
        self.r_script = r_script
        self.end_63x = end_63x
        self.template = template

    def process_output(well, output, dict_list):
        """Function to process output from the R scripts."""
        for c in output.split():
            dict_list[well].append(c)
        return dict_list

    def calc_gain(self, filebases, fin_wells):
        """Function to run R scripts and calculate gain values for
        the wells."""
        # Get a unique set of filebases from the csv paths.
        filebases = sorted(set(filebases))
        # Get a unique set of names of the experiment wells.
        fin_wells = sorted(set(fin_wells))
        for fbase, well in zip(filebases, fin_wells):
            print(well)
            try:
                print('Starting R...')
                r_output = subprocess.check_output(['Rscript',
                                                    self.r_script,
                                                    self.imaging_dir,
                                                    fbase,
                                                    self.init_gain
                                                    ])
                self.gain_dict = process_output(well, r_output, self.gain_dict)
            except OSError as e:
                print('Execution failed:', e)
                sys.exit()
            except subprocess.CalledProcessError as e:
                print('Subprocess returned a non-zero exit status:', e)
                sys.exit()
            print(r_output)
        return self.gain_dict

    def distribute_gain(self):
        """Function to collate gain values and distribute them to the wells as
           to efficiently be able to scan all the wells."""
        green_sorted = defaultdict(list)
        medians = defaultdict(int)
        for i, c in enumerate(['green', 'blue', 'yellow', 'red']):
            mlist = []
            for k, v in self.gain_dict.iteritems():
                # Sort gain data into a list dict with green gain as key
                # and where the value is a list of well ids.
                if c == 'green':
                    # Round gain values to multiples of 10 in green channel
                    if self.end_63x:
                        green_val = int(min(round(int(v[i]), -1), 800))
                    else:
                        green_val = int(round(int(v[i]), -1))
                    if self.template:
                        for well in self.template[k]:
                            green_sorted[green_val].append(well)
                    else:
                        green_sorted[green_val].append(k)
                else:
                    # Find the median value of all gains in
                    # blue, yellow and red channels.
                    mlist.append(int(v[i]))
                    medians[c] = int(np.median(mlist))
        return {'green_sorted': green_sorted, 'medians': medians}

    def set_gain(self, com, channels, job_list):
        for i, c in enumerate(channels):
            gain = str(c)
            if i < 2:
                detector = '1'
                job = job_list[i]
            if i >= 2:
                detector = '2'
                job = job_list[i - 1]
            com.gain_com(exp=job, num=detector, value=gain) + '\n'
        return com
