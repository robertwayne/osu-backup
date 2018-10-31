#############################################################
#   osu!backup is a python script that provides regular     #
#   local and online backups of your scores.db, skins,      #
#   osu.db, in-game settings, collections.db,               #
#   replays, and screenshots files.                         #
#                                                           #
#   It offers support for syncing between computers.        #
#############################################################

import datetime
import logging
import time
from os import mkdir, path, getlogin, stat, walk, remove
from shutil import copytree, copy2, make_archive

import schedule

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

logging.basicConfig(filename='debug.log', level=logging.DEBUG)
BACKUP_PATH = './osu!backup'
DRIVE_DIRECTORY = 'osu!backup'
LOGGED_IN_USER = getlogin()

file_strings = ['osu!.db', 'collection.db', 'scores.db', 'osu!.cfg', f'osu!.{LOGGED_IN_USER}.cfg']
directories = ['Screenshots', 'Replays']

gauth = GoogleAuth()
drive = GoogleDrive()


def get_time():
    return str(datetime.datetime.utcnow()) + ': '


def backup_procedure():
    for file in file_strings:
        try:
            if not path.exists(f'{BACKUP_PATH}/{file}'):
                copy2(file, BACKUP_PATH)
                logging.info(get_time() + 'Initial backup successful: ' + str(file))
            elif stat(file).st_mtime - stat(f'{BACKUP_PATH}/{file}').st_mtime > 1:
                copy2(file, BACKUP_PATH)
                logging.info(get_time() + 'Backup successful: ' + str(file))
        except OSError:
            logging.error(get_time() + 'Could not backup ' + str(file), exc_info=True)

    # Look through local directories; add directory if it does not exist.
    for directory in directories:
        try:
            if not path.exists(f'{BACKUP_PATH}/{directory}'):
                copytree(directory, f'{BACKUP_PATH}/{directory}')
                logging.info(get_time() + 'Initial backup successful: ' + str(directory))
            elif stat(directory).st_mtime == stat(f'{BACKUP_PATH}/{directory}').st_mtime:
                pass
            else:
                # Look through local files compared to backup files; create if non-existent, update only if changed.
                for root, dirs, files in walk(directory):
                    for file in files:
                        if not path.exists(f'{BACKUP_PATH}/{directory}/{file}'):
                            copy2(f'{directory}/{file}', f'{BACKUP_PATH}/{directory}/{file}')
                            logging.info('Successfully added ' + file + ' in ' + str(directory))
                        elif stat(f'{directory}/{file}').st_mtime - \
                                stat(f'{BACKUP_PATH}/{directory}/{file}').st_mtime > 1:
                            copy2(f'{BACKUP_PATH}/{file}', f'{BACKUP_PATH}/{directory}/{file}')
                            logging.info('Successfully updated ' + file + ' in ' + str(directory))
        except OSError:
            logging.error(get_time() + 'Could not backup ' + str(directory), exc_info=True)

    # Look for local files in the backup directory which no longer exist and delete them.
    for directory in directories:
        for root, dirs, files in walk(f'{BACKUP_PATH}/{directory}'):
            for file in files:
                try:
                    if not path.exists(f'{directory}/{file}'):
                        remove(f'{BACKUP_PATH}/{directory}/{file}')
                        logging.info('Successfully removed ' + str(file) + ' from ' + str(directory))
                except OSError:
                    logging.error(get_time() + 'Could not remove ' + str(file) + ' in '
                                  + str(directory), exc_info=True)


def archive():
    current_date = datetime.date.today()

    try:
        # root_dir and base_dir must be set like that to avoid the archive adding itself to archives
        make_archive(f'backup-{current_date}', 'zip', root_dir=BACKUP_PATH)
        logging.info(get_time() + 'Successfully created archive of backup directory')
    except OSError:
        logging.error(get_time() + 'Could not create archive', exc_info=True)


def sync():
    directory_list = drive.ListFile({'q': "'root' in parents and trashed=false"}).GetList()
    try:
        if not path.exists(f'{BACKUP_PATH}/drive_settings.txt'):
            # check if drive folder exists under title; if yes - create settings.txt w/ ID if no - create folder & local
            for directory in directory_list:
                if directory['title'] == DRIVE_DIRECTORY:
                    directory_id = directory['id']
                    create_drive_settings(directory_id)
                    print('dir found, created settings.txt')
                    break
                else:
                    # uh... create the directory, then create the settings file (dir func returns ID so pass it in)...
                    create_drive_settings(create_drive_directory())
                    print('upload new dir')
                    break
    finally:
        for directory in directory_list:
            local_file = open(f'{DRIVE_DIRECTORY}/drive_settings.txt', 'r')
            directory_id = local_file.readline()
            local_file.close()

            if directory['id'] == directory_id:
                for root, dirs, files in walk(top='.'):
                    for file in files:
                        if file.startswith('backup') and file.endswith('.zip'):
                            f = drive.CreateFile({'title': file.title().lower(),
                                                  'parents': [{'id': directory_id}],
                                                  'mimeType': 'application/zip'})
                            f.SetContentFile(f'{file}')

                            drive_files = drive.ListFile(
                                {'q': f"'{directory_id}' in parents and trashed=false"}).GetList()
                            if not drive_files:
                                f.Upload()
                            elif drive_files:
                                for drive_file in drive_files:
                                    if drive_file['mimeType'] == 'application/zip':
                                        if drive_file['title'] == file.title().lower():
                                            drive_file.Delete()
                                            f.Upload()


def delete_local_archive():
    for root, dirs, files in walk('.'):
        for file in files:
            if file.startswith('backup') and file.endswith('.zip'):
                remove(file)
                print('removed local archive')


# take a drive folder ID and write it to drive_settings.txt
def create_drive_settings(directory_id):
    local_file = open(f'{BACKUP_PATH}/drive_settings.txt', 'w')
    local_file.write(directory_id)
    local_file.close()
    print('dir found, created settings.txt')


def create_drive_directory():
    d = drive.CreateFile({'title': DRIVE_DIRECTORY,
                          'mimeType': 'application/vnd.google-apps.folder'})
    d.Upload()
    directory_id = d['id']

    return directory_id


def main():
    if not path.isdir(f'{BACKUP_PATH}'):
        try:
            mkdir(f'{BACKUP_PATH}')
            logging.info(get_time() + f': Created backup directory at {BACKUP_PATH}')
        except OSError:
            logging.info(get_time() + ': Failed to create directory', exc_info=True)

    backup_procedure()


if __name__ == '__main__':
    logging.info(get_time() + 'Started running...')

    schedule.every().hour.do(main)
    schedule.every().day.do(archive)
    schedule.every().day.do(sync)
    schedule.every(25).hours.do(delete_local_archive())

    while True:
        schedule.run_pending()
        time.sleep(60)
