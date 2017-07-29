"""The installation script for the iitech3 program."""
from sys import platform
import argparse
import os
import subprocess
import shutil
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
    try:
        cmd = subprocess.run((metadata['__title__'], '--version'), stdout=subprocess.PIPE)
        IS_INSTALLED = True
        INSTALLED_VERSION = cmd.stdout.split()[1]
    except FileNotFoundError:
        IS_INSTALLED = False
else:
    raise RuntimeError('Unrecognized Platform')

DEPENDENCIES = [
    'requests==2.13.0',
    'beautifulsoup4==4.5.3',
    'html5lib==0.999999999'
]
SRC_FILES = [os.path.join('src/', name) for name in os.listdir('src/') if os.path.splitext(name)[1] == '.py']
REPAIRS = [
    (r'^DB_PATH.*#', "DB_PATH = '{:s}'  #".format(os.path.join(DATA_DIR, 'cache.db'))),
    (r'^#!.*$', '#! {:s}'.format(WHICH_PYTHON))
]


# Action functions
def remove(args):
    """Remove the program from the system."""
    if not IS_INSTALLED:
        exit('Nothing to do.')
    if args.purge:
        print('Uninstalling dependencies using pip:')
        for d in DEPENDENCIES:
            pip.main('uninstall {:s}'.format(d).split())
    print('Removing user data.')
    shutil.rmtree(DATA_DIR, ignore_errors=True)
    print('Removing program library.')
    shutil.rmtree(LIB_DIR, ignore_errors=True)
    print('Removing program shortcut.')
    try:
        os.remove(BIN_FILE)
    except FileNotFoundError:
        pass
    print('Uninstalled {:s}'.format(INSTALLED_VERSION))


def install(args):
    """Perform a clean (re)install of the program."""
    if IS_INSTALLED:
        if not args.reinstall:
            exit('The program is already installed.\n'
                 'Please use install --r to reinstall it.\n'
                 'Or use refresh to upgrade it.')
        answer = 'ask'
        while answer not in ('yes', 'no'):
            answer = input('This will OVERWRITE any existing data. Do you want to continue (yes/no)? ')
            if answer not in ('yes', 'no'):
                print("Please enter 'yes' or 'no'.")
        if answer == 'no':
            exit('Operation aborted.')
        args.purge = True
        remove(args)
        refresh(args)
    else:
        refresh(args)


def refresh(args):
    """Refresh the program using the files in this directory."""
    print('Install dependencies using pip.')
    for d in DEPENDENCIES:
        pip.main('install {:s}'.format(d).split())
    print('Copying program library.')
    os.makedirs(LIB_DIR, exist_ok=True)
    for f in SRC_FILES:
        fix_and_copy(f, LIB_DIR, REPAIRS)
    print('Adding shortcut to {:s}.'.format(os.path.dirname(BIN_FILE)))
    try:
        os.remove(BIN_FILE)
    except FileNotFoundError:
        pass
    os.symlink(os.path.join(LIB_DIR, 'main.py'), BIN_FILE)
    os.chmod(BIN_FILE, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    print('Installed {0[__title__]:s} {0[__version__]:s}'.format(metadata))


if __name__ == '__main__':
    base = argparse.ArgumentParser()
    base.set_defaults(func=lambda x: base.print_help())
    base_childs = base.add_subparsers(title='commands')

    install_parser = base_childs.add_parser('install',
                                            description='Install the program.')
    install_parser.set_defaults(func=install)
    install_parser.add_argument('-r', '--reinstall', action='store_true',
                                help='Reinstall the program even if it already exists.')

    remove_parser = base_childs.add_parser('remove',
                                           description='Remove the program.')
    remove_parser.set_defaults(func=remove)
    remove_parser.add_argument('-p', '--purge', action='store_true',
                               help='Remove the program dependencies as well.')

    refresh_parser = base_childs.add_parser('refresh',
                                            description='Repair/Upgrade the program.')
    refresh_parser.set_defaults(func=refresh)

    args = base.parse_args()
    args.func(args)
