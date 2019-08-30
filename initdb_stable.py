#!/usr/bin/env python3
# -*- coding: utf-8 -*-"

import sqlite3
import os
import re
import subprocess
from config import stable_path, stable_branches
from common import workdir, stabledb, stable_branch, createdb

# "commit" is sometimes seen multiple times, such as with commit 6093aabdd0ee
cherrypick=re.compile("cherry picked from (commit )+([0-9a-f]+)")
stable=re.compile("^\s*(commit )+([0-9a-f]+) upstream")
stable2=re.compile("^\s*\[\s*Upstream (commit )+([0-9a-f]+)\s*\]")

def mktable(c):
  '''
  Create database table
  '''

  c.execute("CREATE TABLE commits (sha text, usha text, \
                                   patchid text, \
                                   description text)")
  c.execute("CREATE UNIQUE INDEX commit_sha ON commits (sha)")
  c.execute("CREATE INDEX upstream_sha ON commits (usha)")
  c.execute("CREATE INDEX patch_id ON commits (patchid)")

def update_commits(start, db):
  '''
  Get complete list of commits from stable branch.
  Assume that stable branch exists and has been checked out.
  '''

  conn = sqlite3.connect(db)
  c = conn.cursor()

  commits = subprocess.check_output(['git', 'log', '--no-merges', '--abbrev=12',
                                     '--oneline', '--reverse', '%s..' % start])

  last = None
  for commit in commits.splitlines():
    if commit != "":
      elem = commit.decode('latin-1').split(" ", 1)
      sha = elem[0]
      description = elem[1].rstrip('\n')
      description = description.decode('latin-1') \
                  if not isinstance(description, str) else description

      ps = subprocess.Popen(['git', 'show', sha], stdout=subprocess.PIPE)
      spid = subprocess.check_output(['git', 'patch-id', '--stable'],
                                     stdin=ps.stdout)
      patchid = spid.decode('latin-1').split(" ", 1)[0]

      # Do nothing if the sha is already in the database
      c.execute("select sha from commits where sha='%s'" % sha)
      found = c.fetchone()
      if found:
        continue

      last = sha

      # Search for upstream SHA. If found, record upstream SHA associated
      # with this commit.
      usha=""
      desc = subprocess.check_output(['git', 'show', '-s', sha])
      for d in desc.splitlines():
        d = d.decode('latin-1') if not isinstance(d, str) else d
        m = cherrypick.search(d)
        if not m:
          m = stable.search(d)
          if not m:
            m = stable2.search(d)
        if m:
          usha=m.group(2)[:12]
          # The patch may have been picked multiple times; only record
          # the first entry.
          break

      c.execute("INSERT INTO commits(sha, usha, patchid, description) VALUES (?, ?, ?, ?)",
                (sha, usha, patchid, description))
  if last:
    c.execute("UPDATE tip set sha='%s' where ref=1" % last)

  conn.commit()
  conn.close()

def update_stabledb():

  os.chdir(stable_path)

  for branch in stable_branches:
    start = 'v%s' % branch
    db = stabledb(branch)
    bname = stable_branch(branch)

    print("Handling %s" % bname)

    try:
      conn = sqlite3.connect(db)
      c = conn.cursor()
      c.execute("select sha from tip")
      sha = c.fetchone()
      conn.close()
      if sha and sha[0] != "":
        start = sha[0]
      else:
        fail
    except:
      createdb(db, mktable)

    subprocess.check_output(['git', 'checkout', bname])
    subprocess.check_output(['git', 'pull'])

    update_commits(start, db)

  os.chdir(workdir)

if __name__ == "__main__":
  update_stabledb()
