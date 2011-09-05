import codecs
import time
import urllib2

from chirp.common import chirpradio
from google.appengine.api import datastore_errors
from djdb import search

chirpradio.connect()

terms_to_opt = set()
for line in codecs.open("index.data", "r", "utf-8"):
    F = [f.strip() for f in line.split(",")]
    if F[2] == "1":
        continue
    terms_to_opt.add(F[0])

deleted = 0
skipping = True
for term in terms_to_opt:
    if skipping and term:
        skipping = False
    if skipping:
        continue
    attempt = 1
    while True:
        try:
            n = search.optimize_index(term)
            break
        except (datastore_errors.Timeout, urllib2.URLError):
            attempt += 1
            print "Timeout on attempt %d for %s!" % (attempt,
                                                     term.encode("utf-8"))
            time.sleep(2)
    deleted += n
    print term.encode("utf-8"), n, deleted
    
