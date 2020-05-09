import os
import sys
import logging
import json
import configparser
from datetime import datetime
from tabulate import tabulate

from lib.rclonewrapper import rclone_setup, Rclone


class Config:
    def __init__(self, args, script_path):
        self.args = args
        self.mypath = script_path
        self.cfg = configparser.ConfigParser()
        self.cfg.read(os.path.join(self.mypath, 'config.ini'))
        self.platform = sys.platform

        # store archive mode
        self.archive_mode = False
        if self.args.mode == 'backup':
            self.archive_mode = self.args.archive

        # rclone_path is absolute or relative?
        self.rclone_path = self.cfg['DEFAULT']['Rclone_path']
        if os.path.isabs(self.rclone_path):
            self.rclone_path = os.path.realpath(self.rclone_path)
        else:
            self.rclone_path = os.path.realpath(
                os.path.join(self.mypath, self.rclone_path))
        # rclone binary path
        self.rclone_bin = os.path.join(self.rclone_path, 'rclone')

        # remote root path
        self.remote_root = self.cfg['DEFAULT']['Remote_root']

        # audit log
        self.audit_log = self.cfg['DEFAULT']['Audit_log']
        if not os.path.isfile(self.audit_log):
            logging.error(
                "ERROR: AUDIT LOG IS SUPPOSED TO POINT TO A LOG FILE")
            sys.exit(1)

        # Device names
        self.devices = dict()
        if self.platform == 'linux':
            config_path = os.path.join(
                os.environ['HOME'], '.config', 'syncthing', 'config.xml')
        elif self.platform == 'win32':
            config_path = os.path.join(
                os.environ['LOCALAPPDATA'], 'syncthing', 'config.xml')
        elif self.platform == 'darwin':
            config_path = os.path.join(
                os.environ['HOME'], 'Library', 'Application Support', 'Syncthing', 'config.xml')
        else:
            config_path = None

        if config_path is not None:
            if os.path.isfile(config_path):
                with open(config_path, 'r') as f:
                    for line in f:
                        if 'device id=' in line and 'name=' in line:
                            did = line.split('id="')[1].split('"')[
                                0].split('-')[0]
                            name = line.split('name="')[1].split('"')[0]
                            self.devices.update({did: name})

        # recipients
        self.recipients = self.cfg['DEFAULT']['Recipients']

        # workdir is absolute or relative?
        self.workdir = self.cfg['DEFAULT']['Workdir']
        if os.path.isabs(self.workdir):
            self.workdir = os.path.realpath(self.workdir)
        else:
            self.workdir = os.path.realpath(
                os.path.join(self.mypath, self.workdir))
        # workdir exists?
        if os.path.exists(self.workdir):
            if not os.path.isdir(self.workdir):
                logging.error("ERROR: WORKDIR NOT SUPPOSED TO BE A FILE!")
                sys.exit(1)
        else:
            os.mkdir(self.workdir)

        # list of folders and remotes
        self.remotes = []
        self.folders = []
        for section in self.cfg.sections():
            if self.cfg[section]['Type'].lower() == 'remote':
                self.remotes.append(self.cfg[section])
            elif self.cfg[section]['Type'].lower() == 'folder':
                # set the local absolute path were the folder lives, and the remote path were backups will be stored
                fabspath = os.path.realpath(self.cfg[section]['Path'])
                if self.cfg[section]['Syncthing'].lower() == 'true':
                    # initialize the changed files count
                    self.cfg[section]['Changed'] = '0'
                    frempath = self.remote_root + \
                        '/Syncthing/' + self.cfg[section].name
                else:
                    self.cfg[section]['Changed'] = 'n/a'
                    self.cfg[section]['Id'] = 'n/a'
                    frempath = self.remote_root + \
                        '/Other/' + self.cfg[section].name

                self.cfg[section]['Path'] = fabspath
                self.cfg[section]['RPath'] = frempath
                # parse audit log for changed files
                with open(self.audit_log, 'r') as f:
                    for line in f:
                        jdata = json.loads(line)
                        if 'action' not in jdata['data']:
                            continue
                        if jdata['type'] in ['RemoteChangeDetected', 'LocalChangeDetected']:
                            fid = jdata['data']['folderID']
                            if self.cfg[section]['Id'] == fid:
                                self.cfg[section]['Changed'] = str(
                                    int(self.cfg[section]['Changed']) + 1)
                ####################################################
                # flag to check if we already have the backup ready (checked in backup() loop)
                self.cfg[section]['BackupReady'] = 'False'
                # flags to keep track of progress in prepare_backup()
                self.cfg[section]['MD5'] = 'None'
                self.cfg[section]['Tar'] = 'None'

                if not os.path.isdir(self.cfg[section]['Path']):
                    logging.error("Path to folder which doesn't exist: {}".format(
                        self.cfg[section]['Path']))
                    sys.exit(1)
                # check if folder is enabled
                # finally append the folder
                self.folders.append(self.cfg[section])

    def setup_rclone(self, update=True):
        if update:
            # install rclone
            rclone_setup(self.rclone_path)
        # rclone class
        self.rclone = Rclone(self.rclone_bin)

    def showconfig(self):
        # default config info
        print(tabulate({"DEFAULT": ['Workdir', 'Recipients',
                                    'Audit log', 'Remote root', 'Rclone Path', 'Total Remotes', 'Total Folders'],
                        "Value": [self.workdir, self.recipients, self.audit_log,
                                  self.remote_root, self.rclone_path,
                                  str(len(self.remotes)) + '  (' + str(
                                      len([r for r in self.remotes if r['Enabled'].lower() != 'true']))
                                  + ' disabled)',
                                  str(len(self.folders)) + '  (' + str(
                                      len([f for f in self.folders if f['Enabled'].lower() != 'true']))
                                  + ' disabled)']},
                       headers='keys', tablefmt='psql'))

        # folders info
        print(tabulate({"FOLDERS (enabled)": [f.name for f in self.folders],
                        "Id": [f['Id'] for f in self.folders],
                        "Syncthing": [f['Syncthing'] for f in self.folders],
                        "Path": [f['Path'] for f in self.folders],
                        "RPath": [f['RPath'] for f in self.folders],
                        "DOW": [f['DOW'] for f in self.folders],
                        "Changed": [f['Changed'] for f in self.folders],
                        },
                       headers='keys', tablefmt='psql'))

        # remotes info
        folders_inf = []
        for r in self.remotes:
            line = ""
            for fn, fmax, fmin in zip(r['Folders'].split(), r['Maxbackups'].split(), r['Minfiles'].split()):
                line = line + fn + ' (' + fmax + ')(' + fmin + ')\n'
            folders_inf.append(line)

        print(tabulate({"REMOTES": [r.name for r in self.remotes],
                        "Folder (Maxbackups)(Minfiles)": folders_inf
                        },
                       headers='keys', tablefmt='fancy_grid'))

    def should_backup(self, remote, folder):
        val = self.get_folder_cfg_by_remote(remote, folder)
        if val is None:
            # not configured in this remote
            logging.info(
                "Skipping {} as it is not configured in this remote".format(folder.name))
            return False
        else:
            maxbackups, minfiles = val
            # disabled?
            if folder['Enabled'].lower() != 'true':
                logging.info(
                    "Skipping {} as it is disabled.".format(folder.name))
                return False
            # if we are in archive mode and it's configured and not disabled, go ahead
            elif self.archive_mode:
                logging.info("Bypassing checks as archive mode is enabled")
                return True
            elif str(datetime.today().weekday()) not in folder['DOW']:
                logging.info("Skipping {} as today is {}({}) and is allowed on {}".format(
                    folder.name, datetime.today().strftime('%A'), datetime.today().weekday(), folder['DOW']))
                return False
            # if Syncthing, check if changed < minfiles to skip
            elif folder['Syncthing'].lower() == 'true':
                if int(folder['Changed']) < int(minfiles):
                    logging.info("Skipping {} as it hasn't changed enough files ({} < {})".format(
                        folder.name, folder['Changed'], minfiles))
                    return False

        return True

    def get_folder_cfg_by_remote(self, remote, folder):
        idx = self.get_idx_in_remote(remote, folder)
        if idx < 0:
            return None
        maxfiles = remote['Maxbackups'].split(' ')
        minfiles = remote['Minfiles'].split(' ')
        return (maxfiles[idx], minfiles[idx])

    def get_idx_in_remote(self, remote, folder):
        idx = 0
        for f in remote['Folders'].split(' '):
            if f == folder.name:
                return idx
            idx += 1
        return -1

    def get_folder_by_alias(self, alias):
        for f in self.folders:
            if f.name == alias:
                return f
        return None

    def showremoteconfig(self, remote):
        folders_alias = remote['Folders'].split(' ')
        # to keep the order
        folders = []
        for falias in folders_alias:
            for section in self.cfg.sections():
                if self.cfg[section]['Type'].lower() == 'folder' and self.cfg[section].name == falias:
                    folders.append(self.cfg[section])

        maxbackups = remote['Maxbackups'].split(' ')
        minfiles = remote['Minfiles'].split(' ')

        print(tabulate({remote.name: [f.name for f in folders],
                        "Folder Id": [f['Id'] for f in folders],
                        "Enabled": [f['Enabled'] for f in folders],
                        "Syncthing": [f['Syncthing'] for f in folders],
                        "Maxbackups": maxbackups,
                        "Minfiles": minfiles,
                        "DOW": [f['DOW'] for f in folders],
                        "Changed": [f['Changed'] for f in folders],
                        },
                       headers='keys', tablefmt='psql'))

    def lastmodified(self):
        # parse audit log for changed files
        table = [['Date', 'Time', 'Origin', 'Action', 'Folder',
                  'FolderID', 'Modified By', 'Filename/Path']]
        with open(self.audit_log, 'r') as f:
            for line in f:
                jdata = json.loads(line)
                if 'action' not in jdata['data']:
                    continue
                if jdata['type'] in ['RemoteChangeDetected', 'LocalChangeDetected']:
                    _date = jdata['time'].split('T')[0]
                    _time = jdata['time'].split('T')[1].split('.')[0]
                    origin = jdata['type']
                    if 'Remote' in origin:
                        origin = 'Remote'
                    else:
                        origin = 'Local'
                    action = jdata['data']['action']
                    label = jdata['data']['label']
                    fid = jdata['data']['folderID']
                    modifiedBy = jdata['data']['modifiedBy']
                    if modifiedBy in self.devices.keys():
                        modifiedBy = self.devices[modifiedBy]
                    fpath = jdata['data']['path']
                    table.append([_date, _time, origin, action,
                                  label, fid, modifiedBy, fpath])
            # print all the data
            print(tabulate(table, headers="firstrow", tablefmt="simple"))

    def listbackups(self, ralias=None, falias=None):
        logging.debug("RAlias: {} - FAlias: {}".format(ralias, falias))
        self.setup_rclone(update=False)
        for remote in self.remotes:

            # only print for specific remote if flag was passed
            if ralias is not None:
                if remote.name != ralias[0]:
                    continue

            table = [[remote.name, 'Folder', 'File', 'Size(MB)']]
            data = self.rclone.lsf(
                remote, self.remote_root, use_ls=True, ls_depth='4')
            for line in data:
                #'   758132 Syncthing/KeePass/ARC_20200508124150_KeePass.tar.gz.gpg'
                line = line.strip().split()
                #['758132', 'Syncthing/KeePass/ARC_20200508124150_KeePass.tar.gz.gpg']
                size = line[0]  # '758132'
                size = str(round(float(size)/1048576, 2))  # '0.72'
                line = os.path.split(line[1])
                #('Syncthing/KeePass', 'ARC_20200508124150_KeePass.tar.gz.gpg')

                filename = line[1]  # 'ARC_20200508124150_KeePass.tar.gz.gpg'
                kind = os.path.split(line[0])[0]  # 'Syncthing'
                folder = os.path.split(line[0])[1]  # 'KeePass'

                # skip folder if flag was passed  and does not match
                if falias is not None:
                    if folder != falias[0]:
                        continue

                # append the data
                table.append([kind, folder, filename, size])
            # print each remote
            print(tabulate(table, headers="firstrow", tablefmt="psql"))

    def md5_matches(self, remote, folder, md5_str):
        if self.archive_mode:
            logging.info("Skipping md5 check as archive mode is enabled")
            return False
        output = self.rclone.lsf(remote, folder['RPath'])
        for val in output:
            if md5_str in val:
                logging.debug("MATCH: '{}' is in '{}'".format(md5_str, val))
                return True
        return False
