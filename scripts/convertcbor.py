#!/usr/bin/env python3.9
"""
Convert from and to cbor
"""

import argparse
import cbor2
import json
import os
import sys


def _keyname2sid(keyname, sdata):
  """
  Convert a descriptive key name to an SID
  """
  keyname == keyname[1:]
  for siditem in sdata['items']:
    if keyname == siditem['identifier']:
      return siditem['sid']


def _keys2sids(jdata, sdata, parent=''):
  """
  Convert all key names in a dictionary to SIDs
  """
  if isinstance(jdata, dict):
    for key in list(jdata.keys()):
      if isinstance(jdata[key], dict):
        full_key = parent + '/' + key
        _keys2sids(jdata[key], sdata, full_key)
      elif isinstance(jdata[key], list):
        for item in jdata[key]:
          full_key = parent + '/' + key
          _keys2sids(item, sdata, full_key)
      full_key = parent + '/' + key
      jdata[_keyname2sid(full_key, sdata)] = jdata.pop(key)
  return jdata


def _sid2keyname(sid, sdata):
  """
  Convert an SID to a descriptive key name
  """
  for siditem in sdata['items']:
    if sid == siditem['sid']:
      return siditem['identifier'].split('/')[-1]


def _sids2keys(cdata, sdata):
  """
  Convert all SID keys in a dictionary to names
  """
  if isinstance(cdata, dict):
    for key in list(cdata.keys()):
      if isinstance(cdata[key], dict):
        _sids2keys(cdata[key], sdata)
      elif isinstance(cdata[key], list):
        for item in cdata[key]:
          _sids2keys(item, sdata)
      cdata[_sid2keyname(key, sdata)] = cdata.pop(key)
  return cdata


def json2cbor(jsonfile, cborfile, sidfile):
  """
  Convert a json file to cbor
  """
  try:
    with open(jsonfile) as f:
      jdata = json.load(f)
    f.close()
  except Exception as e:
    sys.stderr.write(f"Could not load JSON file '{jsonfile}': {e}.\n")
    sys.exit(2)
  if sidfile:
    try:
      with open(sidfile) as f:
        sdata = json.load(f)
      f.close()
    except Exception as e:
      sys.stderr.write(f"Could not load SID file '{sidfile}': {e}.\n")
      sys.exit(2)
    jdata = _keys2sids(jdata, sdata)
  if os.path.exists(cborfile):
    sys.stderr.write(f"CBOR file '{cborfile}' already exists.\n")
    sys.exit(2)
  with open(cborfile, 'wb') as f:
    f.write(cbor2.dumps(jdata))
  f.close()


def cbor2json(cborfile, jsonfile, sidfile):
  """
  Convert a cbor file to json
  """
  try:
    with open(cborfile, 'rb') as f:
      cdata = cbor2.load(f)
    f.close()
  except Exception as e:
    sys.stderr.write(f"Could not load CBOR file '{cborfile}': {e}.\n")
    sys.exit(2)
  if sidfile:
    try:
      with open(sidfile) as f:
        sdata = json.load(f)
      f.close()
    except Exception as e:
      sys.stderr.write(f"Could not load SID file '{sidfile}': {e}.\n")
      sys.exit(2)
    cdata = _sids2keys(cdata, sdata)
  if os.path.exists(jsonfile):
    sys.stderr.write(f"JSON file '{jsonfile}' already exists.\n")
    sys.exit(2)
  with open(jsonfile, 'w') as f:
    f.write(f"{json.dumps(cdata, indent=2)}\n")
  f.close()


if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description='Convert files from and to CBOR.')
    action = argparser.add_mutually_exclusive_group(required=True)
    action.add_argument('--c2j', action='store_true', help='cbor to json')
    action.add_argument('--j2c', action='store_true', help='json to cbor')
    argparser.add_argument('-j', '--json', help='json file')
    argparser.add_argument('-c', '--cbor', help='cbor file')
    argparser.add_argument('-s', '--sid', help='sid file')
    args = argparser.parse_args()

    if args.j2c:
      json2cbor(jsonfile=args.json, cborfile=args.cbor, sidfile=args.sid)
    if args.c2j:
      cbor2json(cborfile=args.cbor, jsonfile=args.json, sidfile=args.sid)
