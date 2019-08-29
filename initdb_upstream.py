#!/usr/bin/env python3

import os
import re
import sqlite3
import subprocess
from config import upstream_path, stable_branches
from common import workdir, upstreamdb, createdb

upstream_base = 'v' + stable_branches[0]

rf = re.compile('^\s*Fixes: (?:commit )*([0-9a-f]+).*')
rdesc = re.compile('.* \("([^"]+)"\).*')

def mktables(c):
  # Upstream commits
  c.execute("CREATE TABLE commits (sha text, description text)")
  c.execute("CREATE UNIQUE INDEX commit_sha ON commits (sha)")

  # Fixes associated with upstream commits. sha is the commit, fsha is its fix.
  # Each sha may have multiple fixes associated with it.
  c.execute("CREATE TABLE fixes (sha text, fsha text, patchid text, ignore integer)")
  c.execute("CREATE INDEX sha ON fixes (sha)")

def handle(start):
  conn = sqlite3.connect(upstreamdb)
  c = conn.cursor()
  c2 = conn.cursor()

  commits = subprocess.check_output(['git', 'log', '--abbrev=12', '--oneline',
                                       '--no-merges', '--reverse', start+'..'])
  for commit in commits.splitlines():
    if commit != "":
        elem = commit.decode().split(' ', 1)
        sha = elem[0]
        last = sha

        # skip if SHA is already in database. This will happen
        # for the first SHA when the script is re-run.
        c.execute("select sha from commits where sha is '%s'" % sha)
        if c.fetchone():
          continue

        description = elem[1].rstrip('\n')
        description = description.decode('latin-1') if not isinstance(description, str) else description
        c.execute("INSERT INTO commits(sha, description) VALUES (?, ?)",
                  (sha, description))
        # check if this patch fixes a previous patch.
        description = subprocess.check_output(['git', 'show', '-s', '--pretty=format:%b', sha])
        for d in description.splitlines():
          d = d.decode('latin-1') if not isinstance(d, str) else d
          m = rf.search(d)
          fsha=None
          if m and m.group(1):
            try:
              # Normalize fsha to 12 characters.
              cmd = 'git show -s --pretty=format:%%H %s 2>/dev/null' % m.group(1)
              fsha = subprocess.check_output(cmd, shell=True).decode()
            except:
              print("Commit '%s' for SHA '%s': Not found" % (m.group(0), sha))
              m=rdesc.search(d)
              if m:
                desc=m.group(1)
                desc = desc.replace("'", "''")
                c2.execute("select sha from commits where description is '%s'" % desc)
                fsha = c2.fetchone()
                if fsha:
                  fsha=fsha[0]
                  print("  Real SHA may be '%s'" % fsha)
              # The Fixes: tag may be wrong. The sha may not be in the
              # upstream kernel, or the format may be completely wrong
              # and m.group(1) may not be a sha in the first place.
              # In that case, do nothing.
              pass
          if fsha:
            print("Commit %s fixed by %s" % (fsha[0:12], sha))
            # Calculate patch ID for fixing commit.
            ps = subprocess.Popen(['git', 'show', sha], stdout=subprocess.PIPE)
            spid = subprocess.check_output(['git', 'patch-id'], stdin=ps.stdout)
            patchid = spid.decode().split(' ', 1)[0]

            # Insert in reverse order: sha is fixed by fsha.
            # patchid is the patch ID associated with fsha (in the database).
            c.execute("INSERT into fixes (sha, fsha, patchid, ignore) VALUES (?, ?, ?, ?)",
                      (fsha[0:12], sha, patchid, 0))

  if last:
    c.execute("UPDATE tip set sha='%s' where ref=1" % last)

  conn.commit()
  conn.close()

def update_upstreamdb():
  start = upstream_base

  try:
    # see if we previously handled anything. If yes, use it.
    # Otherwise re-create database
    conn = sqlite3.connect(upstreamdb)
    c = conn.cursor()
    c.execute("select sha from tip")
    sha = c.fetchone()
    conn.close()
    if sha and sha[0] != "":
      start = sha[0]
    else:
      fail
  except:
    createdb(upstreamdb, mktables)

  os.chdir(upstream_path)
  subprocess.check_output(['git', 'pull'])

  handle(start)

  os.chdir(workdir)

update_upstreamdb()
