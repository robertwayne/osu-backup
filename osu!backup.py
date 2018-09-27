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

logging.basicConfig(filename='debug.log', level=logging.DEBUG)
BACKUP_PATH = './backup'
WINDOWS_USER = getlogin()


def get_time():
    return str(datetime.datetime.utcnow()) + ': '


def backup_procedure():
    file_strings = ['osu!.db', 'collection.db', 'scores.db', 'osu!.cfg', f'osu!.{WINDOWS_USER}.cfg']
    directories = ['Screenshots', 'Replays']

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
                        elif stat(f'{directory}/{file}').st_mtime - stat(f'{BACKUP_PATH}/{directory}/{file}').st_mtime > 1:
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
                        logging.error(get_time() + 'Could not remove ' + str(file) + ' in ' + str(directory), exc_info=True)


def archive():
    make_archive('backup-{}'.format(datetime.date.today()), 'zip', root_dir=BACKUP_PATH)
    logging.info(get_time() + 'Successfully created archive of backup directory')


# TODO: Implement upload to a Google Drive
# TODO: Implement sync: check Drive for file first, if False check for local files, if False, create files?
def sync():
    return False


def main():
    if not path.isdir(f'{BACKUP_PATH}'):
        try:
            mkdir(f'{BACKUP_PATH}')
            logging.info(str(datetime.datetime.utcnow()) + f': Created backup directory at {BACKUP_PATH}')
        except OSError:
            logging.info(str(datetime.datetime.utcnow()) + ': Failed to create directory', exc_info=True)

    try:
        backup_procedure()
    finally:
        archive()
        # sync()


if __name__ == '__main__':
    schedule.every().hour.do(main)
    while True:
        schedule.run_pending()
        time.sleep(60)
