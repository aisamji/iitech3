#! /usr/local/bin/python3
"""The main script that serves as the program entry point."""

# Imports
import argparse
from datetime import datetime
from requests.status_codes import _codes as url_statuses
import yaml
import document
import pasteboard
import cache
import exceptions
import version

# String Constants
PROG_NAME = version.__title__
HELP_HELP = 'Print this help message and exit.'

REVIEW_ACT = 'review'
REVIEW_DESC = 'Review the HTML template for correctness before sending it out.'
REPAIR_ACT = 'repair'
REPAIR_DESC = "Repair the HTML template if it isn't loading correctly."
APPLY_ACT = 'apply'
APPLY_DESC = 'Apply a transform to the HTML template. This does not review or repair it.'

EMAIL_TYPE = 'email'
WEBPAGE_TYPE = 'webpage'

LOOKUP_ACT = 'lookup'
LOOKUP_DESC = 'Lookup the status of an email or a url.'
LOOKUP_EMAIL_DESC = 'Look up the status of an email.'
LOOKUP_WEBPAGE_DESC = 'Look up the status of a webpage.'

MARK_ACT = 'mark'
MARK_DESC = 'Manually mark the status of an email or a url.'
MARK_EMAIL_DESC = 'Manually mark the status of an email.'
MARK_WEBPAGE_DESC = 'Manually mark the status of a webpage.'

SNAPSHOT_ACT = 'snapshot'
SAVE_CMD = 'save'
LOAD_CMD = 'load'
LIST_CMD = 'list'

HELP_ACT = 'help'
HELP_DESC = 'Get help on the program or any of its subcommands.'
VERSION_ACT = 'version'
VERSION_DESC = 'Print the version of this program.'


def mkdate(date_string):
    """Convert the string into a datetime object."""
    return datetime.strptime(date_string, '%Y-%m-%d')


def get_code(path):
    """Read in the code from the specified file or the pasteboard."""
    if path is None:
        return pasteboard.get()
    else:
        with open(path, 'r', encoding='UTF-8') as html_file:
            code = html_file.read()
        return code


def set_code(path, doc):
    """Write the Document to the specified file or the pasteboard."""
    if path is None:
        pasteboard.set(doc)
    else:
        with open(path, 'w', encoding='UTF-8') as html_file:
            html_file.write(str(doc))


def review(args):
    """Perform a review operation specified by the given arguments."""
    html_doc = document.Document(get_code(args.file))
    summary = html_doc.review()

    print(
        '{:d} blank links removed.'.format(summary['links']['removed']),
        '{:d} misdirected links set to open in new window.'.format(summary['links']['retargetted']),
        '{:d} double-tracked links decoded.'.format(summary['links']['decoded']),
        '{:d} broken links marked.'.format(summary['links']['broken']),
        '{:d} unchecked links marked.'.format(summary['links']['unchecked']),

        '{:d} links referencing missing anchors marked.'.format(summary['anchors']['marked']),

        '{:d} emails cleaned.'.format(summary['emails']['cleaned']),
        '{:d} invalid emails marked.'.format(summary['emails']['invalid']),
        '{:d} unchecked emails marked.'.format(summary['emails']['unchecked']),
        sep='\n'
    )
    set_code(args.file, html_doc)


def repair(args):
    """Perform a repair operation specified by the given arguments."""
    html_doc = document.Document(get_code(args.file))
    summary = html_doc.repair()

    print(
        '{:d} typographical errors in ismailinsight.org corrected.'.format(summary['typos']),
        '{:d} style tags removed.'.format(summary['styles']),
        'Background fix {:s}applied.'.format('not ' if summary['background'] == 0 else ''),
        sep='\n'
    )
    set_code(args.file, html_doc)


def apply(args):
    """Apply a transform to an HTML template."""
    html_doc = document.Document(get_code(args.file))
    with open(args.transform_file, 'r', encoding='UTF-8') as tfr_file:
        tfr_json = yaml.load(tfr_file)
    not_applied = html_doc.apply(tfr_json)

    if len(not_applied) == 0:
        print('All transforms applied.')
    else:
        print('The following transforms could not be applied:')
        print(yaml.dump(not_applied))
    set_code(args.file, html_doc)


