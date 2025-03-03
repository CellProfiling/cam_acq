"""Tests for command."""

from camacq.plugins.leica import command


def test_del():
    """Test deletelist command."""
    cmd = command.del_com()
    assert cmd == [("cmd", "deletelist")]


def test_start():
    """Test startscan command."""
    cmd = command.start()
    assert cmd == [("cmd", "startscan")]


def test_stop():
    """Test stopscan command."""
    cmd = command.stop()
    assert cmd == [("cmd", "stopscan")]


def test_camstart():
    """Test startcamscan command."""
    cmd = command.camstart_com("afjob10x", 100, 10)
    assert cmd == [
        ("cmd", "startcamscan"),
        ("runtime", "36000"),
        ("repeattime", "36000"),
        ("afj", "afjob10x"),
        ("afr", "100"),
        ("afs", "10"),
    ]


def test_camstart_no_args():
    """Test startcamscan command."""
    cmd = command.camstart_com()
    assert cmd == [
        ("cmd", "startcamscan"),
        ("runtime", "36000"),
        ("repeattime", "36000"),
    ]


def test_cam_stop():
    """Test stopcamscan command."""
    cmd = command.camstop_com()
    assert cmd == [("cmd", "stopcamscan")]


def test_gain():
    """Test command to adjust gain on pmt."""
    cmd = command.gain_com("job12", 2, 666)
    assert cmd == [
        ("cmd", "adjust"),
        ("tar", "pmt"),
        ("num", "2"),
        ("exp", "job12"),
        ("prop", "gain"),
        ("value", "666"),
    ]


def test_enable():
    """Test enable field command."""
    cmd = command.enable_com(0, 2, 1, 3, False)
    assert cmd == [
        ("cmd", "enable"),
        ("slide", "0"),
        ("wellx", "1"),
        ("welly", "3"),
        ("fieldx", "2"),
        ("fieldy", "4"),
        ("value", "false"),
    ]


def test_cam_com():
    """Test add a field to the cam list."""
    cmd = command.cam_com("job12", 0, 2, 1, 3, 45, 68)
    assert cmd == [
        ("cmd", "add"),
        ("tar", "camlist"),
        ("exp", "job12"),
        ("ext", "af"),
        ("slide", "0"),
        ("wellx", "1"),
        ("welly", "3"),
        ("fieldx", "2"),
        ("fieldy", "4"),
        ("dxpos", "45"),
        ("dypos", "68"),
    ]
