#!/usr/bin/python

import os.path
from subprocess import call
import os

def process(line):
	print line
	base =os.path.basename(line) 
	print base
	target = base + ".iso"

	if os.path.isfile(target):
		print target, "already exists.  Skipping..."
		return
	#
	# generate into ".target"
	from subprocess import call
	conv=[ "hdiutil", "makehybrid", "-iso", "-joliet", "-udf", "-udf-volume-name", base, "-o", "." + target, line]
	print conv
	call(conv)
	os.rename("." + target, target)
	print
	# 

import fileinput
for line in fileinput.input():
	line=line.strip()
	process(line)

