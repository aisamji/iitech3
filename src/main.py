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
    base = argparse.ArgumentParser(prog='iitech3',
                                   description='An HTML newsletter manipulation utility '
                                               'for the Ismaili Insight newsletter.',
                                   formatter_class=argparse.RawTextHelpFormatter,
                                   usage='%(prog)s -h|--help\n       '
                                         '%(prog)s -v|--version\n       '
                                         '%(prog)s <command>')
    base._optionals.title = 'options'
    base.set_defaults(func=lambda x: base.print_help())
    base.add_argument('-v', '--version', action='version', version='%(prog)s {:s}'.format(__version__))
    base_childs = base.add_subparsers(title='commands',
                                      help='review\tReview and fix the HTML code of the newsletter in-place.\n'
                                           'lookup\tLookup the status of an email or a url.\n'
                                           'mark  \tManually mark the status of an email or a url.')

    # Define review parser
    review_cmd = base_childs.add_parser('review', prog='iitech3 review',
                                        description='Review and fix the HTML code of the newsletter in-place.',
                                        usage='%(prog)s <file>\n       '
                                              '%(prog)s -p|--pasteboard')
    review_cmd._optionals.title = 'options'
    review_cmd.set_defaults(func=review)
    review_target_grp = review_cmd.add_argument_group(title='targets')
    review_target_mex = review_target_grp.add_mutually_exclusive_group(required=True)
    review_target_mex.add_argument('file', action='store', type=str, nargs='?',
                                   help='The file that contains the HTML code to review.')
    review_target_mex.add_argument('-p', '--pasteboard', action='store_const',
                                   dest='file', const=None,
                                   help='Specifies that the HTML code to review is on the pasteboard.')

    # Define lookup parser
    lookup_cmd = base_childs.add_parser('lookup', prog='iitech3 lookup',
                                        description='Lookup the status of an email or a url.',
                                        formatter_class=argparse.RawTextHelpFormatter,
                                        usage='%(prog)s email [OPTIONS]\n       '
                                              '%(prog)s webpage [OPTIONS]')
    lookup_cmd._optionals.title = 'options'
    lookup_cmd.set_defaults(func=lambda x: lookup_cmd.print_help())
    lookup_childs = lookup_cmd.add_subparsers(title='types',
                                              help='email  \tLook up the status of an email.\n'
                                                    'webpage\tLook up the status of a webpage.')

    lookup_email_cmd = lookup_childs.add_parser('email', prog='iitech3 lookup email', add_help=False,
                                                description='Look up the status of an email.',
                                                usage='%(prog)s [-c|--cached] <address>\n       '
                                                      '%(prog)s -f|--forced <address>')
    lookup_email_cmd.set_defaults(func=lookup_email)
    lookup_email_mode_grp = lookup_email_cmd.add_argument_group(title='modifiers')
    lookup_email_mode_mex = lookup_email_mode_grp.add_mutually_exclusive_group()
    lookup_email_mode_mex.add_argument('-c', '--cached', action='store_true',
                                       help='Prevents an online lookup even if the status is not in the cache.')
    lookup_email_mode_mex.add_argument('-f', '--forced', action='store_true',
                                       help='Forces an online lookup before retrieving the status.')
    lookup_email_gen_grp = lookup_email_cmd.add_argument_group(title='arguments')
    lookup_email_gen_grp.add_argument('address', action='store', type=str,
                                      help='The email address to lookup.')
    lookup_email_gen_grp.add_argument('-h', '--help', action='help',
                                      help='Print this help message and exit.')

    lookup_url_cmd = lookup_childs.add_parser('webpage', prog='iitech3 lookup webpage', add_help=False,
                                              description='Look up the status of a webpage.',
                                              usage='%(prog)s [-c|--cached] <url>\n       '
                                                    '%(prog)s -f|--forced <url>')
    lookup_url_cmd.set_defaults(func=lookup_url)
    lookup_url_mode_grp = lookup_url_cmd.add_argument_group(title='modifiers')
    lookup_url_mode_mex = lookup_url_mode_grp.add_mutually_exclusive_group()
    lookup_url_mode_mex.add_argument('-c', '--cached', action='store_true',
                                     help='Prevents an online lookup even if the status is not in the cache.')
    lookup_url_mode_mex.add_argument('-f', '--forced', action='store_true',
                                     help='Forces an online lookup before retrieving the status.')
    lookup_url_gen_grp = lookup_url_cmd.add_argument_group(title='arguments')
    lookup_url_gen_grp.add_argument('url', action='store', type=str,
                                    help='The url to lookup.')
    lookup_url_gen_grp.add_argument('-h', '--help', action='help',
                                    help='Print this help message and exit.')

    # Define mark parser
    mark_cmd = base_childs.add_parser('mark', prog='iitech3 mark',
                                      formatter_class=argparse.RawTextHelpFormatter,
                                      description='Manually mark the status of an email or a url.',
                                      usage='%(prog)s email [OPTIONS]\n       '
                                            '%(prog)s webpage [OPTIONS]')
    mark_cmd._optionals.title = 'arguments'
    mark_cmd.set_defaults(func=lambda x: mark_cmd.print_help())
    mark_childs = mark_cmd.add_subparsers(title='types',
                                          help='email  \tManually mark the status of an email.\n'
                                               'webpage\tManually mark the status of a webpage.')

    mark_email_cmd = mark_childs.add_parser('email', prog='iitech3 mark email', add_help=False,
                                            description='Manually mark the status of an email.',
                                            usage='%(prog)s --valid <address>\n       '
                                                  '%(prog)s --invalid <address>')
    mark_email_cmd.set_defaults(func=mark_email)
    mark_email_result_grp = mark_email_cmd.add_argument_group(title='statuses')
    mark_email_result_mex = mark_email_result_grp.add_mutually_exclusive_group(required=True)
    mark_email_result_mex.add_argument('--valid', action='store_true', dest='is_valid',
                                       help='Mark the status of the address as valid.')
    mark_email_result_mex.add_argument('--invalid', action='store_false', dest='is_valid',
                                       help='Mark the status of the address as invalid.')
    mark_email_gen_grp = mark_email_cmd.add_argument_group(title='arguments')
    mark_email_gen_grp.add_argument('address', action='store', type=str,
                                    help='The address to mark.')
    mark_email_gen_grp.add_argument('-h', '--help', action='help',
                                    help='Print this help message and exit.')

    mark_url_cmd = mark_childs.add_parser('webpage', prog='iitech3 mark webpage', add_help=False,
                                          description='Manually mark the status of a webpage.',
                                          usage='%(prog)s -s|--status STATUS <url>\n       '
                                                '%(prog)s -k|--ok <url>\n       '
                                                '%(prog)s -b|--bad <url>\n       '
                                                '%(prog)s -d|--down <url>')
    mark_url_cmd.set_defaults(func=mark_url)
    mark_url_status_grp = mark_url_cmd.add_argument_group(title='statuses')
    mark_url_status_mex = mark_url_status_grp.add_mutually_exclusive_group(required=True)
    mark_url_status_mex.add_argument('-s', '--status', action='store', type=int,
                                     help='Mark the url with the given HTTP status code.')
    mark_url_status_mex.add_argument('-k', '--ok', action='store_const', const=200,
                                     dest='status', help='Mark the url as OK (status: 200).')
    mark_url_status_mex.add_argument('-b', '--bad', action='store_const', const=400,
                                     dest='status', help='Mark the url as a client error (status: 400).')
    mark_url_status_mex.add_argument('-d', '--down', action='store_const', const=500,
                                     dest='status', help='Mark the url as a server error (status: 500).')
    mark_url_status_mex.add_argument('--teapot', action='store_const', const=418,
                                     dest='status', help='Mark the url as a teapot (status: 418).')
    mark_url_gen_grp = mark_url_cmd.add_argument_group(title='arguments')
    mark_url_gen_grp.add_argument('url', action='store', type=str, help='The url to mark.')
    mark_url_gen_grp.add_argument('-h', '--help', action='help',
                                  help='Print this help message and exit.')

    # Parse args
    definition = base.parse_args(args)
    definition.func(definition)


if __name__ == '__main__':
    main()
