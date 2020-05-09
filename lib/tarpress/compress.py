import os
import logging
import gzip
from time import time
from lib.timer import timer
from lib.chunkinfo import by_chunk_info


@timer
def compress(file_path):
    logging.info("Starting to compress %s", file_path)
    file_size = os.path.getsize(file_path)
    elapsed = 0
    try:
        chunk_size = 64 * 1024 * 1024
        compressed_path = file_path + '.gz'
        with open(file_path, 'rb') as fh:
            with gzip.open(compressed_path, 'wb') as f:
                while True:
                    t0 = time()
                    chunk = fh.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    elapsed = by_chunk_info(
                        file_size, chunk_size, f.tell(), t0, elapsed)
    except Exception as ex:
        txt = "Failed to compress file.\nException of type {0}. Arguments:\n{1!r}"
        msg = txt.format(type(ex).__name__, ex.args)
        logging.error(msg)
        os.remove(file_path)
        sys.exit(1)

    os.remove(file_path)
    return compressed_path
