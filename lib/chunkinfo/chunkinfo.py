import logging
from time import time


def by_chunk_info(file_size, chunk_size, processed, t0, elapsed):
    t1 = time()
    elapsed_now = t1 - t0
    elapsed = elapsed + elapsed_now
    speed = round((chunk_size / elapsed_now) / (1024 * 1024), 2)
    processed = round(processed/(1024 * 1024), 2)
    file_size = round(file_size/(1024 * 1024), 2)
    msg = "Processing... {}/{} MB - elapsed {} seconds ({} MB/s)".format(
        processed,
        file_size,
        round(elapsed, 2),
        speed
    )
    logging.info(msg)
    return elapsed
