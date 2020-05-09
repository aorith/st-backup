import os
import sys
import logging
import subprocess
from lib.rclonewrapper.myexception import MyException


class Rclone:
    def __init__(self, rclone_bin):
        self.bin = rclone_bin
        if not os.path.isfile(self.bin):
            logging.error(
                "Could not find rclone binary on {}".format(self.bin))
            sys.exit(1)

    def run_command(self, cmd):
        try:
            result = subprocess.Popen(
                cmd.split(),
                stderr=subprocess.STDOUT,
                stdout=subprocess.PIPE,
            )
            ret = result.wait()
            output = str(result.communicate()[0].decode('utf8').strip())
        except Exception as ex:
            txt = "Failed to execute rclone command.\nException of type {0}. Arguments:\n{1!r}\n\n{2}"
            msg = txt.format(type(ex).__name__, ex.args, output)
            logging.error(msg)
            sys.exit(1)

        return ret, output

    def delete(self, remote, filepath):
        cmd = self.bin + ' delete ' + remote.name + ':' + filepath
        ret, output = self.run_command(cmd)
        if ret != 0:
            logging.error("Could not delete: {}".format(output))

    def lsf(self, remote, folder, use_ls=False, ls_depth='1'):
        if use_ls:
            cmd = self.bin + ' ls --max-depth ' + \
                str(ls_depth) + ' ' + remote.name + ':' + folder
        else:
            cmd = self.bin + ' lsf  ' + remote.name + ':' + folder
        ret, output = self.run_command(cmd)
        if ret != 0:
            if 'directory not found' in output.lower():
                return ['']
            elif 't find section in config' in output.lower():
                logging.error("Check for a missconfiguration in the config file for the remote alias\
                        \nAlso check that you've configured the remote with the same name in rclone.\
                        \nError calling: {}".format(cmd))
                sys.exit(1)
            else:
                logging.error(
                    "Unknow error occurred calling: {}\n{}".format(cmd, output))
                sys.exit(1)

        return output.split('\n')

    def upload(self, rname, fname, dest):
        cmd = self.bin + ' mkdir ' + rname + ':' + dest
        self.run_command(cmd)
        cmd = self.bin + ' copy ' + fname + ' ' + rname + ':' + dest
        logging.debug("Running: {}".format(cmd))
        return self.run_command(cmd)

    def check_space(self, remote, filesize=None):
        if filesize is None:
            cmd = self.bin + ' about ' + remote.name + ':'
        else:
            cmd = self.bin + ' about ' + remote.name + ': --full'

        ret, output = self.run_command(cmd)
        if ret != 0:
            logging.error(
                "Something went wrong calling: {}\n{}".format(cmd, output))

        if filesize is None:
            total = output.split()[1]
            used = output.split()[3]
            free = output.split()[5]
            return total, used, free
        else:
            free = output.split()[5]
            logging.debug("FREE: {} - Filesize: {}".format(free, filesize))
            return int(free) > int(filesize)
