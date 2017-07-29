"""The installation script for the iitech3 program."""
from sys import platform
import argparse
import os
import stat
import re
import pip

# Since this will be a CLI program and not a python library, we will not be using distutils

metadata = {}
with open('src/version.py', 'r') as file:
    exec(file.read(), metadata)

with open('README.md', 'r') as file:
    long_descr = file.read()


def fix_and_copy(src, dest_dir, repairs):
    """Implement repairs on a file before copying it, leaving the original file untouched."""
    with open(src, 'r') as file:
        code = file.read()

    for r in repairs:
        code = re.sub(r[0], r[1], code, flags=re.M)

    with open(os.path.join(dest_dir, os.path.basename(src)), 'w') as file:
        file.write(code)


# Configuration Constants
if platform == 'darwin':  # Mac OS X
    DATA_DIR = os.path.join('/usr/local/var', metadata['__title__'])
    LIB_DIR = os.path.join('/usr/local/lib', metadata['__title__'])
    BIN_FILE = os.path.join('/usr/local/bin', metadata['__title__'])
    WHICH_PYTHON = '/usr/bin/env python3'
else:
    raise RuntimeError('Unrecognized Platform')

SRC_FILES = [os.path.join('src/', name) for name in os.listdir('src/') if os.path.splitext(name)[1] == '.py']
REPAIRS = [
    (r'^DB_PATH.*#', "DB_PATH = '{:s}'  #".format(os.path.join(DATA_DIR, 'cache.db'))),
    (r'^#!.*$', '#! {:s}'.format(WHICH_PYTHON))
]


# Action functions
def install():
    """Install iitech3 on this system."""
    pip.main("install requests==2.13.0".split())
    pip.main("install beautifulsoup4==4.5.3".split())
    pip.main("install PyYAML==3.12".split())
    pip.main("install Pillow==4.1.0".split())

    os.makedirs(LIB_DIR, exist_ok=True)
    for f in SRC_FILES:
        fix_and_copy(f, LIB_DIR, REPAIRS)
    try:
        os.remove(BIN_FILE)
    except FileNotFoundError:
        pass
    os.symlink(os.path.join(LIB_DIR, 'main.py'), BIN_FILE)
    os.chmod(BIN_FILE, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)


if __name__ == '__main__':
    base = argparse.ArgumentParser()
    base.set_defaults(func=lambda: base.print_help())
    base_childs = base.add_subparsers(title='commands')

    install_parser = base_childs.add_parser('install',
                                            description='Install the iitech3 command line program.')
    install_parser.set_defaults(func=install)
    base.parse_args().func()
