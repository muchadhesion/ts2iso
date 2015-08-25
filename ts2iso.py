#!/usr/bin/python

import os.path
import os
import itertools
import re
import shutil
import subprocess as sp
import sys
import tempfile


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
    base = os.path.basename(outfile)

    with tempfile.NamedTemporaryFile(dir=dirname, prefix='.ts2iso-tmp-') as temp_outfile:
        hdi_args = [ "hdiutil", "makehybrid", "-iso", "-joliet", "-udf", "-udf-volume-name", base, "-o", temp_outfile.name, infile ]

        print hdi_args  
        if not dry_run:
            sp.call(hdi_args)
            shutil.move(temp_outfile.name, outfile)

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
    args = parser.parse_args()

    # ensure the output directory exists
    if args.output_dir is not None:
        try:
            ensure_directory(args.output_dir)
        except OSError, e:
            log.error("Couldn't create directory '%s'" % args.output_dir)

    for f in itertools.chain( args.files, lines_from_file( args.input_file ) ):
        transcode(f, None, True, True)


