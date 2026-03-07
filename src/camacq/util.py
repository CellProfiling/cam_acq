"""Host utils that are not aware of the implementation of camacq."""

from typing import Any


class dotdict(dict[str, Any]):  # pylint: disable=invalid-name
    """Access to dictionary attributes with dot notation."""

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