def lookup_email(args):
    """Perform a Cache.get_email as specified by the given arguments."""
    db = cache.get_default()
    if args.forced:
        db.lookup_email(args.address)
    try:
        info = db.get_email(args.address, nolookup=args.cached)
        print('{!r:} is {:s}valid: {:s}.'.format(info.address, '' if info.is_valid else 'in',
                                                 info.reason))
    except exceptions.CacheMissException:
        exit('{!r:} is not in the cache.'.format(args.address))


def lookup_url(args):
    """Perform a Cache.get_url as specified by the given arguments."""
    db = cache.get_default()
    if args.forced:
        db.lookup_webpage(args.url)
    try:
        info = db.get_webpage(args.url, nolookup=args.cached)
        print('{!r:} reports {:s}.'.format(info.url, url_statuses[info.status][0]))
    except exceptions.CacheMissException:
        exit('{!r:} is not in the cache.'.format(args.url))


def mark_email(args):
    """Perform a Cache.set_email as specified by the given arguments."""
    cache.get_default().set_email(args.address, args.is_valid)
    print('{!r:} marked as {:s}valid.'.format(args.address, '' if args.is_valid else 'in'))


def mark_url(args):
    """Perform a Cache.set_url as specified by the given arguments."""
    cache.get_default().set_webpage(args.url, args.status)
    print('{!r:} marked with {:s}.'.format(args.url, url_statuses[args.status][0]))


def save_snapshot(args):
    """Save a snapshot of the current document state."""
    html_doc = document.Document(get_code(args.file))
    info = html_doc.save(args.message, date=args.edition, region=args.region)
    if info is None:
        print('Duplicate snapshot. No snapshot saved.')
    else:
        print('Snapshot saved for {:s} {:%B %d, %Y}. '.format(info[2].capitalize(), info[3]) +
              '{0!r:} - {1:%B} {1.day:2}, {1:%Y %l:%M:%S.%f %p}'.format(info[0], info[1]))


def load_snapshot(args):
    """Revert the document code to the state described by the selected snapshot."""
    html_doc = document.Document(get_code(args.file))
    snapshot = html_doc.load(args.index, date=args.edition, region=args.region)
    set_code(args.file, html_doc)
    print('Loaded snapshot {0!r:} - {1:%B} {1.day:2}, {1:%Y %l:%M:%S.%f %p}'.format(snapshot[1], snapshot[0]))


def list_snapshots(args):
    """Print a list of all available snapshots along with their indexes."""
    html_doc = document.Document(get_code(args.file))
    edition, region, snapshots = html_doc.list(date=args.edition, region=args.region)
    print('Snapshots for {:s} {:%B %d, %Y}'.format(region.capitalize(), edition))
    for i in range(len(snapshots)):
        print('({:2d}) {!r:} -'.format(i, snapshots[i][1]) +
              ' {0:%B} {0.day:2}, {0:%Y %l:%M:%S.%f %p}'.format(snapshots[i][0]))

