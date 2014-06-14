#!/usr/bin/env python

import sys
import os
import os.path
import urllib2
import datetime as datetime
from subprocess import call
import pprint as pp
import semanticnet.SemanticNet as sn

bgpdump = "./ripencc-bgpdump/bgpdump"
baseurl = "http://archive.routeviews.org/bgpdata/"

bgpdata_dir = "./bgpdata/"
graph_dir = "./graphs/"

nodes = dict()
edges = dict()

def check_configuration():
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

    if not os.path.isfile(bgpdump):
        print("Error: bgpdump tool not found, please compile it and adjust bgpdump variable in script!")
        sys.exit()

def make_names(now):
    if now.hour % 2 > 0:
        now -= datetime.timedelta(hours=1)
    url = now.strftime(baseurl + "%Y.%m/RIBS/")
    archive = now.strftime("rib.%Y%m%d.%H00.bz2")
    return [url, archive, archive[:-4], archive[:-4] + ".txt"]

def download_file(url, filename):
    u = urllib2.urlopen(url)
    f = open(filename, 'wb')
    meta = u.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    print("Downloading: %s Bytes: %s" % (filename, file_size))

    file_size_dl = 0
    block_sz = 8192
    while True:
        buffer = u.read(block_sz)
        if not buffer:
            break

        file_size_dl += len(buffer)
        f.write(buffer)
        status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
        status = status + chr(8)*(len(status)+1)
        print status,

    f.close()

def add_or_get_node(graph, label):
    global nodes
    if label not in nodes:
        nodes[label] = graph.add_node({ "label" : label })
    return nodes[label]

def add_or_get_edge(graph, src, dst):
    global edges
    key = str(src) + " " + str(dst)
    if key not in edges:
        edges[key] = graph.add_edge(src, dst)
    return edges[key]

if __name__ == "__main__":

    check_configuration()

    now = datetime.datetime.utcnow()
    print("\nUTC time is " + str(now))

    for i in range(0, 3):
        try:
            names = make_names(now)
            print("\nFetching RIB file : " + names[0] + names[1] + " ...")
            if os.path.isfile(bgpdata_dir + names[1]) or os.path.isfile(bgpdata_dir + names[2]) or os.path.isfile(bgpdata_dir + names[3]):
                print(". File is already in local database, skipping.")
                break
            download_file(names[0] + names[1], bgpdata_dir + names[1])
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

                as_path = split[6].split()
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

                src_id = add_or_get_node(graph, origin)
                dst_id = add_or_get_node(graph, dst)
                graph.set_node_attribute(dst_id, "type", "AS")

                as_as_id = add_or_get_edge(graph, src_id, dst_id)
                graph.set_edge_attribute(as_as_id, "type", "AS->AS")
                    
                line_count += 1
                if line_count % 100 == 0:
                    status = "Line : " + str(line_count)
                    sys.stdout.write(status + chr(8) * (len(status) + 1))

            print("\nSaving graph in " + graph_filename)
            graph.save_json(graph_filename)
            print("Done.")

    if not os.path.isfile(graph_filename):
        print("Graph file doesn't exist! Exiting.")
        sys.exit()

    if graph is None:
        print("\nLoading graph in " + graph_filename + " ...") 
        graph = sn.Graph()
        graph.load_json(graph_filename)
    viz_filename = graph_filename[:-5] + ".viz.json"
    print("\nCreating visual graph in " + viz_filename + " ...")

    print(". Removing prefix nodes ...")
    for id in graph.get_nodes():
        att_type = graph.get_node_attribute(id, "type")
        if att_type == "Prefix":
            graph.remove_node(id)

    '''
    print(". Building edge table ...")
    edges = graph.get_edges()
    print(edges.keys()[0:10])

    d = dict()
    for id in edges.keys():
        src = str(edges[id]["src"])
        dst = str(edges[id]["dst"])
        key = src + " -> " + dst
        d[key] = id
    print(d.keys()[0:10])

    print(". Pruning edges")
    directional = 0
    bidirectional = 0
    for id in edges.keys():
        src = str(edges[id]["src"])
        dst = str(edges[id]["dst"])
        key_sd = src + " -> " + dst
        key_ds = dst + " -> " + src

        print(key_sd, key_ds)

        if (key_sd in d) and not(key_ds in d):
            graph.set_edge_attribute(id, "link", "->")
            directional += 1
        elif (key_sd in d) and (key_ds in d):
            print(key_sd + " is bidirectional.")
            graph.remove_edge(d[key_ds])
            graph.set_edge_attribute(id, "link", "<->")
            bidirectional += 1
        else:
            print("Internal Error.")

    print(str(directional) + " directional and " + str(bidirectional) + " bidirectional edges.")
    '''
        
    print(". Saving file in " + viz_filename + " ...")
    graph.save_json(viz_filename)
            

 
