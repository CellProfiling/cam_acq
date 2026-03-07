"""Handle commands."""


def start() -> list[tuple[str, str]]:
    """Start the scan.

    Return a list with parts for the cam command.
    """
    return [("cmd", "startscan")]


def stop() -> list[tuple[str, str]]:
    """Stop the scan.

    Return a list with parts for the cam command.
    """
    return [("cmd", "stopscan")]


def del_com() -> list[tuple[str, str]]:
    """Delete the cam list.

    Return a list with parts for the cam command.
    """
    return [("cmd", "deletelist")]


def camstart_com(
    afjob: str | None = None,
    afrange: int | None = None,
    afsteps: int | None = None,
) -> list[tuple[str, str]]:
    """Start the cam scan with selected AF job and AF settings.

    Return a list with parts for the cam command.
    """
    afjob_tup: tuple[str, str] | None = None
    afrange_tup: tuple[str, str] | None = None
    afsteps_tup: tuple[str, str] | None = None
    if afjob is not None:
        afjob_tup = ("afj", str(afjob))
    if afrange is not None:
        afrange_tup = ("afr", str(afrange))
    if afsteps is not None:
        afsteps_tup = ("afs", str(afsteps))

    template: list[tuple[str, str]] = [
        ("cmd", "startcamscan"),
        ("runtime", "36000"),
        ("repeattime", "36000"),
    ]

    for cmd in [afjob_tup, afrange_tup, afsteps_tup]:
        if cmd:
            template.append(cmd)

    return template


def camstop_com() -> list[tuple[str, str]]:
    """Stop the cam scan.

    Return a list with parts for the cam command.
    """
    return [("cmd", "stopcamscan")]


def gain_com(exp: str, num: int, value: float) -> list[tuple[str, str]]:
    """Change the pmt gain in a job.

    Return a list with parts for the cam command.
    """
    return [
        ("cmd", "adjust"),
        ("tar", "pmt"),
        ("num", str(num)),
        ("exp", str(exp)),
        ("prop", "gain"),
        ("value", str(value)),
    ]


def enable_com(
    wellu: int, wellv: int, fieldx: int, fieldy: int, enable: bool
) -> list[tuple[str, str]]:
    """Enable a field in a well.

    Return a list with parts for the cam command.
    """
    wellx = str(wellu + 1)
    welly = str(wellv + 1)
    fieldx_str = str(fieldx + 1)
    fieldy_str = str(fieldy + 1)

    return [
        ("cmd", "enable"),
        ("slide", "0"),
        ("wellx", wellx),
        ("welly", welly),
        ("fieldx", fieldx_str),
        ("fieldy", fieldy_str),
        ("value", str(enable).lower()),
    ]


def cam_com(
    exp: str,
    wellu: int,
    wellv: int,
    fieldx: int,
    fieldy: int,
    dxcoord: float,
    dycoord: float,
) -> list[tuple[str, str]]:
    """Add a field to the cam list.

    Return a list with parts for the cam command.
    """
    wellx = str(wellu + 1)
    welly = str(wellv + 1)
    fieldx_str = str(fieldx + 1)
    fieldy_str = str(fieldy + 1)

    return [
        ("cmd", "add"),
        ("tar", "camlist"),
        ("exp", exp),
        ("ext", "af"),
        ("slide", "0"),
        ("wellx", wellx),
        ("welly", welly),
        ("fieldx", fieldx_str),
        ("fieldy", fieldy_str),
        ("dxpos", str(dxcoord)),
        ("dypos", str(dycoord)),
    ]
