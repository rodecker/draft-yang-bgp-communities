#!/usr/bin/env python3
#
# Derive meaning of BGP communities from JSON definitions

import json
import re
import sys

def main(values_file,struct_file):
    bgprc = []
    bgplc = []
    bgpec = []

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
        elif re.match('^0x\d\d:0x\d\d:\d+:\d+$',line):
            bgpec.append(line)
        else:
            sys.stderr.write("Could not determine community type for '{}'\n".format(line))

    j = open(struct_file)
    jdata = json.load(j)
    candidates_rc = jdata['draft-yang-bgp-communities:bgp-communities']['regular']
    candidates_lc = jdata['draft-yang-bgp-communities:bgp-communities']['large']
    candidates_ec = jdata['draft-yang-bgp-communities:bgp-communities']['extended']

    for rc in bgprc:
      parse_regular_community(rc,candidates_rc)
    for lc in bgplc:
      parse_large_community(lc,candidates_lc)
    for ec in bgpec:
      parse_extended_community(ec,candidates_ec)

# Process RFC1997 community
# Input is a regular community and a list of JSON candidate definitions
# Returns the matched candidate or None
def parse_regular_community(rc,candidates):
    asn,content = rc.split(':')

    found = _try_candidates_rc(asn,content,candidates)
    if found:
        fieldvals = _candidate2fields(content,found['localadmin'])
        _print_match(rc,found,fieldvals)
        return found
    else:
        _print_unknown(rc)
        return None

# Process RFC8092 community
# Input is a large community and a list of JSON candidate definitions
# Returns the matched candidate or None
def parse_large_community(lc,candidates):
    asn,content1,content2 = lc.split(':')

    found = _try_candidates_lc(asn,content1,content2,candidates)
    if found:
        fieldvals = _candidate2fields_lc(content1,content2,
                                         found['localdatapart1'],
                                         found['localdatapart2'])
        _print_match(lc,found,fieldvals)
        return found
    else:
        _print_unknown(lc)
        return None

# Process RFC4360 community
# Input is an extended community and a list of JSON candidate definitions
# Returns the matched candidate or None
def parse_extended_community(ec,candidates):
    extype,exsubtype,asn,content = ec.split(':')

    found = _try_candidates_ec(extype,exsubtype,asn,content,candidates)
    if found:
        fieldvals = _candidate2fields(content,found['localadmin'])
        _print_match(ec,found,fieldvals)
        return found
    else:
        _print_unknown(ec)
        return None

# Try to find a matching Regular Community amongst candidate JSON definitions
def _try_candidates_rc(asn,content,candidates):
    for candidate in candidates:
        if asn != str(candidate['globaladmin']):
            continue
        if 'format' in candidate['localadmin']:
            if candidate['localadmin']['format'] == 'binary':
                content = _decimal2bits(content,16)
        if _try_candidate_fields(content,candidate['localadmin']['fields']):
            return candidate
    return False

# Try to find a matching Large Community amongst candidate JSON definitions
def _try_candidates_lc(asn,content1,content2,candidates):
    for candidate in candidates:
        if asn != str(candidate['globaladmin']):
            continue
        if 'format' in candidate['localdatapart1']:
            if candidate['localdatapart1']['format'] == 'binary':
                content1 = _decimal2bits(content1,32)
        if 'format' in candidate['localdatapart2']:
            if candidate['localdatapart2']['format'] == 'binary':
                content2 = _decimal2bits(content2,32)
        if _try_candidate_fields(content1,candidate['localdatapart1']['fields']) \
           and _try_candidate_fields(content2,candidate['localdatapart2']['fields']):
            return candidate
    return False

# Try to find a matching Extended Community amongst candidate JSON definitions
def _try_candidates_ec(extype,exsubtype,asn,content,candidates):
    for candidate in candidates:
        contentstring = content
        if int(extype,16) != candidate['type']:
            continue
        if int(exsubtype,16) != candidate['subtype']:
            continue
        if candidate['asn']:
            if asn != str(candidate['asn']):
                continue
        elif candidate['asn4']:
            if asn != str(candidate['asn4']):
                continue
        if 'format' in candidate['localadmin']:
            if candidate['localadmin']['format'] == 'binary':
                if 'asn4' in candidate:
                    contentstring = _decimal2bits(content,16)
                else:
                    contentstring = _decimal2bits(content,32)
        if _try_candidate_fields(contentstring,candidate['localadmin']['fields']):
            return candidate
    return False

