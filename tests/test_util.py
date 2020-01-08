"""Test util module."""
from collections import OrderedDict
from copy import deepcopy
from unittest.mock import call, patch, mock_open

from camacq.util import read_csv, write_csv

CSV_TEMPLATE = """
header1,header2,header3
one,two,three
four,five,six
""".strip()

CSV_READ = [
    OrderedDict([("header1", "one"), ("header2", "two"), ("header3", "three")]),
    OrderedDict([("header1", "four"), ("header2", "five"), ("header3", "six")]),
]

CSV_WRITE = {
    "one": {"header2": "two", "header3": "three"},
    "four": {"header2": "five", "header3": "six"},
}


def test_read_csv():
    """Test read csv."""
    with patch("builtins.open", mock_open(read_data=CSV_TEMPLATE)) as m_open:
        mock_path = "path/to/open"
        csv_dict = read_csv(mock_path)
        assert csv_dict == CSV_READ
        assert m_open.call_args == call(mock_path)


def test_read_csv_index():
    """Test read csv with index."""
    index = "header2"
    expected_csv = {}
    for item in deepcopy(CSV_READ):
        key = item.pop(index)
        expected_csv[key] = item

    with patch("builtins.open", mock_open(read_data=CSV_TEMPLATE)) as m_open:
        mock_path = "path/to/open"
        csv_dict = read_csv(mock_path, index=index)
        assert csv_dict == expected_csv
        assert m_open.call_args == call(mock_path)


def test_write_csv():
    """Test write csv."""
    with patch("builtins.open", mock_open()) as m_open:
        mock_path = "path/to/open"
        write_csv(mock_path, CSV_WRITE, list(CSV_READ[0]))
        written = [
            tuple(CSV_READ[0]),
            tuple(CSV_READ[0].values()),
            tuple(CSV_READ[1].values()),
        ]
        assert m_open.return_value.write.call_count == 3
        assert m_open.return_value.write.call_args_list == [
            call(",".join(args) + "\r\n") for args in written
        ]
