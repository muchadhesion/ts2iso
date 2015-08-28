#!/usr/bin/python

import os.path
import os
import itertools
import re
import shutil
import subprocess as sp
import sys
import tempfile
import datetime


def change_file_ext(fname, ext):
    '''Transforms the given filename's extension to the given extension.'''
    return os.path.splitext(fname)[0] + ext

def transcode(infile, outfile=None, skip_existing=True, dry_run = True):
    outfile = outfile or change_file_ext(infile, '.iso')

    # skip transcoding existing files if specified
    if skip_existing and os.path.exists(outfile):
        print outfile, "already exists.  Skipping..."
        return

    # NOTE: we use a temp file to store the incremental in-flight transcode, and
    # move it to the final output filename when transcode is complete. this
    # approach prevents partial or interrupted transcodes from getting in the
    # way of --skip-existing.

    # create the file in the same dir (and same filesystem) as the final target,
    # this keeps our final shutil.move efficient
    dirname = os.path.dirname(outfile)
    basename = os.path.basename(outfile)
    undecorated_name = os.path.splitext(basename)[0]

    temp_outfile = '%s/.ts2iso-%s-%s.iso' % (dirname, undecorated_name, str(os.getpid()))
    hdi_args = [ "hdiutil", "makehybrid", "-iso", "-joliet", "-udf", "-udf-volume-name", basename, "-o", temp_outfile, infile ]

    print hdi_args
    if dry_run:
        return None
    else:
        sp.call(hdi_args)
        shutil.move(temp_outfile, outfile)

    return 0 # return value

def lines_from_file(file):
    '''
    A generator to read lines from a file that does not buffer the input lines

    Standard python file iterator line-buffering prevents interactive uses of stdin as
    an input file.  Only readline() has the line-buffered behaviour we want.
    '''
    while file and True:
        line = file.readline()
        if line == '':
            break
        yield line.strip()


def walk_dir(d, follow_links=False):
    '''
    Yields all the file names in a given directory, including those in
    subdirectories.  If 'follow_links' is True, symbolic links will be followed.
    This option can lead to infinite looping since the function doesn't keep
    track of which directories have been visited.
    '''

    # walk the directory and collect the full path of every file therein
    for root, dirs, files in os.walk(d, followlinks=follow_links):
        for name in files:
            # append the normalized file name
            yield os.path.abspath(os.path.join(root, name))

def walk_paths(path_list, follow_links=False):
    '''
    Yields all the file names in a given list of files and directories
    If 'follow_links' is True, symbolic links will be followed.

    Files are guaranteed to be listed only once
    '''

    # keep track of files added to de-duplicate files supplied on command line and avoid
    # symlink cycles
    files = set()

    for p in path_list:
        if os.path.isdir(p):
            for f in walk_dir(p):
                if f not in files:
                    files.add(f)
                    yield f
        else:
            if p not in files:
                files.add(p)
                yield p


def init_logger(args):
    # set log level and format
    log = logging.getLogger('ts2iso')
    log.setLevel(logging.INFO)

    # prevent 'no loggers found' warning
    log.addHandler(logging.NullHandler())

    # custom log formatting
    formatter = logging.Formatter('[%(levelname)s] %(message)s')

    # log to stderr unless disabled
    if not args.quiet:
        sh = logging.StreamHandler()
        sh.setFormatter(formatter)
        log.addHandler(sh)

    # add a file handler if specified
    if args.logfile is not None:
        fh = logging.FileHandler(args.logfile)
        fh.setFormatter(formatter)
        log.addHandler(fh)

    return log


if __name__ == '__main__':
    import logging
    import time
    import argparse

    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('files', metavar='FILES', type=str, nargs='*',
            help='Files and/or directories to transcode')

    # options and flags
    parser.add_argument('-o', '--output-dir', type=os.path.abspath,
            help='Directory to output transcoded files to')
    parser.add_argument('-f', '--file', nargs='?', type=argparse.FileType('r'), 
            default=None, dest='input_file',
            help='Supply a list of files to transcode in FILE')
    parser.add_argument('-s', '--skip-existing', action='store_true',
            help='Skip transcoding files if the output file already exists')
    parser.add_argument('-n', '--dry-run', action='store_true',
            help="Look at the files, but don't do anything")
    parser.add_argument('-l', '--logfile', type=os.path.normpath, default=None,
            help='log output to a file as well as to the console.')
    parser.add_argument('-q', '--quiet', action='store_true',
            help='Disable console output.')

    args = parser.parse_args()
    log = init_logger(args)

    # ensure the output directory exists
    if args.output_dir is not None:
        try:
            ensure_directory(args.output_dir)
        except OSError, e:
            log.error("Couldn't create directory '%s'" % args.output_dir)

    for f in itertools.chain( args.files, lines_from_file( args.input_file ) ):
        log.info("Transcoding '%s'..." % f)
        # time the transcode
        start_time = time.time()
        retcode = transcode(f, outfile=None, skip_existing=args.skip_existing, dry_run=args.dry_run)
        total_time = time.time() - start_time

        # log success or error
        if retcode == 0:
            log.info("Transcoded '%s' in %s" % 
                ( f, '{:0>8}'.format(datetime.timedelta(seconds=total_time) ) ) )
        elif retcode == None:
            log.info("Skipped '%s'", f)
        else:
            log.error("Failed to transcode '%s' after %s" %
                ( f, '{:0>8}'.format(datetime.timedelta(seconds=total_time) ) ) )
