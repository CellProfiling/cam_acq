import re
from collections import OrderedDict


def make_com(base_com):
    """Decorator function for the command functions, in the Command class."""

    def wrapper(self, *args, **kwargs):
        """Wrapper function in the decorator.
        Creates the command from the base command and concatenates
        any existing command with the new command and returns."""
        com = ''
        for key, val in base_com(self, *args, **kwargs).iteritems():
            com = com + ' /' + key + ':' + val
        self.com = self.com + '/cli:1 /app:matrix' + com + '\n'
        return self.com
    return wrapper


class Command(object):

    """Command class

    Attributes:
        com: A string where each line is a command to be sent to the server.
    """

    def __init__(self):
        self.com = ''

    def get_wfx(self, compartment):
        """Returns a string representing the well or field X coordinate."""

        return str(int(re.sub(r'\D',
                              '',
                              re.sub('--.\d\d', '', compartment)
                              )) + 1)

    def get_wfy(self, compartment):
        """Returns a string representing the well or field Y coordinate."""

        return str(int(re.sub(r'\D',
                              '',
                              re.sub('.\d\d--', '', compartment)
                              )) + 1)

    @make_com
    def del_com(self):
        """Returns a dict with parts for the cam command for deleting
        the cam list."""

        return OrderedDict([('cmd', 'deletelist')])

    @make_com
    def start_com(self):
        """Returns a dict with parts for the cam command for starting
        the scan."""

        return OrderedDict([('cmd', 'startscan')])

    @make_com
    def stop_com(self):
        """Returns a dict with parts for the cam command for stopping
        the scan."""

        return OrderedDict([('cmd', 'stopscan')])

    @make_com
    def camstart_com(self, afjob=None, afrange=None, afsteps=None):
        """Returns a dict with parts for the cam command to start the cam scan
        with selected AF job and AF settings."""

        if afjob is None:
            afjob = ''
        else:
            afjob = afjob
        if afrange is None:
            afrange = ''
        else:
            afrange = afrange
        if afsteps is None:
            afsteps = ''
        else:
            afsteps = afsteps

        return OrderedDict([('cmd', 'startcamscan'), ('runtime', '36000'),
                            ('repeattime', '36000'), ('afj', afjob),
                            ('afr', afrange), ('afs', afsteps)])

    @make_com
    def camstop_com(self):
        """Returns a dict with parts for the cam command for stopping the
        cam scan."""

        return OrderedDict([('cmd', 'stopcamscan')])

    @make_com
    def gain_com(self, exp='job', num='1', value='800'):
        """Returns a dict with parts for the cam command for changing the
        pmt gain in a job."""

        return OrderedDict([('cmd', 'adjust'), ('tar', 'pmt'), ('num', num),
                            ('exp', exp), ('prop', 'gain'), ('value', value)])

    @make_com
    def enable_com(self, well, field, enable):
        """Returns a dict with parts for the cam command
        to enable a field in a well. Gets wellx/y and fieldx/y from well and
        field by calling get_wfx and get_wfy."""

        wellx = self.get_wfx(well)
        welly = self.get_wfy(well)
        fieldx = self.get_wfx(field)
        fieldy = self.get_wfy(field)

        return OrderedDict([('cmd', 'enable'), ('slide', '0'), ('wellx', wellx),
                            ('welly', welly), ('fieldx', fieldx),
                            ('fieldy', fieldy), ('value', enable)])

    @make_com
    def cam_com(self, exp, well, field, dx, dy):
        """Returns a dict with parts for the cam command to add a field to
        the cam list. Gets wellx/y and fieldx/y from well and field by calling
        get_wfx and get_wfy."""

        wellx = self.get_wfx(well)
        welly = self.get_wfy(well)
        fieldx = self.get_wfx(field)
        fieldy = self.get_wfy(field)

        return OrderedDict([('cmd', 'add'), ('tar', 'camlist'), ('exp', exp),
                            ('ext', 'af'), ('slide', '0'), ('wellx', wellx),
                            ('welly', welly), ('fieldx', fieldx),
                            ('fieldy', fieldy), ('dxpos', dx), ('dypos', dy)])
