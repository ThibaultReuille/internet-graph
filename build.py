#!/usr/bin/env python

import sys
import os
import os.path
import urllib2
import datetime as datetime
from subprocess import call
import pprint as pp

SEMANTIC_NET_PATH = "../semantic-net"
sys.path.insert(0, SEMANTIC_NET_PATH)
import SemanticNet as sn

bgpdump = "./ripencc-bgpdump/bgpdump"
baseurl = "http://archive.routeviews.org/bgpdata/"

db_dir = "./db/"
bgpdata_dir = db_dir + "bgpdata/"
graph_dir = db_dir + "graphs/"
rir_dir = db_dir + "rir/"

_nodes = dict()
_edges = dict()

def check_configuration():
    try:
        os.stat(db_dir)
    except:
        print("Creating directory to store database ...")
        os.mkdir(db_dir)

    try:
        os.stat(bgpdata_dir)
    except:
        print("Creating directory to store bgpdata ...")
        os.mkdir(bgpdata_dir)
    
    try:
        os.stat(graph_dir)
    except:
        print("Creating directory to store graphs ...")
        os.mkdir(graph_dir)

    try:
        os.stat(rir_dir)
    except:
        print("Creating directory to store RIRs ...")
        os.mkdir(rir_dir)

    if not os.path.isfile(bgpdump):
        print("Error: bgpdump tool not found, please compile it and adjust bgpdump variable in script!")
        sys.exit()

def make_names(now):
    if now.hour % 2 > 0:
        now -= datetime.timedelta(hours=1)
    url = now.strftime(baseurl + "%Y.%m/RIBS/")
    archive = now.strftime("rib.%Y%m%d.%H00.bz2")
    return [url, archive, archive[:-4], archive[:-4] + ".txt"]

def curl_dl_file(url, filename):
    call(["curl", "--progress-bar", url, "-o", filename])

def add_or_get_node(graph, label):
    global _nodes
    if label not in _nodes:
        _nodes[label] = graph.add_node({ "label" : label })
    return _nodes[label]

def add_or_get_edge(graph, src, dst):
    global _edges
    key = src.hex + " -> " + dst.hex
    if key not in _edges:
        _edges[key] = graph.add_edge(src, dst)
    return _edges[key]

def enrich_with_rir(graph, labels, filename):
    inactive = 0
    with open(filename, "rU") as rir:
        line_count = 0
        for line in rir:
            if line.startswith("#"):
                continue
            split = line.split("|")
            
            if split[2] != "asn":
                continue

            rir = split[0]
            cc = split[1].upper()
            registration=split[5]
            if cc == "*":
                continue

            if len(split) < 7:
                print("Weird : " + line)
                continue

            #print(split)
            asn = split[3]

            if asn not in labels:
                inactive += 1
                continue
                
            attributes = graph.get_node_attributes(labels[asn])
            if "rir" in attributes:
                print ("ASN " + asn + " has multiple RIRs.")
            else:
                graph.set_node_attribute(labels[asn], "rir", rir)

            if "cc" in attributes:
                print ("ASN " + asn + " has multiple CCs.")
            else:
                graph.set_node_attribute(labels[asn], "cc", cc)

            if "registration" in attributes:
                print ("ASN " + asn + " has multiple registration dates.")
            else:
                graph.set_node_attribute(labels[asn], "registration", registration)

        print("  . " + str(inactive) + " inactive ASNs.")

