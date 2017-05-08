
The CHIRP Radio Machine
=======================

These are a bunch of scripts `CHIRP Radio`_ uses to maintain its music library
and broadcast stream.
For more general info about CHIRP software see the `CHIRP Project`_ page.

.. note::

  WARNING: Currently this is not a turnkey radio station solution. These are
  tailored for use at CHIRP. With that said, pull requests are welcome!
  Feel free to get in touch with any questions.

.. contents::
   :local:

Installation
------------------

You'll need Python 2.7+, `Google App Engine SDK 1.9+`_, `virtualenv`_ and `pip`_.
Change into the source tree, activate a virtualenv, and type these commands::

  pip install -r requirements.txt
  python setup.py develop
  cp settings_local.py-dist settings_local.py

Change the values of the settings variables in `settings_local.py` according to your own preferences and
directory layout. You'll need to manually create empty directories for each setting.
With the default settings, that would look like this:

````
mkdir ~/chirpradio-data/samba
mkdir ~/chirpradio-data/library
mkdir ~/chirpradio-data/tmp
mkdir ~/chirpradio-data/music_dropbox
````

Next, create the local SQL database with the following command:

  python -c "from chirp.common.conf import LIBRARY_DB
  from chirp.library import database
  db = database.Database(LIBRARY_DB)
  db.create_tables()"

.. _`Google App Engine SDK 1.9+`: https://cloud.google.com/appengine/downloads#Google_App_Engine_SDK_for_Python
.. _`virtualenv`: http://pypi.python.org/pypi/virtualenv
.. _`pip`: http://www.pip-installer.org/
.. _`CHIRP Radio`: http://chirpradio.org
.. _`CHIRP Project`: http://code.google.com/p/chirpradio/

Developers
------------------

To run the test suite, type::

  nosetests -v

Please follow `PEP8`_ when writing code.

.. _`PEP8`: http://www.python.org/dev/peps/pep-0008/

Community
-----------

You can reach out to the CHIRP development community on our
`mailing list <http://groups.google.com/group/chirpdev>`_.

Music Library
------------------

.. note::

  This requires a lot of manual sysadmin work and some of it is hard coded
  on our servers. The
  `chirpradio-webcontrol <https://github.com/chirpradio/chirpradio-webcontrol>`_
  project is a web app we're working on to help make it easier.

Here's how to import new music into the digital library so that it's available
for DJs to play on our Traktor machine and also available in the online
DJ Database.

If you're installing the app for the first time,
read through settings.py and add any
necessary settings overrides to settings_local.py.  Here are some of the
crucial settings:

- Set CHIRPRADIO_PATH to your source checkout of the
  `CHIRP Radio internal app code`_.
- Make sure MUSIC_DROPBOX is correct.
- Make sure GOOGLE_APPENGINE_SDK_PATH is set to the latest
  `Google App Engine SDK`_.

.. _`Google App Engine SDK`: http://code.google.com/appengine/
.. _`CHIRP Radio internal app code`: http://code.google.com/p/chirpradio/source/checkout

Running an import
-------------------

To run an import you either need to install the app (instructions above)
or have a server admin grant you permissions to run an import within the CHIRP
studio servers. At CHIRP, all
scripts are run as the ``musiclib`` user.

First, enter into a musiclib shell::

    sudo -u musiclib -i

Next, change into the source directory::

    cd ~/chirpradio-machine

**IMPORTANT**: You should always run an import with `screen`_ or `tmux`_ so that
your SSH connection does not abort a running job.

.. _`screen`: http://www.gnu.org/software/screen/
.. _`tmux`: http://tmux.sourceforge.net/

Step #1: Update the Artist White-list
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run this command to see a list of the artists from the dropbox who are not already in the music library::

  do_dump_new_artists_in_dropbox

Carefully proofread the list of new artists.  If they are all correct, update the whitelist::

  do_dump_new_artists_in_dropbox --rewrite

It's a rare possibility that you will get an error at this stage. Read on to the
import section to see the options for resolving albums that produce errors.

If it ran without errors, proofread the whitelist by viewing the changes in context::

  git diff chirp/library/data/artist-whitelist

If everything looks OK, commit the changes back to git::

  git commit chirp/library/data/artist-whitelist -m "Adding new artists"
  git push

Step #2: Actually Do The Import
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run the import script without any additional args, logging the output to a file::

  do_periodic_import 2>&1 | tee ~/import.log

This might take a while to run.

Next, inspect the log file and see if any errors were reported.  If they were, correct them and try again.  Repeat this process until there are no more errors. **Do not proceed if there are errors.** If you can't resolve them,
just move the culprit album aside temporarily.

Correcting Errors
~~~~~~~~~~~~~~~~~

There is a helper script to set aside albums when they are producing errors.
This lets you continue with an import while the music director can correct the
album and re-upload it. Let's say you hit an error with an album named Hair.
Run this to set it aside::

  sudo `which remove_from_dropbox` '/mnt/disk_array/public/Departments/Music Dept/New Music Dropbox/Hair'

After the problem albums have been set aside and you were able to do a dry-run
without any errors, you can proceed
with an additional flag to actually go ahead with the import.

However, it's really important that you don't interrupt this script
while it's running. Be sure your SSH session will not timeout by using
`screen <http://www.gnu.org/software/screen/>`_ or something like that.
Using screen is the best way to go through an import process.

::

  do_periodic_import --actually-do-import

Again, do not interrupt the import script while it is running!

At this point everything in the dropbox has been imported, so it is safe to clean it out.
This command will remove all files::

  sudo `which empty_dropbox`


Step #3: Prepare a New NML File For Traktor
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This command will create a file named ``output.nml`` in the current directory::

  do_generate_collection_nml

Note that for this command to work, you must have a ```traktor`` group in your
system, and the current user must be in that group. You also need to have set
the settings variable ``TRAKTOR_NML_FILE`` to a valid path.

At this point Traktor can be switched over to the new collection
whereby you shut down Traktor, rename ``new-collection.nml`` to ``collection.nml``
and restart Traktor.

Step #4: Upload New Data to the DJ Database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First, upload the new artists::

  do_push_artists_to_chirpradio

To upload the album and track information, you must specify a "start timestamp" that tells the system which part of the library to upload.  Each library import covers one or more timestamps, which are of the form "YYYYMMDD-HHMMSS".   The timestamps are printed during the main import.  It is usually OK to just use a timestamp corresponding to the date of the import with the time-of-day set to 0.  For example, if you are importing on April 3rd 2011, you would use a start timestamp of "20110403-000000".

::

  do_push_to_chirpradio --start-at=20120115-000000

If you don’t see any output from this command you probably entered the wrong timestamp.  It should show you verbose output of all the new albums uploading to App Engine.


Stream Archiver
------------------

The stream archiver no longer runs from this code repository.
You can find the new archiver and read about how it works at
`chirpradio-archiver <https://github.com/chirpradio/chirpradio-archiver/>`_.
The old archiver code is still available in
``chirp/stream/archiver.py`` for historic reasons.

Stream Monitor
------------------

To check if the stream is up and see some basic stats, there's a small web
page you can take a look at.
This daemon currently runs as the ``barix`` user in production.

To start the web server type::

  ./bin/run_proxy_barix_status.sh

.. note::

  Currently this assumes you installed into a virtualenv at
  ~/.virtualenvs/chirpradio-machine/
