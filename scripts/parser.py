#!/usr/bin/env python3
#
# Derive meaning of BGP communities from JSON definitions

import json
import re
import sys

def main(values_file,struct_file):
    bgprc = []
    bgplc = []

    f = open(values_file)
    for line in f.readlines():
        line = line.rstrip()
        line = re.sub('\s*#.*','',line)
        if re.match('^(\s*)$',line):
            continue
        if re.match('^\d+:\d+$',line):
            bgprc.append(line)
        elif re.match('^\d+:\d+:\d+$',line):
            bgplc.append(line)
        else:
            sys.stderr.write("Could not determine community type for '{}'\n".format(line))

    j = open(struct_file)
    jdata = json.load(j)
    candidates_rc = jdata['draft-yang-bgp-communities:bgp-communities']['regular']
    candidates_lc = jdata['draft-yang-bgp-communities:bgp-communities']['large']

    for rc in bgprc:
      parse_regular_community(rc,candidates_rc)
    for lc in bgplc:
      parse_large_community(lc,candidates_lc)

# Process RFC1997 community
# Input is a regular community and a list of JSON candidate definitions
# Returns the matched candidate or None
def parse_regular_community(rc,candidates):
    asn,fields = rc.split(':')
    contentbits = _decimal2bits(fields,16)

    found = _try_candidates(asn,contentbits,candidates)
    if found:
        fieldvals = _candidate2fields(contentbits,found['fields'])
        _print_match(rc,found,fieldvals)
        return found
    else:
        _print_unknown(rc)
        return None

# Process RFC8092 community
# Input is a large community and a list of JSON candidate definitions
# Returns the matched candidate or None
def parse_large_community(lc,candidates):
    asn,fields1,fields2 = lc.split(':')
    contentbits = _decimal2bits(fields1,32) + _decimal2bits(fields2,32)

    found = _try_candidates(asn,contentbits,candidates)
    if found:
        fieldvals = _candidate2fields(contentbits,found['fields'])
        _print_match(lc,found,fieldvals)
        return found
    else:
        _print_unknown(lc)
        return None

# Try to find a match amongst candidate JSON definitions
def _try_candidates(asn,contentbits,candidates):
    for candidate in candidates:
        if asn != str(candidate['asn']):
            continue
        if _try_candidate_fields(contentbits,candidate['fields']):
            return candidate
    return False

# Try to match fields from a single candidate JSON definition
def _try_candidate_fields(contentbits,cfields):
        pos = 0
        for cfield in cfields:
            bits = contentbits[pos:pos+cfield['length']]
            if 'value' in cfield:
                value = _bits2decimal(bits)
                cvalue = _glob2regex(cfield['value'])
                if not re.match(cvalue,value):
                    return False
            elif 'range' in cfield:
                value = _bits2decimal(bits)
                rstart,rend = cfield['range'].split('-')
                if not rstart <= value <= rend:
                    return False
            elif 'bvalue' in cfield:
                cvalue = _glob2regex(cfield['bvalue'])
                if not re.match(cvalue,bits):
                    return False
            elif 'brange' in cfield:
                rstart,rend = cfield['brange'].split('-')
                if not rstart <= bits <= rend:
                    return False
            pos = pos + cfield['length']
        return True

# Link values from tested community to field names in matched candidate
def _candidate2fields(contentbits,cfields):
    fields = {}
    pos = 0
    for fid, f in enumerate(cfields):
        fields[fid] = contentbits[pos:pos+f['length']]
        pos = pos + f['length']
    return fields

# Convert decimal value to bit string
def _decimal2bits(decimal,length):
    return "{0:b}".format(int(decimal)).zfill(length)

# Convert bit string to decimal value
def _bits2decimal(bits):
    return str(int(bits, 2))

# Convert '?' and '*' wildcards to their regular expression equivalents
def _glob2regex(glob):
    glob = re.sub('\?','.',glob)
    glob = re.sub('\*','.+',glob)
    return glob

# Print out a matched community
def _print_match(community,candidate,fieldvals):
    name = candidate['name']
    for fid, f in enumerate(candidate['fields']):
        if 'value' in candidate['fields'][fid]:
            name = re.sub('\$' + str(fid),_bits2decimal(fieldvals[fid]),name)
        elif 'bvalue' in candidate['fields'][fid]:
            name = re.sub('\$' + str(fid),_bits2decimal(fieldvals[fid]),name)
    print("{} - {}".format(community,name))

# Print out an unmatched community
def _print_unknown(community):
    print("{} - Unknown".format(community))

if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.stderr.write("{} <txt> <json>\n".format(sys.argv[0]))
        sys.exit(2)
    main(sys.argv[1],sys.argv[2])
