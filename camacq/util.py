"""Host utils that are not aware of the implementation of camacq."""
import asyncio

try:
    asyncio_run = asyncio.run  # pylint: disable=invalid-name
except AttributeError:

    def asyncio_run(main, debug=False):
        """Mimic asyncio.run which is only in Python 3.7."""
        loop = asyncio.get_event_loop()
        loop.set_debug(debug)
        try:
            return loop.run_until_complete(main)
        finally:
            asyncio.set_event_loop(None)
            loop.close()


class dotdict(dict):  # pylint: disable=invalid-name
    """Access to dictionary attributes with dot notation."""

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
