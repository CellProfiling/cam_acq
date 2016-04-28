"""Handle commands."""
import re
from collections import OrderedDict


def make_com(base_com):
    """Decorate command functions, in the Command class."""

    def wrapper(self, *args, **kwargs):
        """Wrap the base_com function.

        Create the command from the base command and concatenate
        any existing command with the new command and return the command.
        """
        com = ''
        for key, val in base_com(self, *args, **kwargs).iteritems():
            if val:
                com = com + ' /' + key + ':' + val
        self.com = self.com + '/cli:1 /app:matrix' + com + '\n'
        return self.com
    return wrapper


class Command(object):
    """Command class.

    Attributes:
        com: A string where each line is a command to be sent to the server.
    """

    def __init__(self):
        """Set up instance."""
        self.com = ''

    def get_wfx(self, compartment):
        """Return a string representing the well or field X coordinate."""
        return str(int(re.sub(
            r'\D', '', re.sub(r'--.\d\d', '', compartment))) + 1)

    def get_wfy(self, compartment):
        """Return a string representing the well or field Y coordinate."""
        return str(int(re.sub(
            r'\D', '', re.sub(r'.\d\d--', '', compartment))) + 1)

    @make_com
    def del_com(self):
        """Delete the cam list.

        Return a dict with parts for the cam command.
        """
        return OrderedDict([('cmd', 'deletelist')])

    @make_com
    def start_com(self):
        """Start the scan.

        Return a dict with parts for the cam command.
        """
        return OrderedDict([('cmd', 'startscan')])

    @make_com
    def stop_com(self):
        """Stop the scan.

        Return a dict with parts for the cam command.
        """
        return OrderedDict([('cmd', 'stopscan')])

    @make_com
    def camstart_com(self, afjob=None, afrange=None, afsteps=None):
        """Start the cam scan with selected AF job and AF settings.

        Return a dict with parts for the cam command.
        """
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
        """Stop the cam scan.

        Return a dict with parts for the cam command.
        """
        return OrderedDict([('cmd', 'stopcamscan')])

    @make_com
    def gain_com(self, exp='job', num='1', value='800'):
        """Change the pmt gain in a job.

        Return a dict with parts for the cam command.
        """
        return OrderedDict([('cmd', 'adjust'), ('tar', 'pmt'), ('num', num),
                            ('exp', exp), ('prop', 'gain'), ('value', value)])

    @make_com
    def enable_com(self, well, field, enable):
        """Enable a field in a well.

        Return a dict with parts for the cam command.
        Get wellx/y and fieldx/y from well and field
        by calling get_wfx and get_wfy.
        """
        wellx = self.get_wfx(well)
        welly = self.get_wfy(well)
        fieldx = self.get_wfx(field)
        fieldy = self.get_wfy(field)

        return OrderedDict([('cmd', 'enable'), ('slide', '0'),
                            ('wellx', wellx), ('welly', welly),
                            ('fieldx', fieldx), ('fieldy', fieldy),
                            ('value', enable)])

    @make_com
    def cam_com(self, exp, well, field, dxcoord, dycoord):
        """Add a field to the cam list.

        Return a dict with parts for the cam command.
        Get wellx/y and fieldx/y from well and field by calling
        get_wfx and get_wfy.
        """
        wellx = self.get_wfx(well)
        welly = self.get_wfy(well)
        fieldx = self.get_wfx(field)
        fieldy = self.get_wfy(field)

        return OrderedDict([('cmd', 'add'), ('tar', 'camlist'), ('exp', exp),
                            ('ext', 'af'), ('slide', '0'), ('wellx', wellx),
                            ('welly', welly), ('fieldx', fieldx),
                            ('fieldy', fieldy), ('dxpos', dxcoord),
                            ('dypos', dycoord)])
