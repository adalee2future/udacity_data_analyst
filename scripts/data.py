import xml.etree.cElementTree as ET
import re
import codecs
import json
import time

lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

CREATED = [ "version", "changeset", "timestamp", "user", "uid"]
POS = ["lat", "lon"]

# mapping to audit street
street_mapping = {
    u'Rd\.': u'Road',
    u'Rd': u'Road',
    u'Rode': u'Road',
    u'Roaf': u'Road',
    u'Ave\.': u'Avenue',
    u'avenue': u'Avenue'
}

# mapping to audit city
city_mapping = {
    u'.+Shanghai': u'Shanghai',
    u'\u53cb\u8c0a\u8def\u8857\u9053': u'Shanghai',
    u'\u65e0\u9521': u'Wuxi',
    u'\u6e56\u5dde\u5e02': u'Huzhou',
    u'fenghua': u'Fenghua',
    u'\u5b81\u6ce2': u'Ningbo',
    u'\u6cf0\u5174': u'\u6cf0\u5174\u5e02',
    u'\u677e\u6c5f': u'Shanghai',
    u'shanghai': u'Shanghai',
    u'\u5609\u5174': u'Jiaxing',
    u'\u4e34\u6e2f\u65b0\u57ce': u'Shanghai',
    u'Qidong': u'Nantong',
    u'\u67ab\u6cfe\u9547': u'Shanghai',
    u'Kun[Ss]han': u'Kunshan',
    u'\u5357\u4eac': u'\u5357\u4eac\u5e02',
    u'\u95f5\u884c': u'Shanghai',
    u'jiaxing': u'Jiaxing',
    u'Shanghai.+': u'Shanghai',
    u'Anting': u'Shanghai',
    u'\u5357\u901a': u'Nantong',
    u'Nantong': u'Nantong',
    u'\u6d66\u6c5f\u6f15\u6cb3\u6cfe\u9ad8\u79d1\u6280\u56ed\u533a': u'Shanghai',
    u'\u6606\u5c71\u5e02': u'Kunshan',
    u'[h]an\\w\\whou': u'Hangzhou',
    u'\u4e0a\u6d77': u'Shanghai',
    u'\u82cf\u5dde': u'Suzhou',
    u'\u65b0\u5e02\u9547': u'Huzhou',
    u'\u65b0\u57ed\u9547': u'\u5e73\u6e56\u5e02',
    u'Suzhou.+': u'Suzhou',
    u'\u676d\u5dde': u'Hangzhou',
    u'\u91d1\u5c71\u533a': u'Shanghai'
}

def shape_element(element, street_file, city_file, postcode_file):

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
            # keys that only consists lower characters or "_"
            if lower.search(key):
                node[key] = val
            # keys that contains characters, "_", ";"
            if lower_colon.search(key):
                if key.startswith('addr:'):
                    key = key.split(':')[-1]
                    # audit street, some abbreviation, and some misspell
                    if key == "street":
                        # sort street_mapping.items() to make sure searching 'Rd.' before 'Rd'
                        for street_mapping_key, street_mapping_val in sorted(street_mapping.items(), reverse=True):
                            if re.search(street_mapping_key, val):
                                old_val = val
                                val = re.sub(street_mapping_key, street_mapping_val, val)
                                # write out street audit information to street_file
                                msg = u'Audit street: "{}" --> "{}"\n'.format(old_val, val).encode("utf8")
                                street_file.write(msg)
                                break
                    # audit city
                    elif key == "city":
                        for city_mapping_key, city_mapping_val in city_mapping.items():
                            if re.search(city_mapping_key, val):
                                old_val = val
                                val = city_mapping_val
                                # write out city audit information to city_file
                                msg = u'Audit city: "{}" --> "{}"\n'.format(old_val, val).encode("utf8")
                                city_file.write(msg)
                                break
                    # audity postcode, make sure all postcode consist only numbers
                    elif key == "postcode":
                        # postcode in China should be exactly 6 numbers
                        if not re.search(u'^[0-9]{6}$', val):
                            old_val = val
                            val = re.search(u'[0-9]+', val).group()
                            if len(val) == 6:
                                # automately correction for postcode sucessfully
                                msg = u'Audit postcode: "{}" --> "{}"\n'.format(old_val, val).encode("utf8")       
                            else:
                                # incorrect postcode with wrong length, need manually correct them
                                msg = u'Could not correct postcode "{}", please investigate manually.\n'.format(old_val).encode("utf8")
                            # write out audit message to postcode_file
                            postcode_file.write(msg)

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

def process_map(file_in, street_filename, city_filename, postcode_filename, pretty = False):
    file_out = "{0}.json".format(file_in)
    # open three files to store auditing information about street, city and postcode
    street_file = open(street_filename, 'w')
    city_file = open(city_filename, 'w')
    postcode_file = open(postcode_filename, 'w')

    data = []
    with codecs.open(file_out, "w") as fo:

        for _, element in ET.iterparse(file_in):
            el = shape_element(element, street_file, city_file, postcode_file)
            if el:
                data.append(el)
                if pretty:
                    fo.write(json.dumps(el, indent=2)+"\n")
                else:
                    fo.write(json.dumps(el) + "\n")
    # close three auditing files
    street_file.close()
    city_file.close()
    postcode_file.close()
    return data

shanghai_china = 'data/shanghai_china.osm'
street_file = "auditing_street.txt"
city_file = "auditing_city.txt"
postcode_file = "auditing_postcode.txt"
print "processing, need less than 2 minutes, please wait..."
start = time.time()
data = process_map(shanghai_china, street_file, city_file, postcode_file)
end = time.time()
print "process takes {} seconds".format(end-start)

