#! /usr/bin/env python3
"""The main script that serves as the program entry point."""
# Metadata
__title__ = 'iitech3'
__author__ = 'Ali I Samji'
__version__ = '0.1.0'

# Imports
import argparse
from requests.status_codes import _codes as url_statuses
import document
import pasteboard
import cache

# String Constants
REVIEW_DESC = 'Review and fix the HTML code of the newsletter in-place.'
LOOKUP_DESC = 'Lookup the status of an email or a url.'
LOOKUP_EMAIL_DESC = 'Look up the status of an email.'
LOOKUP_WEBPAGE_DESC = 'Look up the status of a webpage.'
MARK_DESC = 'Manually mark the status of an email or a url.'
MARK_EMAIL_DESC = 'Manually mark the status of an email.'
MARK_WEBPAGE_DESC = 'Manually mark the status of a webpage.'
HELP_HELP = 'Print this help message and exit.'
PROG_NAME = __title__
REVIEW_ACT = 'review'
LOOKUP_ACT = 'lookup'
MARK_ACT = 'mark'
EMAIL_TYPE = 'email'
WEBPAGE_TYPE = 'webpage'


def review(args):
    """Perform a review operation specified by the given arguments."""
    if args.file is None:
        code = pasteboard.get()
    else:
        with open(args.file, 'r') as file:
            code = file.read()
    html_doc = document.Document(code)
    summary = html_doc.review()

    print(
        '{:d} blank links removed.'.format(summary['links']['removed']),
        '{:d} misdirected links set to open in new window.'.format(summary['links']['retargetted']),
        '{:d} double-tracked links decoded.'.format(summary['links']['decoded']),
        '{:d} broken/unchecked links marked.'.format(summary['links']['marked']),

        '{:d} links referencing missing anchors marked.'.format(summary['anchors']['marked']),

        '{:d} emails cleaned.'.format(summary['emails']['cleaned']),
        '{:d} invalid/unchecked emails marked.'.format(summary['emails']['marked']),
        sep='\n'
    )

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
    base = argparse.ArgumentParser(prog=PROG_NAME,
                                   description='An HTML newsletter manipulation utility '
                                               'for the Ismaili Insight newsletter.',
                                   formatter_class=argparse.RawTextHelpFormatter,
                                   usage='%(prog)s -h|--help\n       '
                                         '%(prog)s -v|--version\n       '
                                         '%(prog)s <action>')
    base._optionals.title = 'options'
    base.set_defaults(func=lambda x: base.print_help())
    base.add_argument('-v', '--version', action='version', version='%(prog)s {:s}'.format(__version__))
    base_childs = base.add_subparsers(title='actions',
                                      help='{:6s}\t{:s}\n'.format(REVIEW_ACT, REVIEW_DESC) +
                                           '{:6s}\t{:s}\n'.format(LOOKUP_ACT, LOOKUP_DESC) +
                                           '{:6s}\t{:s}'.format(MARK_ACT, MARK_DESC))

    # Define review parser
    review_cmd = base_childs.add_parser(REVIEW_ACT, prog='{:s} {:s}'.format(PROG_NAME, REVIEW_ACT),
                                        description=REVIEW_DESC,
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
    lookup_cmd = base_childs.add_parser(LOOKUP_ACT, prog='{:s} {:s}'.format(PROG_NAME, LOOKUP_ACT),
                                        description=LOOKUP_DESC,
                                        formatter_class=argparse.RawTextHelpFormatter,
                                        usage='%(prog)s {:s} [OPTIONS]\n       '.format(EMAIL_TYPE) +
                                              '%(prog)s {:s} [OPTIONS]'.format(WEBPAGE_TYPE))
    lookup_cmd._optionals.title = 'options'
    lookup_cmd.set_defaults(func=lambda x: lookup_cmd.print_help())
    lookup_childs = lookup_cmd.add_subparsers(title='types',
                                              help='{:7s}\t{:s}\n'.format(EMAIL_TYPE, LOOKUP_EMAIL_DESC) +
                                                    '{:7s}\t{:s}'.format(WEBPAGE_TYPE, LOOKUP_WEBPAGE_DESC))

    lookup_email_cmd = lookup_childs.add_parser(EMAIL_TYPE, prog='{:s} {:s} {:s}'.format(
                                                    PROG_NAME, LOOKUP_ACT, EMAIL_TYPE),
                                                add_help=False,
                                                description=LOOKUP_EMAIL_DESC,
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
                                      help=HELP_HELP)

    lookup_url_cmd = lookup_childs.add_parser(WEBPAGE_TYPE, prog='{:s} {:s} {:s}'.format(
                                                  PROG_NAME, LOOKUP_ACT, WEBPAGE_TYPE),
                                              add_help=False,
                                              description=LOOKUP_WEBPAGE_DESC,
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
                                    help=HELP_HELP)

    # Define mark parser
    mark_cmd = base_childs.add_parser(MARK_ACT, prog='{:s} {:s}'.format(PROG_NAME, MARK_ACT),
                                      formatter_class=argparse.RawTextHelpFormatter,
                                      description=MARK_DESC,
                                      usage='%(prog)s {:s} [OPTIONS]\n       '.format(EMAIL_TYPE) +
                                            '%(prog)s {:s} [OPTIONS]'.format(WEBPAGE_TYPE))
    mark_cmd._optionals.title = 'arguments'
    mark_cmd.set_defaults(func=lambda x: mark_cmd.print_help())
    mark_childs = mark_cmd.add_subparsers(title='types',
                                          help='{:7s}\t{:s}\n'.format(EMAIL_TYPE, MARK_EMAIL_DESC) +
                                               '{:7s}\t{:s}'.format(WEBPAGE_TYPE, MARK_WEBPAGE_DESC))

    mark_email_cmd = mark_childs.add_parser(EMAIL_TYPE, prog='{:s} {:s} {:s}'.format(
                                                PROG_NAME, MARK_ACT, EMAIL_TYPE),
                                            add_help=False,
                                            description=MARK_EMAIL_DESC,
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
                                    help=HELP_HELP)

    mark_url_cmd = mark_childs.add_parser(WEBPAGE_TYPE, prog='{:s}'.format(
                                              PROG_NAME, MARK_ACT, WEBPAGE_TYPE),
                                          add_help=False,
                                          description=MARK_WEBPAGE_DESC,
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
                                  help=HELP_HELP)

    # Parse args
    definition = base.parse_args(args)
    definition.func(definition)


if __name__ == '__main__':
    main()
