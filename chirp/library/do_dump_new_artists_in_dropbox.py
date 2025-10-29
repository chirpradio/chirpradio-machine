#!/usr/bin/env python

import codecs
import sys
from chirp.common.printing import cprint
from chirp.common.input import cinput
from chirp.library import artists
from chirp.library import dropbox



def main_generator(rewrite, test=False, update_artists=False, update_drop=False):

    drop = dropbox.Dropbox()
    if test:
        if update_artists:
            update_artists(artists)
        if update_drop:
            update_drop(drop)
    print(artists._complete_whitelist)
    print(artists._collision_mappings)
    print(drop._path)

    new_artists = set()


    for au_file in drop.tracks():
        try:
            tpe1 = au_file.mutagen_id3["TPE1"].text[0]
        except:
            cprint('** file: %r' % au_file.path)
            raise

        if not rewrite:
            new_artists.add(tpe1)
        else:
            collisions = artists.check_collisions(tpe1)
            if collisions:
                collisions.sort()
                cl_inpt = cinput(f"Multiple potential matches found for {tpe1}. Choose which is correct.",
                                 collisions, allow_custom=False)
                au_file.mutagen_id3["TPE1"].text[0] = cl_inpt
                new_artists.add(cl_inpt)
                au_file.mutagen_id3.save(au_file.path)
            
            else:
                standardized_name = artists.standardize(tpe1)
                if not standardized_name:
                    new_artists.add(tpe1)
                elif standardized_name != tpe1:
                    bp_inpt = cinput(f"Correct {tpe1} to {standardized_name}?", ["Yes (default)","No"], allow_custom=False)
                    if(bp_inpt == "No"): #Breakpoint passed
                        new_artists.add(tpe1)
                    else:
                        au_file.mutagen_id3["TPE1"].text[0] = standardized_name
                        au_file.mutagen_id3.save(au_file.path)

    to_print = set(new_artists)
    if rewrite:
        to_print.update(set(artists.all()))
    to_print = list(to_print)
    to_print.sort(key=artists.sort_key)

    output = None
    if rewrite:
        output = codecs.open(artists._WHITELIST_FILE, "w", "utf-8")
    for tpe1 in to_print:
        if output:
            output.write(tpe1)
            output.write("\n")
        else:
            cprint(tpe1)
        yield

    if rewrite:
        cprint('Artist whitelist updated', type='success')
    else:
        cprint('Found %d new artists' % len(to_print), type='success')


def main():
    for _ in main_generator(rewrite="--rewrite" in sys.argv):
        pass


if __name__ == "__main__":
    main()
