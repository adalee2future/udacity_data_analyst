import xml.etree.cElementTree as ET
import re
import codecs
import json

lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

CREATED = [ "version", "changeset", "timestamp", "user", "uid"]
POS = ["lat", "lon"]

def shape_element(element):
    node = {}
    node["created"] = {}
    if element.tag == "node" or element.tag == "way" :
        # YOUR CODE HERE
        attrib = element.attrib
        for key in CREATED:
            if key in attrib:
                node["created"][key] = attrib[key]
        if element.tag == "node":
            node["pos"] = [ float(attrib["lat"]), float(attrib["lon"]) ]
            node["type"] = "node"
        else:
            node["type"] = "way"
        for key in set(attrib.keys()).difference(CREATED + POS):
            node[key] = attrib[key]
        address = {}
        for tag_elem in element.iter('tag'):
            key, val = tag_elem.attrib['k'], tag_elem.attrib['v']
            # don't add problematic items, and dont update "type", "type" has already been "node" or "way"
            if problemchars.search(key) or key == "type":
                continue
            if lower.search(key):
                node[key] = val
            if lower_colon.search(key):
                if key.startswith('addr:'):
                    key = key.split(':')[-1]
                    address[key] = val                   
                else:
                    node[key] = val
        if len(address) > 0:
            node["address"] = address
        
        node_refs = []
        for nd_elem in element.iter('nd'):
            node_refs.append(nd_elem.attrib['ref'])
        if len(node_refs) > 0:
            node['node_refs'] = node_refs        
            
        return node
    else:
        return None

def process_map(file_in, pretty = False):
    file_out = "{0}.json".format(file_in)
    data = []
    with codecs.open(file_out, "w") as fo:
        for _, element in ET.iterparse(file_in):
            el = shape_element(element)
            if el:
                data.append(el)
                if pretty:
                    fo.write(json.dumps(el, indent=2)+"\n")
                else:
                    fo.write(json.dumps(el) + "\n")
    return data

shanghai_china = 'data/shanghai_china.osm'
process_map(shanghai_china)
