"""
Pushes artists that have been added to the whitelist up to chirpradio.
"""

import time

from chirp.library import artists

from chirp.common.printing import cprint
from chirp.common import chirpradio
from djdb import models
from djdb import search


def main():
    for _ in main_generator():
        pass


def main_generator():
    chirpradio.connect()

    dry_run = False

    # Find all of the library artists
    all_library_artists = set(artists.all())

    # Find all of the artists in the cloud.
    all_chirpradio_artists = set()
    mapped = 0
    t1 = time.time()
    for art in models.Artist.fetch_all():
        if art.revoked:
            continue
        std_name = artists.standardize(art.name)
        if std_name != art.name:
            cprint(u"Mapping {}: {} => {}".format(mapped, art.name, std_name))
            mapped += 1
            art.name = std_name
            idx = search.Indexer()
            idx._transaction = art.parent_key()
            idx.add_artist(art)
            if not dry_run:
                idx.save()
        all_chirpradio_artists.add(art.name)
        yield

    to_push = list(all_library_artists.difference(all_chirpradio_artists))

    cprint("Pushing %d artists" % len(to_push))
    while to_push:
        # Push the artists in batches of 50
        this_push = to_push[:50]
        to_push = to_push[50:]
        idx = search.Indexer()
        for name in this_push:
            cprint(name)
            art = models.Artist.create(parent=idx.transaction, name=name)
            idx.add_artist(art)
        if not dry_run:
            idx.save()
        cprint("+++++ Indexer saved")
        yield


if __name__ == "__main__":
    main()
