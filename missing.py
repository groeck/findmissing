#!/usr/bin/env python3
# -*- coding: utf-8 -*-"

from collections import defaultdict
import operator
import os
import re
import subprocess
import sys
import sqlite3

from config import stable_path, stable_branches
from common import workdir, stabledb, upstreamdb, stable_branch

nowhere = open('/dev/null', 'w')

def get_status(sha):
  '''
  Check if patch needs to be applied to current branch.
  The working directory and branch must be set when calling
  this function.

  Return 0 if the patch has already been applied,
  1 if the patch is missing and applies cleanly,
  2 if the patch is missing and fails to apply.
  '''

  ret = 0

  os.system("git reset --hard HEAD > /dev/null 2>&1")

  try:
    # Returns 0 on success, else a non-zero status code
    result = subprocess.call(['git', 'cherry-pick', '-n', sha], stderr=nowhere)

    if result:
      ret = 2
    else:
      diff = subprocess.check_output(['git', 'diff', 'HEAD'])
      if diff:
        ret = 1
  except:
    ret = 2

  os.system("git reset --hard HEAD > /dev/null 2>&1")

  return ret

def getcontext(bname, sdb, udb, usha, recursive):
  cs = sdb.cursor()
  cu = udb.cursor()

  cu.execute("select sha, description from commits where sha is '%s'" % usha)
  found = False
  for (sha, description) in cu.fetchall():
    # usha -> sha maping should be 1:1
    # If it isn't, skip duplicate entries.
    if found:
      print("hmm")
      continue
    found = True
    cu.execute("select fsha, patchid, ignore from fixes where sha='%s'" % usha)
    # usha, however, may have multiple fixes
    printed = recursive
    for (fsha, patchid, ignore) in cu.fetchall():
      if ignore:
        continue
      # Check if the fix (fsha) is in our code base
      cs.execute("select sha, usha from commits where usha is '%s'" % fsha)
      fix=cs.fetchone()
      if not fix:
        # The fix is not in our code base. Try to find it using its patch ID.
        # print(" SHA %s not found, trying patch ID based lookup" % fsha)
        cs.execute("select sha, usha from commits where patchid is '%s'" % patchid)
        fix=cs.fetchone()
        if not fix:
          status = get_status(fsha)
          if status != 0:
            if not printed:
              print("SHA %s [%s] ('%s')" % (sha, usha, description))
              printed = True
            str = "    " if recursive else "  "
            print("%sFixed by commit %s" % (str, fsha))
            if status == 1:
              print("  %sFix is missing from %s and applies cleanly" % (str, bname))
            else:
              print("  %sFix may be missing from %s; trying to apply it results in conflicts/errors" %
                    (str, bname))
            getcontext(bname, sdb, udb, fsha, True)

def missing(version):
  """
  Look for missing Fixup commits in provided stable release
  """

  bname = stable_branch(version)

  print("Checking branch %s" % bname)

  subprocess.check_output(['git', 'checkout', bname], stderr=nowhere)

  sdb = sqlite3.connect(stabledb(version))
  cs = sdb.cursor()
  udb = sqlite3.connect(upstreamdb)
  cu = udb.cursor()

  cs.execute("select usha from commits where usha != ''")
  for (usha) in cs.fetchall():
    getcontext(bname, sdb, udb, usha[0], False)

  udb.close()
  sdb.close()

def findmissing():
  if len(sys.argv) > 1:
    branches = sys.argv[1:]
  else:
    branches = stable_branches

  os.chdir(stable_path)
  for b in branches:
    missing(b)

findmissing()
