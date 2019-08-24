#!/usr/bin/env python3

import sys
import os

import networkx as nx

def extract_AS_graph(igraph):

    print("\nExtracting AS graph ...")
    ograph = nx.Graph() # NOTE: This will unify edges from the DiGraph

    print(". Adding AS nodes only ...")

    node_table = dict()
    for nid in igraph.nodes:
        if igraph.nodes[nid]["type"] == "AS":
            ograph.add_node(nid, **igraph.nodes[nid])
   
    print(". Adding AS->AS edges only ...")

    for edge in igraph.edges:
        edge_data = igraph.edges[edge[0], edge[1]]
        if edge_data.get("type") == "AS->AS":
            ograph.add_edge(edge[0], edge[1], **edge_data)

    '''
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
    '''

    return ograph

def extract_cc_map(igraph):
    cc_map = dict()
    for node in igraph.nodes:
        cc = igraph.nodes[node].get("cc")
        if cc is None or len(cc) == 0:
             cc = ""
        if cc not in cc_map:
            cc_map[cc] = 0
        cc_map[cc] += 1
    return cc_map

def extract_cc_graph(igraph, cc):
    ograph = nx.DiGraph()
    
    cc_nodes = dict()
    for edge in igraph.edges:
        src = edge[0]
        dst = edge[1]
        if igraph.nodes[src].get("cc") == cc or igraph.nodes.get("cc") == cc:
            ograph.add_node(src, **igraph.nodes[src])
            ograph.add_node(dst, **igraph.nodes[dst])
            ograph.add_edge(src, dst, **igraph.edges[src, dst])

    return ograph
        
def extract_cc_graphs(igraph, cc_graph_dir):
    print("\nExtracting country code graphs ...")
    print(". Building country code map ...")
    cc_map = extract_cc_map(igraph)

    print(". Building country code graphs ...")
    for cc in sorted(cc_map.keys()):
        # if cc is None or len(cc) == 0:
        #     print("  . TODO : None/Empty CC")
        #     continue
        filename = "{}/{}.gml".format(cc_graph_dir, "??" if ((cc is None) or (len(cc) == 0)) else cc)
        if os.path.isfile(filename):
            print("  . " + cc + " is already built. Skipping.")
        else:
            cc_graph = extract_cc_graph(igraph, cc)
            print("  . {} - {} : {} nodes, {} edges".format(cc, filename, len(cc_graph.nodes), len(cc_graph.edges)))
            nx.write_gml(cc_graph, filename)

def load_internet_graph(filename, ig):
    if ig is not None:
        return ig
    if not os.path.isfile(filename):
        print("Internet graph file doesn't exist! Exiting.")
        sys.exit()

    print("Loading internet graph in " + filename + " ...") 
    return nx.read_gml(filename)

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: " + sys.argv[0] + " <graph.gml>")
        sys.exit()

    if not sys.argv[1].endswith(".gml"):
        print("Error: Input file must have .json extension!")
        sys.exit()

    igraph_filename = sys.argv[1]
    igraph = None
    
    subdir = ".".join(igraph_filename.split('.')[:-1])
    if not os.path.isdir(subdir):
        print("Creating subfolder : " + subdir + " ...")
        os.mkdir(subdir)

    as_graph_filename = subdir + "/as.gml"
    if os.path.isfile(as_graph_filename):
        print("AS graph already extracted, loading from file ...")
        as_graph = nx.read_gml(as_graph_filename)
    else:
        igraph = load_internet_graph(igraph_filename, igraph)
        as_graph = extract_AS_graph(igraph)
        print(". Saving result in {} ...".format(as_graph_filename))
        nx.write_gml(as_graph, as_graph_filename)
        print("{} nodes, {} edges.".format(len(as_graph.nodes), len(as_graph.edges)))

    as_cc_graph_dir = subdir + "/cc"
    if not os.path.isdir(as_cc_graph_dir):
        os.mkdir(as_cc_graph_dir)
    extract_cc_graphs(as_graph, as_cc_graph_dir)


