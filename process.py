#!/usr/bin/env python

import sys
import os

SEMANTIC_NET_PATH = "../semantic-net"
sys.path.insert(0, SEMANTIC_NET_PATH)
import SemanticNet as sn

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: " + sys.argv[0] + " <graph.json>")
        sys.exit()

    if not sys.argv[1].endswith(".json"):
        print("Error: Input file must have .json extension!")
        sys.exit()

    graph_filename = sys.argv[1]

    if not os.path.isfile(graph_filename):
        print("Graph file doesn't exist! Exiting.")
        sys.exit()

    print("\nLoading graph in " + graph_filename + " ...") 
    graph = sn.Graph()
    graph.load_json(graph_filename)
    asn_filename = graph_filename[:-5] + ".asn.json"
    print("\nCreating ASN graph in " + viz_filename + " ...")

    print(". Removing all nodes except ASNs ...")
    for id in graph.get_nodes():
        att_type = graph.get_node_attribute(id, "type")
        if att_type != "AS":
            graph.remove_node(id)

    print(". Pruning edges ...")

    edge_table = dict()
    graph_edges = graph.get_edges()
    bidirectional = 0
    for id in graph_edges.keys():
        src = graph_edges[id]["src"].hex
        dst = graph_edges[id]["dst"].hex
        key_ab = src + " -> " + dst
        key_ba = dst + " -> " + src

        if key_ba in edge_table:
            graph.remove_edge(id)
            graph.set_edge_attribute(edge_table[key_ba], "type", "AS<->AS")
            bidirectional += 1
        else:
            graph.set_edge_attribute(id, "type", "AS->AS")
            edge_table[key_ab] = id
        
    print("  . " + str(bidirectional) + " bidirectional edge(s) found.")
        
    print(". Saving file in " + asn_filename + " ...")
    graph.save_json(asn_filename)
    print(str(len(graph.get_nodes())) + " nodes, " + str(len(graph.get_edges())) + " edges.")
