#!/usr/bin/env python

import sys
import os

import semanticnet as sn
import networkx as nx

def calculate_degree_map(igraph):
    degree_map = dict()
    edges = igraph.get_edges()
    for eid in edges.keys():
        src = edges[eid]["src"]
        dst = edges[eid]["dst"]

        if src not in degree_map:
            degree_map[src] = { "in" : 0, "out" : 0  }
        if dst not in degree_map:
            degree_map[dst] = { "in" : 0, "out" : 0 }

        degree_map[src]["out"] += 1
        degree_map[dst]["in"] += 1

    return degree_map

def build_label_map(igraph):
    label_map = dict()
    nodes = igraph.get_nodes()
    for nid in nodes.keys():
        if "label" not in nodes[nid]:
            print("Error: " + nid.hex + " doesn't have a label! Skipping.")
            continue
        label = nodes[nid]["label"]
        if label in label_map:
            print("Error: Label '" + label + "' has duplicates! Something is very wrong... Skipping anyway.")
            continue
        label_map[label] = nid

    return label_map

def extract_SPNs_from_AS_list(as_graph, asn_list, pn_check=True):
    print("Extracting Sibling Peripheral Nodes from AS list ...")

    print(". Calculating degree map ...")
    degree_map = calculate_degree_map(as_graph)

    print(". Building label map ...")
    label_map = build_label_map(as_graph)

    print(". Converting to NetworkX graph ...")
    as_nx_graph = as_graph.networkx_graph()

    print(". Creating subgraph ...")
    ograph = sn.DiGraph()
    
    as_nodes = as_graph.get_nodes()
    onode_map = dict()
    oedge_map = dict()

    input_queue = []
    successor_queue = []
    for asn in asn_list:

        if asn not in label_map:
            print("  . Warning: AS '" + asn + "' couldn't be found in AS graph! Skipping.")
            continue
        nid = label_map[asn]
        if nid not in degree_map:
            print("  . Error: AS '" + asn + "' couldn't be found in degree map! Skipping.")
            continue
        if pn_check:
            if not(degree_map[nid]["in"] == 0 and degree_map[nid]["out"] >= 1):
                print("  . Warning: AS '" + asn + "' is not a peripheral node! Skipping.")
                continue

        # NOTE : Add AS to sub graph (If necessary)
        if asn not in onode_map:
            onode_map[asn] = ograph.add_node(as_nodes[nid])
            ograph.set_node_attribute(onode_map[asn], "type", "AS (Input)")
            ograph.set_node_attribute(onode_map[asn], "depth", 0)
            input_queue.append({"nid" : nid, "asn" : asn})

    print("  . " + str(len(input_queue)) + " input nodes found.")

    for item in input_queue:
        
        nid = item["nid"]
        asn = item["asn"]

        successors = as_nx_graph.successors(nid)
        for succ_id in successors:

            # NOTE : Add successor
            succ_label = as_nodes[succ_id]["label"]
            if succ_label not in onode_map:
                onode_map[succ_label] = ograph.add_node(as_nodes[succ_id])
                ograph.set_node_attribute(onode_map[succ_label], "type", "AS (Parent)")

            edge1_key = asn + "->" + succ_label
            if edge1_key not in oedge_map:
                oedge_map[edge1_key] = ograph.add_edge(onode_map[asn], onode_map[succ_label])
                # TODO : Conserve edge attributes, right now everything is lost.
                ograph.set_edge_attribute(oedge_map[edge1_key], "type", "AS->AS (1)")

            successor_queue.append({ "nid" : succ_id, "asn" : succ_label })     
       

    print("  . " + str(len(successor_queue)) + " parents found.")

    p_count = 0
    for item in successor_queue:

        nid = item["nid"]
        asn = item["asn"]

        # NOTE : Get successor's predecessors
        predecessors = as_nx_graph.predecessors(nid)
        for pred_id in predecessors:

            if pn_check:
                if not(degree_map[pred_id]["in"] == 0 and degree_map[pred_id]["out"] >= 1):
                    continue

            pred_label = as_nodes[pred_id]["label"]
            if pred_label not in onode_map:
                onode_map[pred_label] = ograph.add_node(as_nodes[pred_id])
                ograph.set_node_attribute(onode_map[pred_label], "type", "AS (Sibling)")
                p_count += 1
                    
            edge2_key = pred_label + "->" + asn
            if edge2_key not in oedge_map:
                oedge_map[edge2_key] = ograph.add_edge(onode_map[pred_label], onode_map[asn])
                ograph.set_edge_attribute(oedge_map[edge2_key], "type", "AS->AS (2)")

    print("  . " + str(p_count) + " peripheral siblings found.")

    return ograph
    
if __name__ == "__main__":
        
        if len(sys.argv) != 4:
            print("Usage: " + sys.argv[0] + " <as_list_file> <path/to/as.json> <output_dir>") 
            sys.exit(0)

        as_list_filename = sys.argv[1]
        as_graph_filename = sys.argv[2]
        spn_graph_dir = sys.argv[3]
        spn_graph_filename = spn_graph_dir + "/full.json"
        
        print("Loading ASN list in " + as_list_filename + " ...")
        with open(as_list_filename, "rU") as as_list_file:
            as_list = as_list_file.read().splitlines()

        if not as_graph_filename.split("/")[-1] == "as.json":
            print("Error: Filename doesn't point to an AS graph!")
            sys.exit(0)

        print("Loading AS graph in " + as_graph_filename + " ...")
        as_graph = sn.DiGraph()
        as_graph.load_json(as_graph_filename)

        if not os.path.isdir(spn_graph_dir):
            print("Creating folder " + spn_graph_dir + " ...")
            os.mkdir(spn_graph_dir)

        spn_graph = extract_SPNs_from_AS_list(as_graph, as_list)
        print("Saving result in " + spn_graph_filename + " ...")
        spn_graph.save_json(spn_graph_filename)

        print("Splitting components into separate files ...")
        print("  . Converting result to NetworkX ...")
        nx_spn_graph = spn_graph.networkx_graph()
        print("  . Calculating components ...")
        wcc = nx.weakly_connected_components(nx_spn_graph)
        print("  . Writing to files ...")
        c = 0
        nodes = spn_graph.get_nodes()
        for component in wcc:
            with open(spn_graph_dir + "/wcc-" + str(c) + ".txt", "w") as outfile: 
                for nid in component:
                   outfile.write(nodes[nid]["label"] + "\n")
            c += 1
        print("    . " + str(c) + " components written.")

        
        
        
        
        
        
