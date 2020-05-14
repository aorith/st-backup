import os
import logging


def cleanup(cfg):
    logging.info("Cleaning up!")
    cfg.setup_rclone(update=False)
    for folder in cfg.folders:
        if os.path.isfile(folder['Tar']):
            logging.debug("Deleting {}".format(folder['Tar']))
            os.remove(folder['Tar'])
        if os.path.isfile(folder['BackupReady']):
            logging.debug("Deleting {}".format(folder['BackupReady']))
            os.remove(folder['BackupReady'])

    # clean the older backup from each folder when maxbackups is reached
    for remote in cfg.remotes:
        logging.info("<< Cleaning {} >>".format(remote.name))
        output = cfg.rclone.lsf(remote, cfg.remote_root,
                                use_ls=True, ls_depth='9')

        # create a dict to store current count of backups for each folder and the oldest file
        backupdict = dict()
        for f in cfg.folders:
            backupdict.update({f.name: 0,
                               f.name + '_max': None,
                               f.name + '_oldest': None})

        for line in output:
            line = line.split()[1]
            # skip Archived backups
            if os.path.basename(line).startswith('ARC'):
                continue
            # try to get the folder alias
            falias = os.path.split(os.path.split(line)[0])[1]
            folder = cfg.get_folder_by_alias(falias)
            if folder is None:
                continue
            # get maxbackups for this folder
            val = cfg.get_folder_cfg_by_remote(remote, folder)
            if val is None:
                # folder is not configured in this remote (maybe it was before) skipping it
                continue
            maxbackups, _ = val
            new_count = backupdict[folder.name] + 1
            # update oldest file
            if backupdict[folder.name + '_oldest'] == None:
                backupdict[folder.name + '_oldest'] = line
            else:
                try:
                    curr_timestamp = int(os.path.basename(line).split('_')[0])
                    stored_timestamp = int(os.path.basename(
                        backupdict[folder.name + '_oldest']).split('_')[0])
                    if curr_timestamp < stored_timestamp:
                        backupdict[folder.name + '_oldest'] = line
                except Exception as ex:
                    logging.error(
                        "This should not happen, offending line is:\n{}".format(line))

            # update the dict on each line
            backupdict.update(
                {folder.name: new_count, folder.name + '_max': maxbackups})

        # now proceed at cleaning this remote
        for folder in cfg.folders:
            curr_count = int(backupdict[folder.name])
            maxbackups = backupdict[folder.name + '_max']
            if maxbackups is None:
                # folder is probably not configured in this remote
                continue
            maxbackups = int(maxbackups)
            if curr_count <= maxbackups:
                # don't need to clean
                logging.debug("R:{} - F:{} - {}/{} (curr/max) - skipping...".format(
                    remote.name, folder.name, curr_count, maxbackups))
                continue
            # ok, we have to clean this
            frpath = cfg.remote_root + '/' + \
                backupdict[folder.name + '_oldest']
            logging.info("{} - {}/{} (current/maxbackups) deleting --> {}".format(
                folder.name, curr_count, maxbackups, frpath))
            cfg.rclone.delete(remote, frpath)

    logging.info("Finished!")
