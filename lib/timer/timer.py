import logging
from time import time


def timer(function):
    """
    wrapper timer function, use with a decorator --> @timer
    """
    def wrapper(*args, **kwargs):
        before = time()
        rv = function(*args, **kwargs)
        elapsed = time() - before
        logging.info('Function %s() finished in %.3f seconds.',
                     function.__name__, elapsed)
        return rv
    return wrapper
