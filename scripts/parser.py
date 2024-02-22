#!/usr/bin/env python3
"""
Derive meaning of BGP communities from JSON definitions
"""

import json
import re
import sys


def main(values_file: str, struct_file: str):
    """
    Main function.
    """
    bgprc = []
    bgplc = []
    bgpec = []

    with open(values_file, "r", encoding="utf-8") as filehandle:
        for line in filehandle.readlines():
            line = line.rstrip()
            line = re.sub(r'\s*#.*', '', line)
            if re.match(r'^(\s*)$', line):
                continue
            if re.match(r'^\d+:\d+$', line):
                bgprc.append(line)
            elif re.match(r'^\d+:\d+:\d+$', line):
                bgplc.append(line)
            elif re.match(r'^0x\d\d:0x\d\d:\d+:\d+$', line):
                bgpec.append(line)
            else:
                sys.stderr.write(f"Could not determine community type for '{line}'\n")

    with open(struct_file, "r", encoding="utf-8") as filehandle:
        jdata = json.load(filehandle)
        candidates_rc = jdata['draft-ietf-grow-yang-bgp-communities:bgp-communities']['regular']
        candidates_lc = jdata['draft-ietf-grow-yang-bgp-communities:bgp-communities']['large']
        candidates_ec = jdata['draft-ietf-grow-yang-bgp-communities:bgp-communities']['extended']

    for regular_community in bgprc:
        parse_regular_community(regular_community, candidates_rc)
    for large_community in bgplc:
        parse_large_community(large_community, candidates_lc)
    for extended_community in bgpec:
        parse_extended_community(extended_community, candidates_ec)


def parse_regular_community(regular_community, candidates):
    """
    Process RFC1997 community
    Input is a regular community and a list of JSON candidate definitions
    Returns the matched candidate or None
    """
    asn, content = regular_community.split(':', 1)

    found = _try_candidates_rc(asn, content, candidates)
    if found:
        fieldvals = _candidate2fields(content, found['localadmin'])
        _print_match(regular_community, found, fieldvals)
        return found

    _print_unknown(regular_community)
    return None


def parse_large_community(large_community, candidates):
    """
    Process RFC8092 community
    Input is a large community and a list of JSON candidate definitions
    Returns the matched candidate or None
    """
    asn, content1, content2 = large_community.split(':', 2)

    found = _try_candidates_lc(asn, content1, content2, candidates)
    if found:
        fieldvals = _candidate2fields_lc(content1, content2,
                                         found['localdatapart1'],
                                         found['localdatapart2'])
        _print_match(large_community, found, fieldvals)
        return found

    _print_unknown(large_community)
    return None


def parse_extended_community(extended_community, candidates):
    """
    Process RFC4360 community
    Input is an extended community and a list of JSON candidate definitions
    Returns the matched candidate or None
    """
    extype, exsubtype, asn, content = extended_community.split(':', 3)

    found = _try_candidates_ec(extype, exsubtype, asn, content, candidates)
    if found:
        fieldvals = _candidate2fields(content, found['localadmin'])
        _print_match(extended_community, found, fieldvals)
        return found

    _print_unknown(extended_community)
    return None


def _try_candidates_rc(asn, content, candidates):
    """
    Try to find a matching Regular Community amongst candidate JSON definitions
    """
    for candidate in candidates:
        if asn != str(candidate['globaladmin']):
            continue
        if 'format' in candidate['localadmin']:
            if candidate['localadmin']['format'] == 'binary':
                content = _decimal2bits(content, 16)
        if _try_candidate_fields(content, candidate['localadmin']['fields']):
            return candidate
    return False


def _try_candidates_lc(asn, content1, content2, candidates):
    """
    Try to find a matching Large Community amongst candidate JSON definitions
    """
    for candidate in candidates:
        if asn != str(candidate['globaladmin']):
            continue
        if 'format' in candidate['localdatapart1']:
            if candidate['localdatapart1']['format'] == 'binary':
                content1 = _decimal2bits(content1, 32)
        if 'format' in candidate['localdatapart2']:
            if candidate['localdatapart2']['format'] == 'binary':
                content2 = _decimal2bits(content2, 32)
        if _try_candidate_fields(content1, candidate['localdatapart1']['fields']) \
           and _try_candidate_fields(content2, candidate['localdatapart2']['fields']):
            return candidate
    return False