def main(args=None):
    """Run the program with the given args or from the cmd args."""
    # Define base parser
    base = argparse.ArgumentParser(prog=PROG_NAME,
                                   description=version.__description__,
                                   formatter_class=argparse.RawTextHelpFormatter,
                                   usage='%(prog)s <action>', add_help=False)
    base.set_defaults(func=lambda x: base.print_help())
    base_childs = base.add_subparsers(title='actions',
                                      help='{:6s}\t{:s}\n'.format(REVIEW_ACT, REVIEW_DESC) +
                                           '{:6s}\t{:s}\n'.format(REPAIR_ACT, REPAIR_DESC) +
                                           '{:6s}\t{:s}\n'.format(LOOKUP_ACT, LOOKUP_DESC) +
                                           '{:6s}\t{:s}\n'.format(MARK_ACT, MARK_DESC) +
                                           '{:6s}\t{:s}\n'.format(APPLY_ACT, APPLY_DESC) +
                                           '{:6s}\t{:s}\n'.format(SNAPSHOT_ACT, 'Manage Snapshots') +
                                           '{:6s}\t{:s}\n'.format(HELP_ACT, HELP_DESC) +
                                           '{:6s}\t{:s}'.format(VERSION_ACT, VERSION_DESC))

    # Define review parser
    review_cmd = base_childs.add_parser(REVIEW_ACT, prog='{:s} {:s}'.format(PROG_NAME, REVIEW_ACT),
                                        description=REVIEW_DESC, add_help=False,
                                        usage='%(prog)s <file>\n       '
                                              '%(prog)s -p|--pasteboard')
    review_cmd.set_defaults(func=review)
    review_target_grp = review_cmd.add_argument_group(title='targets')
    review_target_mex = review_target_grp.add_mutually_exclusive_group(required=True)
    review_target_mex.add_argument('file', action='store', type=str, nargs='?',
                                   help='The file that contains the HTML code to review.')
    review_target_mex.add_argument('-p', '--pasteboard', action='store_const',
                                   dest='file', const=None,
                                   help='Specifies that the HTML code to review is on the pasteboard.')

    # Define repair parser
    repair_cmd = base_childs.add_parser(REPAIR_ACT, prog=' '.join([PROG_NAME, REPAIR_ACT]),
                                        description=REPAIR_DESC, add_help=False,
                                        usage='%(prog)s <file>\n       '
                                              '%(prog)s -p|--pasteboard')
    repair_cmd.set_defaults(func=repair)
    repair_target_grp = repair_cmd.add_argument_group(title='targets')
    repair_target_mex = repair_target_grp.add_mutually_exclusive_group(required=True)
    repair_target_mex.add_argument('file', action='store', type=str, nargs='?',
                                   help='The file that contains the HTML code to repair.')
    repair_target_mex.add_argument('-p', '--pasteboard', action='store_const',
                                   dest='file', const=None,
                                   help='Specifies that the HTML code to repair is on the pasteboard.')

    # Define lookup parser
    lookup_cmd = base_childs.add_parser(LOOKUP_ACT, prog='{:s} {:s}'.format(PROG_NAME, LOOKUP_ACT),
                                        description=LOOKUP_DESC, add_help=False,
                                        formatter_class=argparse.RawTextHelpFormatter,
                                        usage='%(prog)s {:s} [OPTIONS]\n       '.format(EMAIL_TYPE) +
                                              '%(prog)s {:s} [OPTIONS]'.format(WEBPAGE_TYPE))
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

    # Define mark parser
    mark_cmd = base_childs.add_parser(MARK_ACT, prog='{:s} {:s}'.format(PROG_NAME, MARK_ACT),
                                      formatter_class=argparse.RawTextHelpFormatter,
                                      description=MARK_DESC, add_help=False,
                                      usage='%(prog)s {:s} [OPTIONS]\n       '.format(EMAIL_TYPE) +
                                            '%(prog)s {:s} [OPTIONS]'.format(WEBPAGE_TYPE))
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

    # Define apply parser
    apply_cmd = base_childs.add_parser(APPLY_ACT, prog='{:s} {:s}'.format(PROG_NAME, APPLY_ACT),
                                       description=APPLY_DESC,
                                       usage='%(prog)s <transform_file> <target>', add_help=False)
    apply_cmd._optionals.title = 'options'
    apply_cmd.set_defaults(func=apply)
    apply_cmd.add_argument('transform_file', action='store', type=str,
                           help='The yaml file that describes the transform to apply.')
    apply_target_grp = apply_cmd.add_argument_group(title='targets')
    apply_target_mex = apply_target_grp.add_mutually_exclusive_group(required=True)
    apply_target_mex.add_argument('file', action='store', type=str, nargs='?',
                                  help='The file that contains the HTML code to transform.')
    apply_target_mex.add_argument('-p', '--pasteboard', action='store_const',
                                  dest='file', const=None,
                                  help='Specifies that the HTML code to transform is on the pasteboard.')

    # Define snapshot parser
    snapshot_cmd = base_childs.add_parser(SNAPSHOT_ACT, prog=' '.join((PROG_NAME, SNAPSHOT_ACT)),
                                          usage='%(prog)s {:s} [OPTIONS]\n       '.format(SAVE_CMD) +
                                                '%(prog)s {:s} [OPTIONS]'.format(LOAD_CMD), add_help=False)
    snapshot_cmd.set_defaults(func=lambda x: snapshot_cmd.print_help())
    snapshot_childs = snapshot_cmd.add_subparsers(title='subcommands')

    snapshot_save_cmd = snapshot_childs.add_parser(SAVE_CMD, prog=' '.join((PROG_NAME, SNAPSHOT_ACT,
                                                                            SAVE_CMD)))
    snapshot_save_cmd.set_defaults(func=save_snapshot)
    snapshot_save_cmd.add_argument('message')
    snapshot_save_cmd.add_argument('-e', '--edition', type=mkdate, metavar='DATE')
    snapshot_save_region_mex = snapshot_save_cmd.add_mutually_exclusive_group()
    snapshot_save_region_mex.add_argument('-ne', '--northeastern', dest='region', action='store_const',
                                          const='northeastern')
    snapshot_save_region_mex.add_argument('-se', '--southeastern', dest='region', action='store_const',
                                          const='southeastern')
    snapshot_save_region_mex.add_argument('-fl', '--florida', dest='region', action='store_const',
                                          const='florida')
    snapshot_save_region_mex.add_argument('-mw', '--midwestern', dest='region', action='store_const',
                                          const='midwestern')
    snapshot_save_region_mex.add_argument('-c', '--central', dest='region', action='store_const',
                                          const='central')
    snapshot_save_region_mex.add_argument('-sw', '--southwestern', dest='region', action='store_const',
                                          const='southwestern')
    snapshot_save_region_mex.add_argument('-w', '--western', dest='region', action='store_const',
                                          const='western')
    snapshot_save_target_grp = snapshot_save_cmd.add_argument_group(title='targets')
    snapshot_save_target_mex = snapshot_save_target_grp.add_mutually_exclusive_group(required=True)
    snapshot_save_target_mex.add_argument('file', nargs='?')
    snapshot_save_target_mex.add_argument('-p', '--pasteboard', action='store_const',
                                          dest='file', const=None,)

    snapshot_load_cmd = snapshot_childs.add_parser(LOAD_CMD, prog=' '.join((PROG_NAME, SNAPSHOT_ACT,
                                                                             LOAD_CMD)))
    snapshot_load_cmd.set_defaults(func=load_snapshot)
    snapshot_load_cmd.add_argument('index', type=int)
    snapshot_load_cmd.add_argument('-e', '--edition', type=mkdate, metavar='DATE')
    snapshot_load_region_mex = snapshot_load_cmd.add_mutually_exclusive_group()
    snapshot_load_region_mex.add_argument('-ne', '--northeastern', dest='region', action='store_const',
                                          const='northeastern')
    snapshot_load_region_mex.add_argument('-se', '--southeastern', dest='region', action='store_const',
                                          const='southeastern')
    snapshot_load_region_mex.add_argument('-fl', '--florida', dest='region', action='store_const',
                                          const='florida')
    snapshot_load_region_mex.add_argument('-mw', '--midwestern', dest='region', action='store_const',
                                          const='midwestern')
    snapshot_load_region_mex.add_argument('-c', '--central', dest='region', action='store_const',
                                          const='central')
    snapshot_load_region_mex.add_argument('-sw', '--southwestern', dest='region', action='store_const',
                                          const='southwestern')
    snapshot_load_region_mex.add_argument('-w', '--western', dest='region', action='store_const',
                                          const='western')
    snapshot_load_target_grp = snapshot_load_cmd.add_argument_group(title='targets')
    snapshot_load_target_mex = snapshot_load_target_grp.add_mutually_exclusive_group(required=True)
    snapshot_load_target_mex.add_argument('file', nargs='?')
    snapshot_load_target_mex.add_argument('-p', '--pasteboard', action='store_const',
                                          dest='file', const=None,)

    snapshot_list_cmd = snapshot_childs.add_parser(LIST_CMD, prog=' '.join((PROG_NAME, SNAPSHOT_ACT,
                                                                            LIST_CMD)))
    snapshot_list_cmd.set_defaults(func=list_snapshots)
    snapshot_list_cmd.add_argument('-e', '--edition', type=mkdate, metavar='DATE')
    snapshot_list_region_mex = snapshot_list_cmd.add_mutually_exclusive_group()
    snapshot_list_region_mex.add_argument('-ne', '--northeastern', dest='region', action='store_const',
                                          const='northeastern')
    snapshot_list_region_mex.add_argument('-se', '--southeastern', dest='region', action='store_const',
                                          const='southeastern')
    snapshot_list_region_mex.add_argument('-fl', '--florida', dest='region', action='store_const',
                                          const='florida')
    snapshot_list_region_mex.add_argument('-mw', '--midwestern', dest='region', action='store_const',
                                          const='midwestern')
    snapshot_list_region_mex.add_argument('-c', '--central', dest='region', action='store_const',
                                          const='central')
    snapshot_list_region_mex.add_argument('-sw', '--southwestern', dest='region', action='store_const',
                                          const='southwestern')
    snapshot_list_region_mex.add_argument('-w', '--western', dest='region', action='store_const',
                                          const='western')
    snapshot_list_target_grp = snapshot_list_cmd.add_argument_group(title='targets')
    snapshot_list_target_mex = snapshot_list_target_grp.add_mutually_exclusive_group(required=True)
    snapshot_list_target_mex.add_argument('file', nargs='?')
    snapshot_list_target_mex.add_argument('-p', '--pasteboard', action='store_const',
                                          dest='file', const=None,)

    # Define version command
    version_cmd = base_childs.add_parser(VERSION_ACT, prog=' '.join((PROG_NAME, VERSION_ACT)),
                                         description=VERSION_DESC,
                                         usage='%(prog)s', add_help=False)
    version_cmd.set_defaults(func=lambda x: print(' '.join((PROG_NAME, version.__version__))))

    # Define help command
    help_cmd = base_childs.add_parser(HELP_ACT, prog=' '.join((PROG_NAME, HELP_ACT)),
                                      description=HELP_DESC, usage='%(prog)s <action>',  add_help=False)
    help_childs = help_cmd.add_subparsers(title='actions')
    help_review = help_childs.add_parser(REVIEW_ACT, prog=' '.join((PROG_NAME, HELP_ACT, REVIEW_ACT)),
                                         usage='%(prog)s', add_help=False)
    help_review.set_defaults(func=lambda x: review_cmd.print_help())
    help_repair = help_childs.add_parser(REPAIR_ACT, prog=' '.join((PROG_NAME, HELP_ACT, REPAIR_ACT)),
                                         usage='%(prog)s', add_help=False)
    help_repair.set_defaults(func=lambda x: repair_cmd.print_help())
    help_lookup = help_childs.add_parser(LOOKUP_ACT, prog=' '.join((PROG_NAME, HELP_ACT, LOOKUP_ACT)),
                                         usage='%(prog)s', add_help=False)
    help_lookup.set_defaults(func=lambda x: lookup_cmd.print_help())
    help_mark = help_childs.add_parser(MARK_ACT, prog=' '.join((PROG_NAME, HELP_ACT, MARK_ACT)),
                                       usage='%(prog)s', add_help=False)
    help_mark.set_defaults(func=lambda x: mark_cmd.print_help())
    help_apply = help_childs.add_parser(APPLY_ACT, prog=' '.join((PROG_NAME, HELP_ACT, APPLY_ACT)),
                                        usage='%(prog)s', add_help=False)
    help_apply.set_defaults(func=lambda x: apply_cmd.print_help())

    # Parse args
    definition = base.parse_args(args)
    definition.func(definition)


if __name__ == '__main__':
    main()
