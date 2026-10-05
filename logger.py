import logging
import sys

LOG = logging.getLogger('sound-helper')


def setup(debug=False):
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)-5s [%(name)s] %(message)s',
        datefmt='%H:%M:%S',
    ))
    LOG.addHandler(handler)
    LOG.setLevel(logging.DEBUG if debug else logging.INFO)
    LOG.debug('Debug logging enabled')
