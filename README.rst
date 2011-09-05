
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

You'll need Python greater than 2.5, `virtualenv`_ and `pip`_.
Change into the source tree, activate a virtualenv, and type these commands::

  pip install -r requirements.txt
  python setup.py develop
  cp settings_local.py-dist settings_local.py


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

Music Library
------------------

.. note::

  This requires a lot of manual sysadmin work and some of it is hard coded
  on our servers. At some point it will hopefully be available as a web app.
  Get in touch if you'd like to help!

Here's how to import new music into the digital library so that it's available
for DJs to play on our Traktor machine and also available in the online
DJ Database.  First, be sure to read through settings.py and add any
necessary settings overrides to settings_local.py.  Here are some of the
crucial settings:

- Set CHIRPRADIO_PATH to your source checkout of the
  `CHIRP Radio internal app code`_.
- Make sure MUSIC_DROPBOX is correct.
- Make sure GOOGLE_APPENGINE_SDK_PATH is set to the latest
  `Google App Engine SDK`_.

.. _`Google App Engine SDK`: http://code.google.com/appengine/
.. _`CHIRP Radio internal app code`: http://code.google.com/p/chirpradio/source/checkout

Next, change into the root directory and run these commands:

Step #1: Update the Artist White-list
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run this command to see a list of the artists from the dropbox who are not already in the music library::

  do_dump_new_artists_in_dropbox

Carefully proofread the list of new artists.  If they are all correct, update the whitelist::

  do_dump_new_artists_in_dropbox --rewrite

Now proofread the whitelist by viewing the changes in context::

  svn diff chirp/library/data/artist-whitelist

If everything looks OK, common the changes back to Subversion::

  svn commit chirp/library/data/artist-whitelist -m "Adding new artists"

Step #2: Actually Do The Import
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run the import script without any additional args, logging the output to a file::

  do_periodic_import >& ~/import.log

This might take a while to run.

Next, inspect the log file and see if any errors were reported.  If they were, correct them and try again.  Repeat this process until there are no more errors. **Do not proceed if there are errors.** If you can't resolve them,
just move the culprit album aside temporarily.

Now re-run the import script with an additional flag telling to actually go ahead with the import.  This currently requires root privileges.

::

  sudo `which do_periodic_import` --actually-do-import

Do not interrupt the import script while it is running!

At this point everything in the dropbox has been imported, so it is safe to clean it out::

  ls path/to/dropbox
  sudo rm -rf path/to/dropbox/*

Finally, run a script to copy the newly-added files to the backup drive::

  ~trow/backup-lib.sh

Step #3: Prepare a New NML File For Traktor
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This command will create a file named ``output.nml`` in the current directory::

  do_generate_collection_nml

Copy the new NML into Traktor's root directory::

  NEW_NML=/samba/traktor/TraktorProRootDirectory/new-collection.nml
  sudo install -o traktor -g traktor output.nml $NEW_NML

At this point Traktor can be switched over to the new collection.

Step #4: Upload New Data to the DJ Database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First, upload the new artists::

  do_push_artists_to_chirpradio

To upload the album and track information, you must specify a "start timestamp" that tells the system which part of the library to upload.  Each library import covers one or more timestamps, which are of the form "YYYYMMDD-HHMMSS".   The timestamps are printed during the main import.  It is usually OK to just use a timestamp corresponding to the date of the import with the time-of-day set to 0.  For example, if you are importing on April 3rd 2011, you would use a start timestamp of "20110403-000000".

::

  TIMESTAMP=20110403-000000
  do_push_to_chirpradio --start-at=$TIMESTAMP

If you don’t see any output from this command you probably entered the wrong timestamp.  It should show you verbose output of all the new albums uploading to App Engine.


Stream Archiver
------------------

The stream archiver writes out mp3 archives of the stream in one hour chunks.
To fire it up switch to the archiver user and type::

  ./bin/run_archiver.sh

.. note::

  Currently this assumes you installed into a virtualenv at
  ~/.virtualenvs/chirpradio-machine/


Stream Monitor
------------------

To check if the stream is up and see some basic stats, there's a small web 
page you can take a look at.
To start the web server for this, switch to the archiver user and type::

  ./bin/run_proxy_barix_status.sh

.. note::

  Currently this assumes you installed into a virtualenv at
  ~/.virtualenvs/chirpradio-machine/
