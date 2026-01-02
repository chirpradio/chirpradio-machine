import sys
import subprocess
import os.path as op
import time
import datetime

from chirp.common.printing import cprint

from .mock_commands import fake_command


def new_artists():
    from chirp.library.do_dump_new_artists_in_dropbox import main_generator
    for _ in main_generator(rewrite=False):
        yield


def update_artist_whitelist():
    from chirp.library import artists
    from chirp.library.do_dump_new_artists_in_dropbox import main_generator
    cwd = op.dirname(artists._WHITELIST_FILE)

    # Make sure the comitted version of the whitelist is checked out.
    # This allows operators to fix mistakes by editing mp3 tags
    # and continuously re-running this task.
    cmd = ['git', 'checkout', artists._WHITELIST_FILE]
    exec_and_print(cmd, cwd)

    # This will reload the artist whitelist file
    # in python memory.
    artists._init()

    for _ in main_generator(rewrite=True):
        yield

    # Show changes to the artist whitelist file
    cprint('Changes made to artist whitelist:')
    cmd = ['git', 'diff', artists._WHITELIST_FILE]
    exec_and_print(cmd, cwd)

    # Once again, this reloads the artist whitelist file
    # in python memory.
    artists._init()


def push_artist_whitelist():
    from chirp.library import artists
    cwd = op.dirname(artists._WHITELIST_FILE)

    # Commit and push.
    cmd = ['git', 'commit', artists._WHITELIST_FILE, '-m', 'Adding new artists']
    exec_and_print(cmd, cwd)
    cmd = ['git', 'push']
    exec_and_print(cmd, cwd)
    cprint('Changes to artist whitelist pushed to git', type='success')

    yield   # to make this function a generator function


def check_music():
    from chirp.library.do_periodic_import import import_albums
    for _ in import_albums(dry_run=True):
        yield


def import_music():
    from chirp.library.do_periodic_import import import_albums
    for _ in import_albums(dry_run=False):
        yield
    cprint('Finished!', type='success')


def generate_traktor():
    from chirp.library.do_generate_collection_nml import main_generator
    for _ in main_generator():
        yield


def upload(date):
    from chirp.library.do_push_artists_to_chirpradio import main_generator
    for _ in main_generator():
        yield

    from chirp.library.do_push_to_chirpradio import main_generator

    # Parse the date string we got from the client.
    dt = datetime.datetime.strptime(date, '%m/%d/%Y')
    cprint('Uploading track changes made since: {:%m/%d/%Y %H:%M}'.format(dt))
    timestamp = time.mktime(dt.timetuple())
    for _ in main_generator(start_timestamp=timestamp):
        yield

    cprint('Finished!', type='success')

def update_mp3s_in_database(song_title, song_artist, album_title, date, tag):
    from chirp.library import database

    db = database.Database("catalog.sqlite3_db")
    matches = []
    cprint('matches length is too long')
    #follows this logic to modify the tab
    # for _ in db._modify_tag(song_title, song_artist, album_title, date, tag):
    #     matches += 1
    #     yield
    if len(matches) > 1:
        matches = prompt_user_to_select_match(matches)
        #extract relevant data to Yi's function to update it
    elif len(matches) == 0:
        cprint('No matches found', type='success')
    else:
        print('MP3 Updated!', type='error')
    
def prompt_user_to_select_match(matches):
    cprint("Multiple matches found. Please select one:")
    for i, match in enumerate(matches):
        cprint(f"{i + 1}.) {match}")  

    while True:
        choice = input("Enter the number of the match to select (or 'q' to cancel): ").strip()
        if choice.lower() == 'q':
            return None
        if choice.isdigit():
            index = int(choice) - 1
            if 0 <= index < len(matches):
                return matches[index]
        print("Invalid choice. Try again.")

def exec_and_print(cmd, cwd):
    cprint(' '.join(cmd), type='highlight')
    output = subprocess.check_output(cmd, cwd=cwd)
    cprint(output)
