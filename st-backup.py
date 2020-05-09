#!/usr/bin/env python3
import os
import sys
import argparse
import logging
from datetime import datetime

from lib.stconfig import Config
from lib.timer import timer
from lib.tarpress import compress, create_tar
from lib.gpgwrapper import gpg_encrypt
from lib.md5 import md5
from lib.cleanup import cleanup


def get_args():
    parser = argparse.ArgumentParser(description='st-backup')
    subparsers = parser.add_subparsers(dest='mode')
    subparsers.required = True

    subp_showconfig = subparsers.add_parser(
        'showconfig', help='Show current config.')
    subp_backup = subparsers.add_parser(
        'backup', help='Run backup mode.')
    subp_backup.add_argument('-a', '--archive', action='store_true', required=False,
                             help='Archive the backups: Ignores md5sum, minfiles and schedule requisites to perform a backup, also bypasses the cleaning that is performed when maxbackups is reached.')
    subp_listbackups = subparsers.add_parser(
        'list', help='List backups on the remotes.')
    subp_listbackups.add_argument('-r', '--remotealias', nargs=1, type=str, required=False, default=None,
                                  help='Specify a remote alias to filter by it')
    subp_listbackups.add_argument('-f', '--folderalias', nargs=1, type=str, required=False, default=None,
                                  help='Specify a folder alias to filter by it')
    subp_lastmodified = subparsers.add_parser(
        'last', help='Parse the audit_log and list modified files.')

    return parser.parse_args()


@timer
def prepare_backup(cfg, remote, folder):
    logging.info("Preparing folder {}...".format(folder.name))
    curr_time = datetime.now().strftime("%Y%m%d%H%M%S")

    # check if we've got the md5sum and if we have the tarball ready
    # if we are here, it's because BackupReady == 'False'
    if folder['Tar'] == 'None':
        # we need to tarball
        tar_name = curr_time + '_' + folder.name + '.tar'
        tar_path = os.path.join(cfg.workdir, tar_name)
        # create the archive
        create_tar(folder['Path'], tar_path)
        folder['Tar'] = tar_path
        # check its md5
        folder['MD5'] = md5(tar_path)
        if cfg.md5_matches(remote, folder, folder['MD5']):
            # store 'False' in folder['BackupReady']
            logging.info("Skipping folder {} as md5 matches in {}".format(
                folder.name, remote.name))
            return 'False'
    else:
        # we already have the tarball and the md5sum
        logging.info("Tar is ready, checking md5...")
        if cfg.md5_matches(remote, folder, folder['MD5']):
            # we won't go ahead compressing and encrypting as the md5 matches
            logging.info("Skipping folder {} as md5 matches in {}".format(
                folder.name, remote.name))
            # return contents of BackupReady, either False or the path of the prepared backup
            return folder['BackupReady']

    # compress and encrypt
    compressed_name = compress(folder['Tar'])
    encrypted_name = gpg_encrypt(compressed_name, cfg.recipients)
    extension = '.' + encrypted_name.split(".", 1)[-1]

    # if we are in archive mode, remove the MD5 string and add ARC
    if cfg.archive_mode:
        backup_path = 'ARC_' + curr_time + '_' + folder.name + extension
    else:
        backup_path = curr_time + '_' + \
            folder['MD5'] + '_' + folder.name + extension

    backup_path = os.path.join(cfg.workdir, backup_path)
    os.rename(encrypted_name, backup_path)
    # store backup_path in folder['BackupReady']
    return backup_path


@timer
def upload(cfg, remote, folder):
    logging.info("Uploading {}".format(folder['BackupReady']))
    ret, output = cfg.rclone.upload(
        remote.name, folder['BackupReady'], folder['RPath'])
    if ret != 0:
        logging.error("The upload failed.\n{}".format(output))
    else:
        logging.info("Upload for {} complete !!!".format(folder.name))


@timer
def backup(cfg):
    logging.info("Starting backup mode...")
    cfg.setup_rclone()
    for remote in cfg.remotes:
        logging.info("<<< --- %s --- >>>", remote.name)
        # skip if disabled
        if remote['Enabled'].lower() != 'true':
            logging.info("Skipping this remote as it's disabled")
            continue

        cfg.showremoteconfig(remote)
        for folder in cfg.folders:
            # skip folders that do not meet the reqs for backup
            if not cfg.should_backup(remote, folder):
                continue
            # folder needs a backup
            logging.info(
                "<<< Folder {} needs a backup >>>".format(folder.name))
            # check if we already have the encrypted backup for this folder
            if folder['BackupReady'] == 'False':
                folder['BackupReady'] = prepare_backup(cfg, remote, folder)
                # if it's still false, we've skipped
                if folder['BackupReady'] == 'False':
                    continue
            elif cfg.md5_matches(remote, folder, folder['MD5']):
                logging.info("Skipping folder {} as md5 matches in {}".format(
                    folder.name, remote.name))
                continue

            logging.info("{} is prepared to upload: {}".format(
                folder.name, folder['BackupReady']))
            file_size = os.path.getsize(folder['BackupReady'])
            if not cfg.rclone.check_space(remote, file_size):
                logging.warning(
                    "There isn't enough space in the remote: {} to upload the backup".format(remote.name))
                continue
            # all ready to upload
            upload(cfg, remote, folder)


def main():
    #log_fmt='[%(asctime)s][%(module)+15s][%(levelname)+8s] %(message)s'
    log_fmt = '[%(asctime)s][%(levelname)+8s] %(message)s'
    logging.basicConfig(
        format=log_fmt, datefmt='%Y.%m.%d %H:%M:%S', level=logging.INFO)
    logging.info('Started')
    cfg = Config(get_args(), os.path.dirname(os.path.realpath(__file__)))

    if cfg.args.mode == 'showconfig':
        cfg.showconfig()
    elif cfg.args.mode == 'backup':
        backup(cfg)
        cleanup(cfg)
    elif cfg.args.mode == 'list':
        cfg.listbackups(ralias=cfg.args.remotealias,
                        falias=cfg.args.folderalias)
    elif cfg.args.mode == 'last':
        cfg.lastmodified()


if __name__ == '__main__':
    main()