def _try_candidates_ec(extype, exsubtype, asn, content, candidates):
    """
    Try to find a matching Extended Community amongst candidate JSON definitions
    """
    for candidate in candidates:
        contentstring = content
        if int(extype, 16) != candidate['type']:
            continue
        if int(exsubtype, 16) != candidate['subtype']:
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
                    contentstring = _decimal2bits(content, 16)
                else:
                    contentstring = _decimal2bits(content, 32)
        if _try_candidate_fields(contentstring, candidate['localadmin']['fields']):
            return candidate
    return False


def _try_candidate_fields(content, cfields):
    """
    Try to match fields from a single candidate JSON definition
    """
    pos = 0
    for cfield in cfields:
        if 'length' in cfield:
            value = content[pos:pos + cfield['length']]
        else:
            value = content

        pattern = cfield['pattern']
        if pattern.startswith('^'):
          pattern = pattern[1:]
        if pattern.endswith('$'):
          pattern = pattern[:-1]
        if not re.match("^{}$".format(pattern), value):
            # print('{} != {}'.format(pattern,value))
            return False

        if 'length' in cfield:
            pos = pos + cfield['length']
    return True


def _candidate2fields(contentbits, clocaladmin):
    """
    Link values from tested community to field names in matched candidate
    """
    fields = {}
    pos = 0
    if 'format' in clocaladmin:
        if clocaladmin['format'] == 'binary':
            contentbits = _decimal2bits(contentbits, 16)
    for fid, field in enumerate(clocaladmin['fields']):
        if 'length' in field:
            length = field['length']
        else:
            length = len(contentbits)
        fields[fid] = contentbits[pos:pos + length]
        pos = pos + length
    return fields


def _candidate2fields_lc(contentbits1,
                         contentbits2,
                         clocaldatapart1,
                         clocaldatapart2):
    """
    Link values from tested large community to field names in matched candidate
    """
    fields = {}
    if 'format' in clocaldatapart1:
        if clocaldatapart1['format'] == 'binary':
            contentbits1 = _decimal2bits(contentbits1, 32)
    if 'format' in clocaldatapart2:
        if clocaldatapart2['format'] == 'binary':
            contentbits2 = _decimal2bits(contentbits2, 32)

    pos = 0
    foffset = 0
    for fid, field in enumerate(clocaldatapart1['fields']):
        if 'length' in field:
            length = field['length']
        else:
            length = len(contentbits1)
        fields[foffset + fid] = contentbits1[pos:pos + length]
        pos = pos + length

    pos = 0
    foffset = len(clocaldatapart1['fields'])
    for fid, field in enumerate(clocaldatapart2['fields']):
        if 'length' in field:
            length = field['length']
        else:
            length = len(contentbits2)
        fields[foffset + fid] = contentbits2[pos:pos + length]
        pos = pos + length
    return fields


def _decimal2bits(decimal, length):
    """
    Convert decimal value to bit string
    """
    return f"{int(decimal):0{length}b}"


def _print_match(community, candidate, fieldvals):
    """
    Print out a matched community
    """
    output_sections = []
    output_fields = []
    for attr in ('globaladmin','asn','asn4'):
      if attr in candidate:
        asn = candidate[attr]
    if 'localadmin' in candidate:
        for fid, field in enumerate(candidate['localadmin']['fields']):
            if 'description' in field:
                output_fields.append(f'{field["name"]}={field["description"]}')
            else:
                output_fields.append(f'{field["name"]}={fieldvals[fid]}')
        output_sections.append(','.join(output_fields))
    elif 'localdatapart1' in candidate:
        offset = 0
        output_fields = []
        for fid, field in enumerate(candidate['localdatapart1']['fields']):
            if 'description' in field:
                output_fields.append(f"{field['name']}={field['description']}")
            else:
                output_fields.append(f"{field['name']}={fieldvals[offset + fid]}")
        output_sections.append(','.join(output_fields))

        offset = len(candidate['localdatapart1']['fields'])
        output_fields = []
        for fid, field in enumerate(candidate['localdatapart2']['fields']):
            if 'description' in field:
                output_fields.append(f'{field["name"]}={field["description"]}')
            else:
                output_fields.append(f'{field["name"]}={fieldvals[offset + fid]}')
        output_sections.append(','.join(output_fields))
    if 'category' in candidate:
        output = f'{community} - {candidate["name"]}/{candidate["category"]} ' \
                 + f'({asn}:{":".join(output_sections)})'
    else:
        output = f'{community} - {candidate["name"]} ({asn}:{":".join(output_sections)})'
    print(output)


def _print_unknown(community):
    """
    Print out an unmatched community
    """
    print(f"{community} - Unknown")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.stderr.write(f"{sys.argv[0]} <textfile> <jsonfile>\n")
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])
