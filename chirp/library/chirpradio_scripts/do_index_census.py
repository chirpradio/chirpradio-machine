
import codecs

from chirp.common import chirpradio
from djdb import models


def all_matches():
    last_key = None
    while True:
        q = models.SearchMatches.all().order("__key__")
        if last_key:
            q.filter("__key__ >", last_key)
        batch = list(q.fetch(100))
        if not batch:
            break
        last_key = batch[-1].key()
        for sm in batch:
            yield sm


chirpradio.connect()

counts = {}

total_obj = 0
total_matches = 0
for sm in all_matches():
    key = (sm.term, sm.field)
    L = counts.get(key)
    if not L:
        L = counts[key] = []
    L.append(len(sm.matches))
    total_obj += 1
    total_matches += len(sm.matches)
    if total_obj % 500 == 0:
        print total_obj, total_matches
    

print total_obj, total_matches

out = codecs.open("index.data", "w", "utf-8")
for (term, field), L in counts.iteritems():
    out.write(u"%s, %s, %d, %d\n" % (term, field, len(L), sum(L)))
out.close()
