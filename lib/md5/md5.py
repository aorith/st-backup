import os
import logging
import hashlib
from lib.timer import timer


@timer
def md5(fname):
    fname = os.path.realpath(fname)
    chunk_size = 4 * 1024 * 1024
    hash_md5 = hashlib.md5()
    logging.info("Calculating md5sum of %s.", fname)
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()
