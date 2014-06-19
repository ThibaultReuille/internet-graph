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

    print("\nExtracing core graph ...")
    ograph = sn.Graph()

    print(". Referencing all bidirectional edges ...")
    b_edges = [ e[1] for e in igraph.get_edges().items() if e[1]["type"] == "AS<->AS" ]
    print("  . " + str(len(b_edges)) + " found.")

    print(". Adding nodes in bidirectional core ...")
    nodes = igraph.get_nodes()
    b_nodes = dict()
    for e in b_edges:
        src = e["src"]
        dst = e["dst"]
        if src not in b_nodes:
            b_nodes[src] = ograph.add_node(nodes[src])
        if dst not in b_nodes:
            b_nodes[dst] = ograph.add_node(nodes[dst])
        eid = ograph.add_edge(b_nodes[src], b_nodes[dst])
        ograph.set_edge_attribute(eid, "type", "AS<->AS")
    return ograph

def extract_ss_graph(igraph):

    print("\nExtracting sibling leaves graph ...")
    ograph = sn.Graph()

    print(". Building node degree table ...")
    degree_table = dict()
    edges = igraph.get_edges()
    for e in edges.values():
        src = e["src"]
        dst = e["dst"]
        if src not in degree_table:
            degree_table[src] = { "in" : 0, "out" : 0 }
        if dst not in degree_table:
            degree_table[dst] = { "in" : 0, "out" : 0 }
        degree_table[src]["out"] += 1
        degree_table[dst]["in"] += 1
    
    print(". Finding source edges ...")
    nodes = igraph.get_nodes()
    s_edges = [ e for e in edges.values() if degree_table[e["src"]]["in"] == 0 ]
    print("  . " + str(len(s_edges)) + " leaf edges found.")

    print(". Building graph with sources and their parents ...")
    ss_nodes = dict()
    for se in s_edges:
        if se["src"] not in ss_nodes:
            ss_nodes[se["src"]] = ograph.add_node(nodes[se["src"]])
        if se["dst"] not in ss_nodes:
            ss_nodes[se["dst"]] = ograph.add_node(nodes[se["dst"]])
        e = ograph.add_edge(ss_nodes[se["src"]], ss_nodes[se["dst"]])
        ograph.set_edge_attribute(e, "type", "AS->AS")

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

    igraph = None

    def load_internet_graph():
        if igraph is None:
            print("\nLoading internet graph in " + igraph_filename + " ...") 
            igraph = sn.Graph()
            igraph.load_json(igraph_filename)
            return igraph
    
    as_graph_filename = igraph_filename[:-5] + ".as.json"
    if os.path.isfile(as_graph_filename):
        print("\nAS graph already extracted, loading from file ...")
        as_graph = sn.Graph()
        as_graph.load_json(as_graph_filename)
    else:
        load_internet_graph(igraph_filename)
        as_graph = extract_AS_graph(igraph)
        print(". Saving result in " + as_graph_filename + " ...")
        as_graph.save_json(as_graph_filename)
        print(str(len(as_graph.get_nodes())) + " nodes, " + str(len(as_graph.get_edges())) + " edges.")
 
    core_graph_filename = as_graph_filename[:-5] + ".core.json"
    if os.path.isfile(core_graph_filename):
        print("\nCore graph already extracted, loading from file ...")
        core_graph = sn.Graph()
        core_graph.load_json(core_graph_filename)
    else:
        core_graph = extract_core_graph(as_graph)
        print(". Saving result in " + core_graph_filename + " ...")    
        core_graph.save_json(core_graph_filename)
        print(str(len(core_graph.get_nodes())) + " nodes, " + str(len(core_graph.get_edges())) + " edges.")
 
    ss_graph_filename = as_graph_filename[:-5] + ".ss.json"
    if os.path.isfile(ss_graph_filename):
        print("\nSibling sources graph already extracted, loading from file ...")
        ss_graph = sn.Graph()
        ss_graph.load_json(ss_graph_filename)
    else:
        ss_graph = extract_ss_graph(as_graph)
        print(". Saving result in " + ss_graph_filename + " ...")
        ss_graph.save_json(ss_graph_filename)
        print(str(len(ss_graph.get_nodes())) + " nodes, " + str(len(ss_graph.get_edges())) + " edges.")
       