if __name__ == "__main__":

    check_configuration()

    now = datetime.datetime.utcnow()
    print("\nUTC time is " + str(now))

    ts = now.strftime("-%Y%m%d")
    print("\nFetching RIR files ...")
    if not os.path.isfile(rir_dir + "arin" + ts):
        print(". ARIN")
        curl_dl_file("ftp://ftp.arin.net/pub/stats/arin/delegated-arin-extended-latest", rir_dir + "arin" + ts)
    if not os.path.isfile(rir_dir + "ripencc" + ts):
        print(". RIPENCC")
        curl_dl_file("ftp://ftp.ripe.net/ripe/stats/delegated-ripencc-latest", rir_dir + "ripencc" + ts)
    if not os.path.isfile(rir_dir + "afrinic" + ts):
        print(". AFRINIC")
        curl_dl_file("ftp://ftp.afrinic.net/pub/stats/afrinic/delegated-afrinic-latest", rir_dir + "afrinic" + ts)
    if not os.path.isfile(rir_dir + "apnic" + ts):
        print(". APNIC")
        curl_dl_file("ftp://ftp.apnic.net/pub/stats/apnic/delegated-apnic-latest", rir_dir + "apnic" + ts)
    if not os.path.isfile(rir_dir + "lacnic" + ts):
        print(". LACNIC")
        curl_dl_file("ftp://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-latest", rir_dir + "lacnic" + ts)

    # RIB file
    for i in range(0, 3):
        try:
            names = make_names(now)
            print("\nFetching RIB file : " + names[0] + names[1] + " ...")
            if os.path.isfile(bgpdata_dir + names[1]) or os.path.isfile(bgpdata_dir + names[2]) or os.path.isfile(bgpdata_dir + names[3]):
                print(". File is already in local database, skipping.")
                break
            curl_dl_file(names[0] + names[1], bgpdata_dir + names[1])
            break
        except:
            print(". RIB file can't be reached, trying H-" + str(2 * (i + 1)))
            now -= datetime.timedelta(hours=2)
            if i == 2:
                print("Too many errors, something is wrong. Stopping.")
                sys.exit()

    print("\nDecompressing " + names[1] + " ...")
    if os.path.isfile(bgpdata_dir + names[2]) or os.path.isfile(bgpdata_dir + names[3]):
        print(". File is already decompressed, skipping.")
    else:
        call(["bzip2", "-d", bgpdata_dir + names[1]])
        if not os.path.isfile(bgpdata_dir + names[2]):
            print("An error occured while decompressing file. Exiting.")
            sys.exit()

    print("\nUsing bgpdump to decode data ...")
    if os.path.isfile(bgpdata_dir + names[3]):
        print(". File is already decoded, skipping.")
    else:
        call([bgpdump, "-m", "-O", bgpdata_dir + names[3], bgpdata_dir + names[2]])
        if not os.path.isfile(bgpdata_dir + names[3]):
            print("An error occured while decoding file. Exiting.")
            sys.exit()
    
    print("\nBuilding graph from RIB information ...")
    graph = None
    graph_filename = graph_dir + names[2][4:] + ".json"
    if os.path.isfile(graph_filename):
        print(". Graph is already built, skipping.")
    else:
        graph = sn.Graph()
        with open(bgpdata_dir + names[3], "rU") as ribfile:
            
            line_count = 0
            for line in ribfile:
                split = line.split('|')
                if len(split) != 15:
                    continue

                # Discard the { .. } fields
                as_path = split[6].split("{")[0].split()

                origin = as_path[-1]
                prefix = split[5]

                origin_id = add_or_get_node(graph, origin)
                graph.set_node_attribute(origin_id, "type", "AS")
                prefix_id = add_or_get_node(graph, prefix)
                graph.set_node_attribute(prefix_id, "type", "Prefix")
                o_p_id = add_or_get_edge(graph, origin_id, prefix_id)
                graph.set_edge_attribute(o_p_id, "type", "AS->Prefix")

                # Find source and destination AS
                if len(as_path) < 2:
                    continue
                i = len(as_path) - 2
                while i >= 0 and as_path[i] == origin:
                    i -= 1
                if i < 0:
                    print("Weird : ", as_path)
                    continue
                dst = as_path[i]

                src_id = origin_id
                dst_id = add_or_get_node(graph, dst)
                graph.set_node_attribute(dst_id, "type", "AS")

                as_as_id = add_or_get_edge(graph, src_id, dst_id)
                graph.set_edge_attribute(as_as_id, "type", "AS->AS")

                line_count += 1
                if line_count % 100 == 0:
                    status = "Line : " + str(line_count)
                    sys.stdout.write(status + chr(8) * (len(status) + 1))

            
            print("\nBuilding graph node table by label ...")
            labels = dict()
            nodes = graph.get_nodes()
            for nid in nodes.keys():
                if nodes[nid]["label"] in labels:
                    print("Error : " + nodes[nid]["label"] + " is defined multiple times!")
                else:
                    labels[nodes[nid]["label"]] = nid

            print("\nEnriching AS nodes with RIR information ...")
            ts = now.strftime("-%Y%m%d")
            print(". Parsing ARIN file")
            enrich_with_rir(graph, labels, rir_dir + "arin" + ts)
            print(". Parsing RIPENCC file")
            enrich_with_rir(graph, labels, rir_dir + "ripencc" + ts)
            print(". Parsing AFRINIC file")
            enrich_with_rir(graph, labels, rir_dir + "afrinic" + ts)
            print(". Parsing APNIC file")
            enrich_with_rir(graph, labels, rir_dir + "apnic" + ts)
            print(". Parsing LACNIC file")
            enrich_with_rir(graph, labels, rir_dir + "lacnic" + ts)

            graph_filename = graph_filename[:-5] + ".json"
            print("\nSaving graph in " + graph_filename + " ...")
            graph.save_json(graph_filename)
            print(str(len(graph.get_nodes())) + " nodes, " + str(len(graph.get_edges())) + " edges.")
           

