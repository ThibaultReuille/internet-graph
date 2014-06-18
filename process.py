#!/usr/bin/env python

import sys
import os

SEMANTIC_NET_PATH = "../semantic-net"
sys.path.insert(0, SEMANTIC_NET_PATH)
import SemanticNet as sn

def extract_AS_graph(igraph):

    print("\nExtracting AS graph ...")
    ograph = sn.Graph()

    print(". Adding AS nodes only ...")

    nodes = igraph.get_nodes()
    node_table = dict()
    for nid in nodes.keys():
        if nodes[nid]["type"] == "AS":
            node_table[nid] = ograph.add_node(nodes[nid])
   
    print(". Adding AS->AS edges only ...")

    edges = igraph.get_edges()
    for eid in edges.keys():
        if edges[eid]["type"] == "AS->AS":
            ograph.add_edge(node_table[edges[eid]["src"]], node_table[edges[eid]["dst"]])

    print(". Pruning edges ...")

    edge_table = dict()
    graph_edges = ograph.get_edges()
    bidirectional = 0
    for id in graph_edges.keys():
        src = graph_edges[id]["src"].hex
        dst = graph_edges[id]["dst"].hex
        key_ab = src + " -> " + dst
        key_ba = dst + " -> " + src

        if key_ba in edge_table:
            ograph.remove_edge(id)
            ograph.set_edge_attribute(edge_table[key_ba], "type", "AS<->AS")
            bidirectional += 1
        else:
            ograph.set_edge_attribute(id, "type", "AS->AS")
            edge_table[key_ab] = id
        
    print("  . " + str(bidirectional) + " bidirectional edge(s) found.")
    return ograph

def extract_core_graph(igraph):

    print("Extracing core graph ...")
    ograph = sn.Graph()

    print(". Referencing all bidirectional edges ...")
    edges = [ e[1] for e in igraph.get_edges().items() if e[1]["type"] == "AS<->AS" ]
    print("  . " + str(len(edges)) + " found.")

    print(edges)
    return ograph

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: " + sys.argv[0] + " <graph.json>")
        sys.exit()

    if not sys.argv[1].endswith(".json"):
        print("Error: Input file must have .json extension!")
        sys.exit()

    igraph_filename = sys.argv[1]

    if not os.path.isfile(igraph_filename):
        print("Graph file doesn't exist! Exiting.")
        sys.exit()

    print("\nLoading graph in " + igraph_filename + " ...") 
    igraph = sn.Graph()
    igraph.load_json(igraph_filename)
    
    as_graph_filename = igraph_filename[:-5] + ".as.json"
    as_graph = extract_AS_graph(igraph)
    print(". Saving result in " + as_graph_filename + " ...")
    as_graph.save_json(as_graph_filename)
    print(str(len(as_graph.get_nodes())) + " nodes, " + str(len(as_graph.get_edges())) + " edges.")
    igraph = as_graph

    '''
    core_graph_filename = igraph_filename[:-5] + ".core.json"
    core_graph = extract_core_graph(as_graph)
    print(". Saving result in " + core_graph_filename + " ...")    
    core_graph.save_json(core_graph_filename)
    print(str(len(core_graph.get_nodes())) + " nodes, " + str(len(core_graph.get_edges())) + " edges.")
    igraph = core_graph
    '''

