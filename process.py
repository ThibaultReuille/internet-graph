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

    print("\nExtracting core graph ...")
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

def extract_cc_map(igraph):
    cc_map = dict()
    nodes = igraph.get_nodes()
    for n in nodes.values():
        if "cc" in n:
            cc = n["cc"]
            if len(cc) == 0:
                cc = None
        else:
            cc = None
        if cc not in cc_map:
            cc_map[cc] = 0
        cc_map[cc] += 1
    return cc_map

def extract_cc_graph(igraph, cc):
    ograph = sn.Graph()
    
    nodes = igraph.get_nodes()
    edges = igraph.get_edges()

    cc_nodes = dict()
    for e in edges.values():
        src = e["src"]
        dst = e["dst"]
        if ("cc" in nodes[src] and nodes[src]["cc"] == cc) or ("cc" in nodes[dst] and nodes[dst]["cc"] == cc):
            if src not in cc_nodes:
                cc_nodes[src] = ograph.add_node(nodes[src])
            if dst not in cc_nodes:
                cc_nodes[dst] = ograph.add_node(nodes[dst])
            e1 = ograph.add_edge(cc_nodes[src], cc_nodes[dst])
            # NOTE : Copy all attributes in original edge.
            for a in [ att for att in e.keys() if att != "id" and att != "src" and att != "dst" ]:
                ograph.set_edge_attribute(e1, a, e[a])

    return ograph
        
def extract_cc_graphs(igraph, cc_graph_dir):
    print("\nExtracting country code graphs ...")
    print(". Building country code map ...")
    cc_map = extract_cc_map(igraph)

    print(". Building country code graphs ...")
    for cc in sorted(cc_map.keys()):
        if cc is None or len(cc) == 0:
            print("  . TODO : None/Empty CC")
            continue
        filename = cc_graph_dir + "/" + cc + ".json"
        if os.path.isfile(filename):
            print("  . " + cc + " is already built. Skipping.")
        else:
            cc_graph = extract_cc_graph(igraph, cc)
            print("  . " + cc + " : " + str(len(cc_graph.get_nodes())) + " nodes, " + str(len(cc_graph.get_edges())) + " edges.")
            cc_graph.save_json(filename)


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
        # NOTE : Src is a source node, it can't have an AS<->AS edge.
        ograph.set_edge_attribute(e, "type", "AS->AS")

    return ograph

def load_internet_graph(ig_filename, ig):
    if ig is not None:
        return ig
    if not os.path.isfile(ig_filename):
        print("Internet graph file doesn't exist! Exiting.")
        sys.exit()

    print("\nLoading internet graph in " + ig_filename + " ...") 
    ig = sn.Graph()
    ig.load_json(ig_filename)
    return ig

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: " + sys.argv[0] + " <graph.json>")
        sys.exit()

    if not sys.argv[1].endswith(".json"):
        print("Error: Input file must have .json extension!")
        sys.exit()

    igraph_filename = sys.argv[1]
    igraph = None
    
    subdir = igraph_filename[:-5]
    if not os.path.isdir(subdir):
        print("\nCreating subfolder : " + subdir + " ...")
        os.mkdir(subdir)

    as_graph_filename = subdir + "/as.json"
    if os.path.isfile(as_graph_filename):
        print("\nAS graph already extracted, loading from file ...")
        as_graph = sn.Graph()
        as_graph.load_json(as_graph_filename)
    else:
        igraph = load_internet_graph(igraph_filename, igraph)
        as_graph = extract_AS_graph(igraph)
        print(". Saving result in " + as_graph_filename + " ...")
        as_graph.save_json(as_graph_filename)
        print(str(len(as_graph.get_nodes())) + " nodes, " + str(len(as_graph.get_edges())) + " edges.")
 
    core_graph_filename = subdir + "/core.json"
    if os.path.isfile(core_graph_filename):
        print("\nCore graph already extracted, loading from file ...")
        core_graph = sn.Graph()
        core_graph.load_json(core_graph_filename)
    else:
        core_graph = extract_core_graph(as_graph)
        print(". Saving result in " + core_graph_filename + " ...")    
        core_graph.save_json(core_graph_filename)
        print(str(len(core_graph.get_nodes())) + " nodes, " + str(len(core_graph.get_edges())) + " edges.")
 
    as_cc_graph_dir = subdir + "/cc"
    if not os.path.isdir(as_cc_graph_dir):
        os.mkdir(as_cc_graph_dir)
    extract_cc_graphs(as_graph, as_cc_graph_dir)
    
    '''
    ss_graph_filename = subdir + "/ss.json"
    if os.path.isfile(ss_graph_filename):
        print("\nSibling sources graph already extracted, loading from file ...")
        ss_graph = sn.Graph()
        ss_graph.load_json(ss_graph_filename)
    else:
        ss_graph = extract_ss_graph(as_graph)
        print(". Saving result in " + ss_graph_filename + " ...")
        ss_graph.save_json(ss_graph_filename)
        print(str(len(ss_graph.get_nodes())) + " nodes, " + str(len(ss_graph.get_edges())) + " edges.")
    '''   

