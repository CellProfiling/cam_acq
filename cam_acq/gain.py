import subprocess
from collections import OrderedDict
from collections import defaultdict
import numpy as np

def calc_gain(wells,
              fbs,
              first_std_fbs,
              sec_std_fbs,
              first_gain_d,
              sec_gain_d,
              imaging_dir,
              first_r_script,
              sec_r_script,
              first_initialgains_file,
              sec_initialgains_file
              ):
    """Function to run R scripts and calculate gain values for the wells."""

    # Get a unique set of fbs from the csv paths.
    fbs = sorted(set(fbs))
    first_std_fbs = sorted(set(first_std_fbs))
    sec_std_fbs = sorted(set(sec_std_fbs))
    # Get a unique set of names of the experiment wells.
    wells = sorted(set(wells))
    for well, fbase in zip(wells, fbs):
        print(well)
        try:
            print('Starting R...')
            r_output = subprocess.check_output(['Rscript',
                                                first_r_script,
                                                imaging_dir,
                                                fbase,
                                                first_initialgains_file
                                                ])
            first_gain_d = process_output(well, r_output, first_gain_d)
            input_gains = r_output
            r_output = subprocess.check_output(['Rscript',
                                                sec_r_script,
                                                imaging_dir,
                                                first_std_fbs[0],
                                                first_initialgains_file,
                                                input_gains,
                                                imaging_dir,
                                                sec_std_fbs[0],
                                                sec_initialgains_file
                                                ])
        except OSError as e:
            print('Execution failed:', e)
            sys.exit()
        except subprocess.CalledProcessError as e:
            print('Subprocess returned a non-zero exit status:', e)
            sys.exit()
        print(r_output)
        sec_gain_d = process_output(well, r_output, sec_gain_d)

    return (first_gain_d, sec_gain_d)

def distribute_gain(sec_gain_d):
    """Function to collate gain values and distribute them to the wells as to
    efficiently be able to scan all the wells."""

    wells = defaultdict()
    gains = defaultdict(list)
    green_sorted = defaultdict(list)
    medians = defaultdict(int)

    for c in ['green', 'blue', 'yellow', 'red']:
        mlist = []
        for d in sec_gain_d:
            # Sort gain data into a list dict with well as key and where the
            # value is a list with a gain value for each channel.
            gains[d['well']].append(d[c])
            if c == 'green':
                # Round gain values to multiples of 10 in green channel
                d['green'] = int(round(int(d['green']), -1))
                green_sorted[d['green']].append(d['well'])
                well_no = 8*(int(get_wfx(d['well']))-1)+int(get_wfy(d['well']))
                wells[well_no] = d['well']
            else:
                # Find the median value of all gains in
                # blue, yellow and red channels.
                mlist.append(int(d[c]))
                medians[c] = int(np.median(mlist))
    wells = OrderedDict(sorted(wells.items(), key=lambda t: t[0]))
    return {'green_sorted': green_sorted, 'medians': medians,
            'wells': wells, 'gains': gains}
