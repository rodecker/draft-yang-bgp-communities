#!/usr/bin/env python3

import argparse
import json
import re
import os
import sys
import pyangbind.lib.pybindJSON as pybindJSON
from pyangbind.lib.serialise import pybindJSONDecoder

from bindings import ietf_bgp_communities

def _key2attrname(key):
    return re.sub(r'-', '_', key)

def _key2attr(obj, key):
    return getattr(obj, f"{_key2attrname(key)}")

def _get_yang_description(obj, key):
    try:
        attr = _key2attrname(key)
        docstring = getattr(obj, f"_get_{attr}").__doc__
        docstring = re.sub(r'\n', ' ', docstring)
        docstring = re.sub(r'.+YANG Description: ', '', docstring)
        docstring = re.sub(r'\s+$', '', docstring)
        return docstring
    except:
        return None

def _input(prompt=""):
    try:
        return input(prompt)
    except EOFError:
        print("\n")
        exit(0)
    except KeyboardInterrupt:
        print("\n")
        exit(0)

def _input_index(obj):
    keys = list(obj)
    index = _input("Index? ")
    try:
        index = int(index)
        if 0 <= index < len(keys):
            key = keys[index]
            return key
        else:
            sys.stderr.write("Error: Invalid index.\n")
            return None
    except ValueError as e:
        sys.stderr.write("Error: Invalid index.\n")
        return None

def print_object(obj):
    print(f"{obj._yang_name}:")
    _print_dict(obj.get(filter=True),recurse=False)

def dump_object(obj):
    print(f"{obj._yang_name}:")
    _print_dict(obj.get(filter=True),recurse=True)

def _print_dict(obj_dict, recurse=False, depth=0):
    depth = depth + 1
    for name, attr in obj_dict.items():
        if hasattr(attr, "items"):
            if recurse == False and depth > 0:
                print(f"{' ' * depth}{name}: <{type(attr).__name__}>")
            else:
                print(f"{' ' * depth}{name}:")
                _print_dict(attr, depth=depth, recurse=recurse)
        else:
            print(f"{' ' * depth}{name}: {attr}")

def edit_object(obj):
    obj_dict = obj.get()
    #if not hasattr(obj,'_parent'):
    print_object(obj)
        
    while True:
        answer = _input("\n(e)dit, (p)rint, (d)ump, (u)p? ")
        if answer == 'e':
            for key, val in obj_dict.items():
                attr = _key2attr(obj, key)
                if attr._is_keyval == True:
                    # Cannot change object keys from within objects
                    continue
                if type(val).__name__ == 'OrderedDict':
                    _edit_dict(attr)
                    continue
                if type(val).__name__ == 'dict':
                    print(f"\n{key} ({_get_yang_description(obj, key)}):\n")
                    edit_object(attr)
                    continue
                else:
                    try:
                        print(f"\n{key} ({_get_yang_description(obj, key)}):")
                        answer = _input(f"[{attr}] > ")
                        if answer:
                            getattr(obj, "_set_" + f"{_key2attrname(key)}")(answer)
                    except ValueError as e:
                        sys.stderr.write(f"Error: {e.args[0]['error-string']}\n")
            #print_object(obj)
        elif answer == 'p':
            print_object(obj)
        elif answer == 'd':
            dump_object(obj)
        elif answer == 'u':
            return

def _edit_dict(obj):
    while True:
        try:
            print(f"\n{obj.yang_name()} " \
                  f"({_get_yang_description(obj._parent, obj.yang_name())}):")
            keys = list(obj)
            if len(keys) > 0:
                print(f"[0..{len(keys)}]")
            elif len(keys) == 1:
                print(f"[0]")
            else:
                print(f"[]")
            answer = _input("\n(a)dd, (r)remove, (e)dit, (p)rint, (d)ump? ")
            if answer == 'a':
                while True:
                    try:
                        print(f"\n{obj._yang_keys}:")
                        answer = _input("> ")
                        obj.add(answer)
                        edit_object(obj[answer])
                        break
                    except KeyError as e:
                        sys.stderr.write(f"Error: {e.args[0].split(',')[0]}\n")
            elif answer == 'r':
                index = _input_index(obj)
                if index:
                    obj.delete(index)
            elif answer == 'e':
                for index, key in enumerate(keys):
                    print(f"{index}: {key}")
                index = _input_index(obj)
                if index:
                    edit_object(obj[index])
            elif answer == 'p':
                index = _input_index(obj)
                if index:
                    print_object(obj[index])
            elif answer == 'd':
                index = _input_index(obj)
                if index:
                    dump_object(obj[index])
            elif answer:
                pass
            else:
                break
        except ValueError as e:
            sys.stderr.write(f"Error: {e.args[0]['error-string']}\n")

