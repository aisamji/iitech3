#! /usr/bin/env python3
"""The main script that serves as the program entry point."""

__author__ = 'Ali I Samji'
__version__ = '0.1.0'

import argparse
import document
import pasteboard


def review(args):
    """Perform a review operation specified by the given arguments."""
    if args.file is None:
        code = pasteboard.get()
    else:
        code = args.file.read()
    html_doc = document.Document(code)
    html_doc.review()


def main(args=None):
    """Run the program with the given args or from the cmd args."""
    # Define base parser
    base = argparse.ArgumentParser(prog='iitech3')
    base.set_defaults(func=lambda x: base.print_help())
    base_childs = base.add_subparsers()

    # Define review parser
    review = base_childs.add_parser('review')
    review.set_defaults(func=review)
    review_target = review.add_mutually_exclusive_group(required=True)
    review_target.add_argument('file', action='store', type=argparse.FileType('r'), nargs='?')
    review_target.add_argument('-p', '--pasteboard', action='store_const',
                               dest='file', const=None)

    # Parse args
    definition = base.parse_args(args)
    definition.func(definition)


if __name__ == '__main__':
    main()
