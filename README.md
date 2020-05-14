st-backup
=========

A python script that I use to upload [Syncthing](https://syncthing.net/) folders to multiple cloud storage solutions such as Google Drive or Dropbox - also some other folders not managed by Syncthing itself.

# Why

I wanted a daily backup script which could compress & encrypt selected folders and upload (if needed) to multiple cloud storage solutions (remotes), just in case my hdds die (they do).

Python is fun.

Also I wanted to apply some constraints before uploading the folders:

- For each remote, a different set of folders
- For each remote, for each folder: have a different minimum of modified files to backup (only Syncthing)
- For each folder a different set of days of the week to backup
- If all the above is true, an md5 checksum before uploading (maybe files were added and then removed, so checksum is the same, or other reasons)
- For each remote, for each folder: have a different maximum amount of backups stored, delete the oldest
- An "Archiving mode" were backups won't get autodeleted or count to the maximum amout