# Supported notations:
#   nnn -> any number
#   x -> any digit
#   a-b -> numeric range a upto b
def _fields_from_txt(localadmin):
    fields = []
    if re.search(r'nnn', localadmin):
        strlen = len(localadmin)
        index = 0
        while index < strlen:
            if localadmin[index] == 'n':
                if localadmin[index+1] == 'n' and \
                   localadmin[index+2] == 'n':
                    field = {}
                    field['pattern'] = '[0-9]+'
                    fields.append(field)
                    index = index + 3
                else:
                    return None
            else:
                if not re.match(r'\d', localadmin[index]):
                    return None
                if len(fields) > 0 and fields[-1]['pattern'] == localadmin[index-1]:
                    fields[-1]['pattern'] = fields[-1]['pattern'] + \
                                             localadmin[index]
                else:
                    field = {}
                    field['pattern'] = localadmin[index]
                    fields.append(field)
                index = index + 1
    elif re.search(r'x', localadmin):
        strlen = len(localadmin)
        index = 0
        while index < strlen:
            if localadmin[index] == 'x':
                field = {}
                field['pattern'] = '[0-9]'
                fields.append(field)
                index = index + 1
            else:
                if not re.match(r'\d', localadmin[index]):
                    return None
                if len(fields) > 0 and fields[-1]['pattern'] == localadmin[index-1]:
                    fields[-1]['pattern'] = fields[-1]['pattern'] + \
                                             localadmin[index]
                else:
                    field = {}
                    field['pattern'] = localadmin[index]
                    fields.append(field)
                index = index + 1
        pass
    elif re.search(r'-', localadmin):
        try:
            start, end = map(int, localadmin.split("-"))
            pattern = "(" + "|".join(str(i) for i in range(start, end + 1)) + ")"
            if len(pattern) < 3:
                return None
            field = {}
            field['pattern'] = pattern
            fields.append(field)            
        except:
            return None
        pass
    else:
        field = {}
        field['pattern'] = localadmin
        fields.append(field)
    return fields

'''
For file format, see:
https://github.com/NLNOG/lg.ring.nlnog.net/blob/main/README.md
'''
def import_text(obj, filename):
    name = os.path.basename(filename)
    globaladmin = None
    m = re.match(r'^as(\d+)\.txt$', name)
    if m:
        globaladmin = m.group(1)
    if not globaladmin:
        sys.stderr.write(f"Error: Could not derive ASN from file name '{args.filename}'\n")
        sys.exit(1)
    obj.bgp_communities._set_description(f"BGP Communities for AS{globaladmin}")

    try:
        f = open(filename, 'r')
    except Exception as e:
        sys.stderr.write(f"Error: {e}")
        exit(1)

    regular = obj.bgp_communities.regular
    extended = obj.bgp_communities.extended
    large = obj.bgp_communities.large
    try:
        for line in f:
            # Regular
            m = re.match(r'^(\d+):([-0-9nx]+),(.+)$', line)
            if m:
                globaladmin = m.group(1)
                localadmin = m.group(2)
                name = f"{globaladmin}:{localadmin}"
                description = m.group(3).strip()
                if name in regular.keys():
                    sys.stderr.write(f"Warning: duplicate entry '{name}'\n")
                    continue
                parsed_fields = _fields_from_txt(localadmin)
                if parsed_fields == None:
                    sys.stderr.write(f"Warning: Unable to parse entry '{name}'\n")
                    continue
                regular.add(name)
                regular[name]._set_description(description)
                regular[name]._set_global_admin(globaladmin)
                for index, pf in enumerate(parsed_fields):
                    regular[name].local_admin.field.add(f"field{index}")
                    field = regular[name].local_admin.field[f"field{index}"]
                    field._set_pattern(pf['pattern'])

            # Extended
            #elif re.match(r'^(soo|rt) (\d+):(\d+),(.+)$', line):

            # Large
            #elif re.match(r'^(\d+):(\d+):\d(\d+),(.+)$', line):

            # Unknown
            elif not re.match(r'^(#).+', line):
                sys.stderr.write(f"Warning: Skipped line '{line.strip()}'\n")
    except Exception as e:
        sys.stderr.write(f"Error: Import from '{filename}' failed: {e}\n")
        exit(1)

def _write_to_file(obj, filename, ask=False):
    if ask:
        while True:
            answer = _input("\nsave (y/n)? ")
            if answer == 'n':
                print("Bye.")
                exit(0)
            elif answer == 'y':
                print("\nfilename:")
                fanswer = _input(f"[{filename}] ")
                if fanswer:
                    filename = fanswer
            break
    try:
        f = open(filename, "w")
        f.write(pybindJSON.dumps(obj,
                                 mode='ietf',
                                 indent=2))
        print("Saved.")
        exit(0)
    except Exception as e:
            sys.stderr.write(f"Error: {e}\n")

def main():
    parser = argparse.ArgumentParser(description="BGP Community definition JSON Editor.")
    parser.add_argument("-c", "--check",
                        action='store_true', help="validate a definition file")
    parser.add_argument("-d", "--dump",
                        action='store_true', help="dump contents of a definition file")
    parser.add_argument("-e", "--edit",
                        action='store_true', help="edit a definition file")
    parser.add_argument("-f", "--from-text",
                        help="convert definition from a text file")
    parser.add_argument("-o", "--overwrite",
                        action='store_true', help="overwrite file if it exists")
    parser.add_argument("filename", help="File name")
    args = parser.parse_args()

    # Initialize commune object to work from
    commune = ietf_bgp_communities()
    if args.from_text:
        if os.path.exists(args.filename) and not args.overwrite:
            sys.stderr.write(f"Error: File '{args.filename}' exists.\n")
            sys.exit(1)
        import_text(commune, args.from_text)
    elif os.path.exists(args.filename):
        try:
            ietf_json = json.load(open(args.filename, 'r'))
        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")
            exit(1)
        try:
            pybindJSONDecoder.load_ietf_json(ietf_json, None, None, obj=commune)
        except Exception as e:
            sys.stderr.write(f"Error: {e.args[0]['error-string']}\n")
            exit(1)
    elif (args.check or args.dump) and not args.edit:
        sys.stderr.write(f"Error: File '{args.filename}' does not exist.\n")
        sys.exit(1)

    # Do work
    if args.check:
        # This should get a yanglint-like validation
        print("OK")
    if args.dump:
        dump_object(commune)
    if args.edit:
        edit_object(commune)
        _write_to_file(commune, args.filename, ask=True)
    elif args.from_text:
        _write_to_file(commune, args.filename, ask=False)
    else:
        print("Nothing to do.")
        exit(0)

if __name__ == '__main__':
    main()
