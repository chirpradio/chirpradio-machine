from setuptools import setup, find_packages


with open('requirements/prod.txt') as fp:
    requires = [
        line.strip() for line in fp.readlines() if not line.startswith('#')
    ]


setup(
    name='chirp',
    version='2.0',
    description="",
    long_description="""""",
    author='Jon Trowbridge, Kumar McMillan',
    author_email='kumar.mcmillan@gmail.com',
    license="Apache License",
    packages=find_packages(exclude=['ez_setup']),
    install_requires=requires,
    url='',
    include_package_data=True,
    entry_points="""
       [console_scripts]

       do_dump_new_artists_in_dropbox = chirp.library.do_dump_new_artists_in_dropbox:main
       do_periodic_import = chirp.library.do_periodic_import:main
       do_generate_collection_nml = chirp.library.do_generate_collection_nml:main
       do_push_artists_to_chirpradio = chirp.library.do_push_artists_to_chirpradio:main
       do_push_to_chirpradio = chirp.library.do_push_to_chirpradio:main
       remove_from_dropbox = chirp.library.remove_from_dropbox:main
       empty_dropbox = chirp.library.empty_dropbox:main

       do_delete_audio_file_from_db = chirp.library.do_delete_audio_file_from_db:main
       do_archive_stream = chirp.stream.do_archive_stream:main
       do_proxy_barix_status = chirp.stream.do_proxy_barix_status:main
       """,
    classifiers=[],
    )
