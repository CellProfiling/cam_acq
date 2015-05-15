import re

def com_deco(new_com):
    """Decorator function for the command functions, in the Command class."""

    def wrapper(self, *args, **kwargs):
        """Wrapper function in the decorator.
        Concatenates the old with the new command and returns."""

        com = ''
        for key, val in new_com().iteritems():
            com = com + ' /' + key + ':' + val
        self.com = self.com + '/cli:1 /app:matrix' + com + '\n'
        return self.com
    return wrapper

def get_wfx(compartment):
    """Returns a string representing the well or field X coordinate."""

    return str(int(re.sub(r'\D', '', re.sub('--.\d\d', '', compartment)))+1)

def get_wfy(compartment):
    """Returns a string representing the well or field Y coordinate."""

    return str(int(re.sub(r'\D', '', re.sub('.\d\d--', '', compartment)))+1)

class Command(object):
    """Command class

    Attributes:
        com: A string where each line is a command to be sent to the server.
    """

    def __init__(self, com):
        self.com = com

    @com_deco
    def del_com(self):
        """Returns a dict with parts for the cam command for deleting
        the cam list."""

        return {'cmd': 'deletelist'}

    @com_deco
    def start_com(self):
        """Returns a dict with parts for the cam command for starting
        the scan."""

        return {'cmd': 'startscan'}

    @com_deco
    def stop_com(self):
        """Returns a dict with parts for the cam command for stopping
        the scan."""

        return {'cmd': 'stopscan'}

    @com_deco
    def camstart_com(self, afjob, afrange, afsteps):
        """Returns a dict with parts for the cam command to start the cam scan
        with selected AF job and AF settings."""

        return {'cmd': 'startcamscan', 'runtime': '36000', 'repeattime': '36000'
                'afj': afjob, 'afr': afrange, 'afs': afsteps}

    @com_deco
    def camstop_com(self):
        """Returns a dict with parts for the cam command for stopping the
        cam scan."""

        return {'cmd': 'stopcamscan'}

    @com_deco
    def gain_com(self, num='0', exp='job', value='800'):
        """Returns a dict with parts for the cam command for changing the
        pmt gain in a job."""

        return {'cmd': 'adjust', 'tar': 'pmt', 'num': num,
                'exp': exp, 'prop': 'gain', 'value': value}

    @com_deco
    def enable_com(self, well, field, enable):
        """Returns a dict with parts for the cam command
        to enable a field in a well. Gets wellx/y and fieldx/y from well and
        field by calling get_wfx and get_wfy."""

        wellx = get_wfx(well)
        welly = get_wfy(well)
        fieldx = get_wfx(field)
        fieldy = get_wfy(field)

        return {'cmd': 'enable', 'slide': '0', 'wellx': wellx, 'welly': welly,
                'fieldx': fieldx, 'fieldy': fieldy, 'value': enable}

    @com_deco
    def cam_com(self, exp, well, field, dx, dy):
        """Returns a dict with parts for the cam command to add a field to
        the cam list. Gets wellx/y and fieldx/y from well and field by calling
        get_wfx and get_wfy."""

        wellx = get_wfx(well)
        welly = get_wfy(well)
        fieldx = get_wfx(field)
        fieldy = get_wfy(field)

        return {'cmd': 'add', 'tar': 'camlist', 'exp': exp, 'ext': 'af',
                'slide': '0' 'wellx': wellx, 'welly': welly, 'fieldx': fieldx,
                'fieldy': fieldy, 'dxpos': dx, 'dypos': dy}
