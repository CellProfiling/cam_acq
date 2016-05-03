"""Handle commands."""
import re


def get_wfx(compartment):
    """Return a string representing the well or field X coordinate."""
    return str(int(re.sub(
        r'\D', '', re.sub(r'--.\d\d', '', compartment))) + 1)


def get_wfy(compartment):
    """Return a string representing the well or field Y coordinate."""
    return str(int(re.sub(
        r'\D', '', re.sub(r'.\d\d--', '', compartment))) + 1)


def del_com():
    """Delete the cam list.

    Return a list with parts for the cam command.
    """
    return [('cmd', 'deletelist')]


def start_com():
    """Start the scan.

    Return a list with parts for the cam command.
    """
    return [('cmd', 'startscan')]


def stop_com():
    """Stop the scan.

    Return a list with parts for the cam command.
    """
    return [('cmd', 'stopscan')]


def camstart_com(afjob=None, afrange=None, afsteps=None):
    """Start the cam scan with selected AF job and AF settings.

    Return a list with parts for the cam command.
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

    return [('cmd', 'startcamscan'), ('runtime', '36000'),
            ('repeattime', '36000'), ('afj', afjob), ('afr', afrange),
            ('afs', afsteps)]


def camstop_com():
    """Stop the cam scan.

    Return a list with parts for the cam command.
    """
    return [('cmd', 'stopcamscan')]


def gain_com(exp='job', num='1', value='800'):
    """Change the pmt gain in a job.

    Return a list with parts for the cam command.
    """
    return [('cmd', 'adjust'), ('tar', 'pmt'), ('num', num), ('exp', exp),
            ('prop', 'gain'), ('value', value)]


def enable_com(well, field, enable):
    """Enable a field in a well.

    Return a list with parts for the cam command.
    Get wellx/y and fieldx/y from well and field
    by calling get_wfx and get_wfy.
    """
    wellx = get_wfx(well)
    welly = get_wfy(well)
    fieldx = get_wfx(field)
    fieldy = get_wfy(field)

    return [('cmd', 'enable'), ('slide', '0'), ('wellx', wellx),
            ('welly', welly), ('fieldx', fieldx), ('fieldy', fieldy),
            ('value', enable)]


def cam_com(exp, well, field, dxcoord, dycoord):
    """Add a field to the cam list.

    Return a list with parts for the cam command.
    Get wellx/y and fieldx/y from well and field by calling
    get_wfx and get_wfy.
    """
    wellx = get_wfx(well)
    welly = get_wfy(well)
    fieldx = get_wfx(field)
    fieldy = get_wfy(field)

    return [('cmd', 'add'), ('tar', 'camlist'), ('exp', exp), ('ext', 'af'),
            ('slide', '0'), ('wellx', wellx), ('welly', welly),
            ('fieldx', fieldx), ('fieldy', fieldy), ('dxpos', dxcoord),
            ('dypos', dycoord)]
