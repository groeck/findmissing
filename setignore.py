#!/usr/bin/env python3

import sqlite3
import sys
from common import upstreamdb

def setignore(sha, value):
  db = sqlite3.connect(upstreamdb)
  c = db.cursor()

  c.execute("select sha from fixes where sha='%s'" % sha)
  fsha = c.fetchone()
  if not fsha or fsha[0] != sha:
    print("Error: sha '%s' not in fixes table" % sha)
    sys.exit(1)

  c.execute("update fixes set ignore='%s' where sha='%s'" % (value, sha))

  db.commit()
  db.close()

if len(sys.argv) != 3 or (sys.argv[2] != "0" and sys.argv[2] != "1"):
  print("Usage: %s <sha> {0|1}" % sys.argv[0])
  sys.exit(1)

setignore(sys.argv[1], sys.argv[2])
