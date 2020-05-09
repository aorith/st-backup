import os
import sys
import platform
import logging
import subprocess
import urllib.request
import zipfile
import shutil


def rclone_setup(rclone_path):
    logging.info("> Checking if rclone is updated <")
    rclone_bin = os.path.join(rclone_path, 'rclone')

    # TODO: implement more platforms
    os_string = platform.system().lower()
    arch_string = platform.machine()
    if 'armv' in arch_string:
        arch_string = 'arm'
    elif 'aarch64' in arch_string:
        arch_string = 'arm64'
    elif '64' in arch_string:
        arch_string = 'amd64'
    else:
        arch_string = '386'

    if not is_rclone_updated(rclone_path, rclone_bin):
        logging.info(
            "Downloading and installing rclone at {}".format(rclone_path))
        zip_file = os.path.join(rclone_path, 'rclone.zip')
        url_string = "https://downloads.rclone.org/rclone-current-{}-{}.zip".format(
            os_string, arch_string)
        try:
            urllib.request.urlretrieve(url_string, zip_file)
        except Exception as ex:
            txt = "Failed to update rclone.\nException of type {0}. Arguments:\n{1!r}"
            msg = txt.format(type(ex).__name__, ex.args)
            logging.error(msg)
            try:
                os.remove(zip_file)
            except:
                pass
            sys.exit(1)

        # we have downloaded the zip, lets unzip and check
        with zipfile.ZipFile(zip_file) as Z:
            for member in Z.namelist():
                filename = os.path.basename(member)
                # skip directories
                if not filename:
                    continue
                # copy file (taken from zipfile's extract)
                source = Z.open(member)
                target = open(os.path.join(rclone_path, filename), "wb")
                with source, target:
                    shutil.copyfileobj(source, target)

        # clean
        os.remove(zip_file)

        # final check
        if is_rclone_updated(rclone_path, rclone_bin):
            logging.info("rclone successfully updated")
        else:
            logging.error("Something went wrong updating rclone")
            sys.exit(1)


def is_rclone_updated(rclone_path, rclone_bin):
    # check upstreams version of rclone
    with urllib.request.urlopen("https://downloads.rclone.org/version.txt") as fp:
        upstream_version = fp.read().decode(
            "utf8").rstrip().split(' ')[1].strip()

    # check installed version
    installed_version = None
    if os.path.isdir(rclone_path):
        if os.path.isfile(rclone_bin):
            try:
                # os.chmod is octal
                os.chmod(rclone_bin, 0o775)
                cmd = rclone_bin + ' --version | head -n 1'
                result = subprocess.check_output(
                    cmd, stderr=subprocess.STDOUT, shell=True
                )
                installed_version = result.decode(
                    "utf8").rstrip().split(' ')[1].strip()
            except Exception as ex:
                txt = "Failed to check rclone version.\nException of type {0}. Arguments:\n{1!r}"
                msg = txt.format(type(ex).__name__, ex.args)
                logging.error(msg)
                sys.exit(1)
    else:
        logging.info("rclone install path does not exist, creating it")
        os.mkdir(rclone_path)
        logging.info("created folder: {}".format(rclone_path))

    logging.info("Installed version: {}".format(installed_version))
    logging.info("Upstream  version: {}".format(upstream_version))

    return installed_version == upstream_version
