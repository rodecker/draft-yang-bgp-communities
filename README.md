# draft-yang-bgp-communities

This document provides a YANG module for specifying BGP communities, Extended BGP communities and Large BGP communities.
The purpose of this is to provide a standardized way for publishing community definitions.
It also helps applications such as looking glasses to interpret communities seen in BGP announcements.

## Contents

This repository contains the following files:

* `draft/draft-yang-bgp-communities.xml` - XML specification of the draft
* `draft/draft-yang-bgp-communities.txt` - The draft, generated using [xml2rfc](https://pypi.org/project/xml2rfc/)
* `yang/draft-yang-bgp-communities.yang` - The YANG model, verified using [yanglint](https://pypi.org/project/libyang/)
* `scripts/parser.py` - An example parser
* `examples/bgp-communities.json` - An example JSON specification conforming to the YANG model
* `examples/bgp-communities.txt` - Example communities to match using the JSON specification
* `examples/bgp-communities.out` - Example output of the parser

## Usage

Generate the draft:
```
xml2rfc --v3 --text --html draft/draft-yang-bgp-communities.xml
```

Display the YANG module tree:
```
yanglint -f tree yang/draft-yang-bgp-communities.yang
```

Validate the JSON specification using the YANG model:
```
yanglint yang/draft-yang-bgp-communities.yang examples/bgp-communities.json
```

Parse the example communities using the example JSON specification:
```
scripts/parser.py examples/bgp-communities.txt examples/bgp-communities.json
```