# Try to match fields from a single candidate JSON definition
def _try_candidate_fields(content,cfields):
        pos = 0
        for cfield in cfields:
            if 'length' in cfield:
                value = content[pos:pos+cfield['length']]
            else:
                value = content

            if not re.match(cfield['pattern'],value):
                #print('{} != {}'.format(cfield['pattern'],value))
                return False

            if 'length' in cfield:
                pos = pos + cfield['length']
        return True

# Link values from tested community to field names in matched candidate
def _candidate2fields(contentbits,clocaladmin):
    fields = {}
    pos = 0
    if 'format' in clocaladmin:
        if clocaladmin['format'] == 'binary':
            contentbits = _decimal2bits(contentbits,16)
    for fid, f in enumerate(clocaladmin['fields']):
        if 'length' in f:
          l = f['length']
        else:
          l = len(contentbits)
        fields[fid] = contentbits[pos:pos+l]
        pos = pos + l
    return fields

# Link values from tested large community to field names in matched candidate
def _candidate2fields_lc(contentbits1,contentbits2,
                         clocaldatapart1,clocaldatapart2):
    fields = {}
    if 'format' in clocaldatapart1:
        if clocaldatapart1['format'] == 'binary':
            contentbits1 = _decimal2bits(contentbits1,32)
    if 'format' in clocaldatapart2:
        if clocaldatapart2['format'] == 'binary':
            contentbits2 = _decimal2bits(contentbits2,32)

    pos = 0
    foffset = 0
    for fid, f in enumerate(clocaldatapart1['fields']):
        if 'length' in f:
          l = f['length']
        else:
          l = len(contentbits1)
        fields[foffset + fid] = contentbits1[pos:pos+l]
        pos = pos + l

    pos = 0
    foffset = len(clocaldatapart1['fields'])
    for fid, f in enumerate(clocaldatapart2['fields']):
        if 'length' in f:
          l = f['length']
        else:
          l = len(contentbits2)
        fields[foffset + fid] = contentbits2[pos:pos+l]
        pos = pos + l
    return fields

# Convert decimal value to bit string
def _decimal2bits(decimal,length):
    return "{0:b}".format(int(decimal)).zfill(length)

# Print out a matched community
def _print_match(community,candidate,fieldvals):
    output_sections = []
    output_fields = []
    if 'localadmin' in candidate:
        for fid, f in enumerate(candidate['localadmin']['fields']):
             if 'description' in f:
                 output_fields.append('{}={}'.format(f['name'],f['description']))
             else:
                 output_fields.append('{}={}'.format(f['name'],fieldvals[fid]))
        output_sections.append(','.join(output_fields))
    elif 'localdatapart1' in candidate:
        offset = 0
        output_fields = []
        for fid, f in enumerate(candidate['localdatapart1']['fields']):
             if 'description' in f:
                 output_fields.append('{}={}'.format(f['name'],
                                                     f['description']))
             else:
                 output_fields.append('{}={}'.format(f['name'],
                                                     fieldvals[offset + fid]))
        output_sections.append(','.join(output_fields))

        offset = len(candidate['localdatapart1']['fields'])
        output_fields = []
        for fid, f in enumerate(candidate['localdatapart2']['fields']):
             if 'description' in f:
                 output_fields.append('{}={}'.format(f['name'],
                                                     f['description']))
             else:
                 output_fields.append('{}={}'.format(f['name'],
                                                     fieldvals[offset + fid]))
        output_sections.append(','.join(output_fields))
    output = '{} - {} ({})'.format(community,
                                    candidate['name'],
                                    ':'.join(output_sections))
    print(output)

# Print out an unmatched community
def _print_unknown(community):
    print("{} - Unknown".format(community))

if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.stderr.write("{} <txt> <json>\n".format(sys.argv[0]))
        sys.exit(2)
    main(sys.argv[1],sys.argv[2])
