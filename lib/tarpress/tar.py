import os
import sys
import logging
import tarfile
from lib.timer import timer


@timer
def create_tar(folder_path, dest_path):
    logging.info("Starting tarball process...")
    try:
        with tarfile.open(dest_path, 'w') as tar:
            tar.add(folder_path, arcname=os.path.basename(folder_path))
    except Exception as ex:
        txt = "Failed to tar file.\nException of type {0}. Arguments:\n{1!r}"
        msg = txt.format(type(ex).__name__, ex.args)
        logging.error(msg)
        os.remove(dest_path)
        sys.exit(1)

    return tar.name
