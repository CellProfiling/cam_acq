"""Handle commands."""


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
    if afjob is not None:
        afjob = ('afj', afjob)
    if afrange is not None:
        afrange = ('afr', afrange)
    if afsteps is not None:
        afsteps = ('afs', afsteps)

    template = [('cmd', 'startcamscan'), ('runtime', '36000'),
                ('repeattime', '36000')]

    for cmd in [afjob, afrange, afsteps]:
        if cmd:
            template.append(cmd)

    return template


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


def enable_com(wellu, wellv, fieldx, fieldy, enable):
    """Enable a field in a well.

    Return a list with parts for the cam command.
    """
    wellx = str(wellu + 1)
    welly = str(wellv + 1)
    fieldx = str(fieldx + 1)
    fieldy = str(fieldy + 1)

    return [('cmd', 'enable'), ('slide', '0'), ('wellx', wellx),
            ('welly', welly), ('fieldx', fieldx), ('fieldy', fieldy),
            ('value', enable)]


def cam_com(exp, wellu, wellv, fieldx, fieldy, dxcoord, dycoord):
    """Add a field to the cam list.

    Return a list with parts for the cam command.
    """
    # pylint: disable=too-many-arguments
    wellx = str(wellu + 1)
    welly = str(wellv + 1)
    fieldx = str(fieldx + 1)
    fieldy = str(fieldy + 1)

    return [('cmd', 'add'), ('tar', 'camlist'), ('exp', exp), ('ext', 'af'),
            ('slide', '0'), ('wellx', wellx), ('welly', welly),
            ('fieldx', fieldx), ('fieldy', fieldy), ('dxpos', dxcoord),
            ('dypos', dycoord)]
