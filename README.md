# draft-yang-bgp-communities

This document provides a YANG module for specifying BGP communities, Extended BGP communities and Large BGP communities.
The purpose of this is to provide a standardized way for publishing community definitions.
It also helps applications such as looking glasses to interpret communities seen in BGP announcements.

## Contents

This repository contains the following files:

* `draft/draft-yang-bgp-communities.xml` - XML specification of the draft
* `draft/draft-yang-bgp-communities.txt` - The draft in plain text format, generated using [xml2rfc](https://pypi.org/project/xml2rfc/)
* `draft/draft-yang-bgp-communities.html` - The draft in html format, generated using [xml2rfc](https://pypi.org/project/xml2rfc/)
* `yang/draft-ietf-grow-yang-bgp-communities.yang` - The YANG model, verified using [yanglint](https://pypi.org/project/libyang/)
* `scripts/parser.py` - An example parser
* `examples/bgp-communities.json` - An example JSON specification conforming to the YANG model
* `examples/bgp-communities.txt` - Example communities to match using the JSON specification
* `examples/bgp-communities.out` - Example output of the parser
* `examples/rfc4384.json` - Example JSON specification for [RFC4384](https://www.rfc-editor.org/info/rfc4384) communities used in the draft
* `examples/rfc8195.json` - Example JSON specification for [RFC8195](https://www.rfc-editor.org/info/rfc8195) community used in the draft
* `resources/inventory.md` - A non-exhaustive list of BGP community definitions found on the web

## Usage

Generate the draft:
```
xml2rfc --v3 --text --html draft/draft-yang-bgp-communities.xml
```

Display the YANG module tree:
```
wget https://www.yangcatalog.org/all_modules/ietf-inet-types@2024-10-21.yang -O yang/ietf-inet-types@2024-10-21.yang
yanglint -p yang -f tree yang/ietf-bgp-communities@2025-03-13.yang
```

Validate the YANG module:
```
pyang --verbose --ietf -p yang yang/ietf-bgp-communities@2025-03-13.yang
```

Validate the JSON specification using the YANG model:
```
yanglint -p yang yang/ietf-bgp-communities@2025-03-13.yang examples/bgp-communities.json
```

Generate a SID file from the YANG model (using Experimental/Private SIDs):
```
cat yang/ietf-bgp-communities@2025-03-13.yang | pyang -p yang --sid-generate-file 60000:100
```

Parse the example communities using the example JSON specification:
```
scripts/parser.py examples/bgp-communities.txt examples/bgp-communities.json
```

Convert the example JSON specification to a CBOR file:
```
scripts/convertcbor.py --j2c -j examples/bgp-communities.json -c examples/bgp-communities.cbor
scripts/convertcbor.py --j2c -j examples/bgp-communities.json -s *.sid -c examples/bgp-communities-sids.cbor
```

Convert a CBOR file to JSON:
```
scripts/convertcbor.py --c2j -c <in.cbor> [-s *.sid] -j <out.json>
```

## Implementations

The following known implementations exist.

### Publishing ASNs

* [AS197000](https://www-static.ripe.net/dynamic/draft-ietf-grow-yang-bgp-communities/as197000.json)
* [AS25152](https://www-static.ripe.net/dynamic/draft-ietf-grow-yang-bgp-communities/as25152.json)

### Parsers

* [NLNOG Looking Glass](https://github.com/NLNOG/lg.ring.nlnog.net/)
