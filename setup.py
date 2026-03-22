# this is for building an app with py2app for macos
# this was ai generated bc i have no clue how to use py2app so if it sucks im sorry

from setuptools import setup

APP = ['main.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'packages': ['PIL', 'imageio', 'av'],
    'includes': ['imageio_ffmpeg'],
    'excludes': ['PyInstaller', 'PyQt5'],
}

setup(
    app=APP,
    name='Sayo Device GIF Maker',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
