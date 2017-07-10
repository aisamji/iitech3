#! /usr/bin/env python3
"""The main script that serves as the program entry point."""

__author__ = 'Ali I Samji'
__version__ = '0.1.0'

import argparse
from requests.status_codes import _codes as url_statuses
import document
import pasteboard
import cache


def review(args):
    """Perform a review operation specified by the given arguments."""
    if args.file is None:
        code = pasteboard.get()
    else:
        with open(args.file, 'r') as file:
            code = file.read()
    html_doc = document.Document(code)
    html_doc.review()

    if args.file is None:
        pasteboard.set(html_doc)
    else:
        with open(args.file, 'w') as file:
            file.write(str(html_doc))


def lookup_email(args):
    """Perform a Cache.get_email as specified by the given arguments."""
    db = cache.get_default()
    if args.forced:
        db.lookup_email(args.address)
    info = db.get_email(args.address, nolookup=args.cached)
    print('{!r:} is {:s}valid: {:s}.'.format(info.address, '' if info.is_valid else 'in',
                                             info.reason))


def lookup_url(args):
    """Perform a Cache.get_url as specified by the given arguments."""
    db = cache.get_default()
    if args.forced:
        db.lookup_webpage(args.url)
    info = db.get_webpage(args.url, nolookup=args.cached)
    print('{!r:} reports {:s}.'.format(info.url, url_statuses[info.status][0]))


def mark_email(args):
    """Perform a Cache.set_email as specified by the given arguments."""
    cache.get_default().set_email(args.address, args.is_valid)
    print('{!r:} marked as {:s}valid.'.format(args.address, '' if args.is_valid else 'in'))


def mark_url(args):
    """Perform a Cache.set_url as specified by the given arguments."""
    cache.get_default().set_webpage(args.url, args.status)
    print('{!r:} marked with {:s}.'.format(args.url, url_statuses[args.status][0]))


def main(args=None):
    """Run the program with the given args or from the cmd args."""
    # Define base parser
    base = argparse.ArgumentParser(prog='iitech3')
    base.set_defaults(func=lambda x: base.print_help())
    base_childs = base.add_subparsers()

    # Define review parser
    review_cmd = base_childs.add_parser('review')
    review_cmd.set_defaults(func=review)
    review_target = review_cmd.add_mutually_exclusive_group(required=True)
    review_target.add_argument('file', action='store', type=str, nargs='?')
    review_target.add_argument('-p', '--pasteboard', action='store_const',
                               dest='file', const=None)

    # Define lookup parser
    lookup_cmd = base_childs.add_parser('lookup')
    lookup_cmd.set_defaults(func=lambda x: lookup_cmd.print_help())
    lookup_childs = lookup_cmd.add_subparsers()

    lookup_email_cmd = lookup_childs.add_parser('email')
    lookup_email_cmd.set_defaults(func=lookup_email)
    lookup_email_mode = lookup_email_cmd.add_mutually_exclusive_group()
    lookup_email_mode.add_argument('-c', '--cached', action='store_true')
    lookup_email_mode.add_argument('-f', '--forced', action='store_true')
    lookup_email_cmd.add_argument('address', action='store', type=str)

    lookup_url_cmd = lookup_childs.add_parser('webpage')
    lookup_url_cmd.set_defaults(func=lookup_url)
    lookup_url_mode = lookup_url_cmd.add_mutually_exclusive_group()
    lookup_url_mode.add_argument('-c', '--cached', action='store_true')
    lookup_url_mode.add_argument('-f', '--forced', action='store_true')
    lookup_url_cmd.add_argument('url', action='store', type=str)

    # Define mark parser
    mark_cmd = base_childs.add_parser('mark')
    mark_cmd.set_defaults(func=lambda x: mark_cmd.print_help())
    mark_childs = mark_cmd.add_subparsers()

    mark_email_cmd = mark_childs.add_parser('email')
    mark_email_cmd.set_defaults(func=mark_email)
    mark_email_result = mark_email_cmd.add_mutually_exclusive_group(required=True)
    mark_email_result.add_argument('--valid', action='store_true', dest='is_valid')
    mark_email_result.add_argument('--invalid', action='store_false', dest='is_valid')
    mark_email_cmd.add_argument('address', action='store', type=str)

    mark_url_cmd = mark_childs.add_parser('webpage')
    mark_url_cmd.set_defaults(func=mark_url)
    mark_url_status = mark_url_cmd.add_mutually_exclusive_group(required=True)
    mark_url_status.add_argument('-s', '--status', action='store', type=int)
    mark_url_status.add_argument('-k', '--ok', action='store_const', const=200,
                                 dest='status')
    mark_url_status.add_argument('-b', '--bad', action='store_const', const=400,
                                 dest='status')
    mark_url_status.add_argument('-d', '--down', action='store_const', const=500,
                                 dest='status')
    mark_url_status.add_argument('--teapot', action='store_const', const=418,
                                 dest='status')
    mark_url_cmd.add_argument('url', action='store', type=str)

    # Parse args
    definition = base.parse_args(args)
    definition.func(definition)


if __name__ == '__main__':
    main()
