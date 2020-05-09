import os
import sys
import logging
import subprocess
from lib.timer import timer


@timer
def gpg_encrypt(fname, recipients):
    logging.info("Starting to encrypt %s", fname)

    cmd_recipients = ""
    for r in recipients.split(' '):
        cmd_recipients = cmd_recipients + ' -r ' + r

    cmd = "gpg -e {} --batch --always-trust --quiet --yes {}".format(
        cmd_recipients,
        fname
    )
    try:
        result = subprocess.check_output(
            cmd, stderr=subprocess.STDOUT, shell=True
        )
    except Exception as ex:
        txt = "Process failed while trying to encrypt: {0}.\nException of type {1}."
        msg = txt.format(fname, type(ex).__name__)
        logging.error(msg)
        os.remove(fname)
        sys.exit(1)

    os.remove(fname)
    return fname + '.gpg'
