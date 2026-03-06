"""Host utils that are not aware of the implementation of camacq."""


class dotdict(dict):  # pylint: disable=invalid-name
    """Access to dictionary attributes with dot notation."""

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
