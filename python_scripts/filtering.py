import os
import pickle as pkl
import decimal
import click
import sys
import subprocess
from decimal import Decimal
import networkx as nx
from shutil import copyfile
from scipy.spatial import ConvexHull, convex_hull_plot_2d
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
import matplotlib.pyplot as plt
import numpy as np

# ----------------------------------------------------------
import quality_measure
import source_sink_generator
import terminal_computation
import pre_extraction
import utils

# ---------------------------------------------------------


def concatenate(lists):
    """
    This concatenates all the lists contained in a list.
    :param lists: a list of lists.
    :return:
        new_list: concatenated list.
    """
    new_list = []
    for i in lists:
        new_list.extend(i)
    return new_list


def terminals_from_cont(
    Graph,
    source_flag,
    sink_flag,
    btns_factor_source,
    btns_factor_sink,
    terminal_criterion="branch_convex_hull+btns_centr",
):
    """
    Computation of source and sink nodes. This script uses information about the inputs of the DMK solver.
    There are three criteria for the selection of the nodes.
    :param Graph: a networkx graph to be filtered.
    :param source_flag: flag used to define the source region in the continuous problem.
    :param sink_flag: flag used to define the sink region in the continuous problem.
    :param btns_factor_source: threshold for the nodes in the source region (see more in paper).
    :param btns_factor_sink: threshold for the nodes in the sink region (see more in paper).
    :param terminal_criterion: 'branch_convex_hull+btns_centr' (combination of btns centr and convex hull by branches),
    'whole_convex_hull+btns_centr' (combination of btns centr and convex hull of the source and sink regions),
    'btns_centr' (only btns centr).

    :return:
        possible_terminals_source: for each i, possible_terminals_source[i]= "sources" of i-th cc.
        possible_terminals_sink: for each i, possible_terminals_sink[i]= "sources" of i-th cc.
    """

    bn = nx.betweenness_centrality(Graph, normalized=True)

    # Defining source-sink nodes of the graph (nodes inside the source or sink of the continuous DMK)
    if source_flag == "rect_cnst":
        nodes_in_source = [
            node
            for node in Graph.nodes()
            if source_sink_generator.source_rect_cnst_test(
                Graph.nodes[node]["pos"][0], Graph.nodes[node]["pos"][1]
            )
        ]
    else:
        nodes_in_source = [
            node
            for node in Graph.nodes()
            if fsource(
                Graph.nodes[node]["pos"][0], Graph.nodes[node]["pos"][1], source_flag
            )
            != 0
        ]
    if sink_flag == "rect_cnst":
        nodes_in_sink = [
            node
            for node in Graph.nodes()
            if source_sink_generator.sink_rect_cnst_test(
                Graph.nodes[node]["pos"][0], Graph.nodes[node]["pos"][1]
            )
        ]
    else:
        nodes_in_sink = [
            node
            for node in Graph.nodes()
            if fsink(
                Graph.nodes[node]["pos"][0], Graph.nodes[node]["pos"][1], sink_flag
            )
            != 0
        ]

    # min bn inside the source and sink

    max_bn_source = max([bn[node] for node in nodes_in_source])
    max_bn_sink = max([bn[node] for node in nodes_in_sink])

    # Defining source-sink candidates based only on btns

    kind_of_leaf_nodes_source = [
        key for key in nodes_in_source if bn[key] <= btns_factor_source * max_bn_source
    ]  # *(min_bn_source)+.0001]
    kind_of_leaf_nodes_sink = [
        key for key in nodes_in_sink if bn[key] <= btns_factor_sink * max_bn_sink
    ]  # *(min_bn_sink+.0001)]

    # Defining the subgraphs induced by the candidates

    sub_source = Graph.subgraph(kind_of_leaf_nodes_source)
    sub_sink = Graph.subgraph(kind_of_leaf_nodes_sink)

    # Removing repeated labels

    possible_terminals_source = set(kind_of_leaf_nodes_source)
    possible_terminals_sink = set(kind_of_leaf_nodes_sink)

    if terminal_criterion != "btns_centr":
        # Getting the coordinates to compute convex hulls

        coordinates_in_source = np.asarray(
            [
                [Graph.nodes[node]["pos"][0], Graph.nodes[node]["pos"][1]]
                for node in nodes_in_source
            ]
        )
        coordinates_in_source_list = concatenate(list(coordinates_in_source))

        coordinates_in_sink = np.asarray(
            [
                [Graph.nodes[node]["pos"][0], Graph.nodes[node]["pos"][1]]
                for node in nodes_in_sink
            ]
        )
        coordinates_in_sink_list = concatenate(list(coordinates_in_sink))

        # If the number of coordinates (or nodes) is not more than 3, then no convex hull computation

        if len(coordinates_in_source) >= 4 and len(coordinates_in_sink) >= 4:

            # Computing convex hull for the branches

            if terminal_criterion == "branch_convex_hull+btns_centr":
                source_hull = ConvexHull(coordinates_in_source)
                index_source_hull = np.asarray(source_hull.vertices)
                nodes_source_hull = []
                coord_source_hull = np.asarray(
                    [coordinates_in_source[node] for node in index_source_hull]
                )
                for node in nodes_in_source:
                    x, y = Graph.nodes[node]["pos"]
                    if x in coord_source_hull[:, 0] and y in coord_source_hull[:, 1]:
                        nodes_source_hull.append(node)

                sink_hull = ConvexHull(coordinates_in_sink)
                index_sink_hull = np.asarray(sink_hull.vertices)
                nodes_sink_hull = []
                coord_sink_hull = np.asarray(
                    [coordinates_in_sink[node] for node in index_sink_hull]
                )
                for node in nodes_in_sink:
                    x, y = Graph.nodes[node]["pos"]
                    if x in coord_sink_hull[:, 0] and y in coord_sink_hull[:, 1]:
                        nodes_sink_hull.append(node)
                possible_terminals_source = set(
                    kind_of_leaf_nodes_source + nodes_source_hull
                )
                possible_terminals_sink = set(kind_of_leaf_nodes_sink + nodes_sink_hull)

            # Computing convex hull for all the nodes defined as candidates

            elif terminal_criterion == "whole_convex_hull+btns_centr":  # not working!
                single_source_hull = ConvexHull(coordinates_in_source_list)
                single_index_source_hull = np.asarray(single_source_hull.vertices)
                nodes_source_hull = []
                single_coord_source_hull = np.asarray(
                    [
                        coordinates_in_source_list[node]
                        for node in single_index_source_hull
                    ]
                )
                for node in nodes_in_source:
                    x, y = Graph.nodes[node]["pos"]
                    if (
                        x in single_coord_source_hull[:, 0]
                        and y in single_coord_source_hull[:, 1]
                    ):
                        nodes_source_hull.append(node)
                single_sink_hull = ConvexHull(coordinates_in_sink_list)
                single_index_sink_hull = np.asarray(single_sink_hull.vertices)
                nodes_sink_hull = []
                single_coord_sink_hull = np.asarray(
                    [coordinates_in_sink_list[node] for node in single_index_sink_hull]
                )
                for node in nodes_in_sink:
                    x, y = Graph.nodes[node]["pos"]
                    if (
                        x in single_coord_sink_hull[:, 0]
                        and y in single_coord_sink_hull[:, 1]
                    ):
                        nodes_sink_hull.append(node)
                possible_terminals_source = set(
                    kind_of_leaf_nodes_source + nodes_source_hull
                )
                possible_terminals_sink = set(kind_of_leaf_nodes_sink + nodes_sink_hull)

    return possible_terminals_source, possible_terminals_sink


def bifurcation_paths(G, terminals):
    """
    This script takes a filtered graph and reduces its paths (sequences of nodes with degree 2) to a single edge.

    :param G:  filtered graph (networkx graph).
    :param terminals: union of source and sink nodes.
    :return:
        G: reduced graph.
    """

    G = G.copy()
    N = len(G.nodes())
    deg_norm = nx.degree_centrality(G)
    deg = {}
    for key in deg_norm.keys():
        deg[key] = int(round((N - 1) * deg_norm[key]))
    # print(deg)
    # deg_neq_2=[node for node in G.nodes() if deg[node]!= 2]
    deg_3 = [
        node
        for node in G.nodes()
        if deg[node] >= 3 or deg[node] == 1 or node in terminals
    ]

    G_wo_bifuc = G.copy()
    for node in deg_3:
        G_wo_bifuc.remove_node(node)
    cc = list(nx.connected_components(G_wo_bifuc))
    # print(list(cc))
    connect_points = {}
    index = 1
    for comp in cc:
        comp = set(comp)
        neighs = {
            neigh for node in comp for neigh in G.neighbors(node) if neigh not in comp
        }
        # print(neighs)
        assert len(neighs) == 2
        G.remove_nodes_from(comp)
        G.add_edge(*tuple(neighs))

    return G


def BP_solver(folder_name, index):
    """
    This script executes the BP_solver (a muffe_sparse_opt/dmk_folder.py sequence)
    :param folder_name: folder path where the outputs will be stored. It should be written "./runs/folder_name".
    :param index: integer representing the connected component to which this algorithm is going to be applied.
    :return:
    """

    # Generating the output folders
    for folder in [
        "output",
        "output/result",
        "output/vtk",
        "output/linear_sys",
        "output/timefun",
    ]:

        try:
            os.mkdir(
                "../otp_utilities/muffe_sparse_optimization/simplifications/"
                + folder_name
                + "/component"
                + str(index)
                + "/"
            )
        except OSError:
            print(
                "Creation of the directory %s failed."
                % (folder_name + "/component" + str(index) + "/")
            )

        try:
            os.mkdir(
                "../otp_utilities/muffe_sparse_optimization/simplifications/"
                + folder_name
                + "/component"
                + str(index)
                + "/"
                + folder
            )
        except OSError:
            print(
                "Creation of the directory %s failed."
                % (folder_name + "/component" + str(index) + "/" + folder)
            )
    os.system(
        "cp ../otp_utilities/muffe_sparse_optimization/simplifications/muffa.fnames  "
        + "../otp_utilities/muffe_sparse_optimization/simplifications/"
        + folder_name
        + "/component"
        + str(index)
        + "/"
    )

    # Copying the par_files
    for file in ["decay", "pflux", "pmass"]:
        os.system(
            "cp  ../otp_utilities/muffe_sparse_optimization/simplifications/par_files/"
            + file
            + ".dat "
            + "../otp_utilities/muffe_sparse_optimization/simplifications/"
            + folder_name
            + "/component"
            + str(index)
            + "/input"
        )

    # Executing the dmk_folder.py run
    continuous_path = os.path.abspath("./")
    discrete_path = "../otp_utilities/muffe_sparse_optimization/simplifications/"

    os.chdir(discrete_path)
    command = (
        "./dmk_folder.py run  "
        + folder_name[2:]
        + "/component"
        + str(index)
        + "  "
        + "muffa.ctrl "
    )  # "> outputs_dmk_d.txt"

    print(command)
    os.system(command)
    os.chdir(continuous_path)


def filtering_from_image(
    small_G_filtered,
    beta_d,
    terminals,
    color_dict,
    partition_dict,
    weighting_method_simplification,
    entry=None,
    folder_name=None,
):
    """
    This takes as input a pre-extracted graph (obtained from an image) and filters it using filtering().
    :param small_G_filtered: pre-extracted graph.
    :param beta_d: beta input for the DMK solver.
    :param terminals: union of source and sink nodes.
    :param color_dict: dictionary s.t., color_dict[key]= real value for the key-th pixel.
        key is the index for the pixels in the resized image.
    :param partition_dict: dictionary, s.t., part_dict[key]=[(x1,y1),...,(x4,y4)].
    :param weighting_method_simplification: 'ER', 'IBP', 'BPW'.
    :param entry: node index. terminals[entry] is the unique source node.
    :param folder_name: folder path where the outputs will be stored. It should be written "./runs/folder_name".
    :return:
        G_final_simplification: filtered graph (networkx graph).
    """

    Graph = small_G_filtered.copy()
    graph_type = 1
    BP_weights = "BPtdens"
    min_ = 0.0001
    terminal_info = [terminals, entry]
    weight_flag = None
    input_flag = "image"

    print(folder_name)
    folder_name = "./runs/" + folder_name.split("/")[-1]
    print(folder_name)
    try:
        print("Creating folder", folder_name.split("/")[-1])
        os.mkdir(
            "../otp_utilities/muffe_sparse_optimization/simplifications/runs/"
            + folder_name.split("/")[-1]
        )
    except:
        pass

    (
        G_final_simplification,
        newGraph,
        ncc,
        possible_terminals_source,
        possible_terminals_sink,
        mapping,
    ) = filtering(
        Graph,
        folder_name + "/",
        beta_d,
        graph_type,
        weighting_method_simplification,
        weight_flag,
        min_,
        BP_weights,
        terminal_info,
        input_flag,
    )

    # Plotting
    ## Filtering on image

    fig, ax = plt.subplots(1, 1, figsize=(15, 15))
    patches = []
    for key in partition_dict:
        square_edges = np.asarray(
            [partition_dict[key][0]]
            + [partition_dict[key][2]]
            + [partition_dict[key][3]]
            + [partition_dict[key][1]]
            + [partition_dict[key][0]]
        )
        s1 = Polygon(square_edges)
        patches.append(s1)
    p = PatchCollection(patches, alpha=0.9, cmap="Wistia", linewidth=0.0, edgecolor="b")

    colors = np.array(list(color_dict.values()))
    p.set_array(colors)
    ax.add_collection(p)

    plt.savefig(folder_name + "/image", transparent=False)

    fig, ax = plt.subplots(1, 1, figsize=(15, 15))
    patches = []
    for key in partition_dict:
        square_edges = np.asarray(
            [partition_dict[key][0]]
            + [partition_dict[key][2]]
            + [partition_dict[key][3]]
            + [partition_dict[key][1]]
            + [partition_dict[key][0]]
        )
        # print(square_edges)
        # print(len(square_edges))
        s1 = Polygon(square_edges)
        patches.append(s1)
    p = PatchCollection(patches, alpha=0.9, cmap="Wistia", linewidth=0.1, edgecolor="b")

    colors = np.array(list(color_dict.values()))
    p.set_array(colors)
    ax.add_collection(p)

    # plt.savefig('./component1/image', transparent=False)

    pos = nx.get_node_attributes(small_G_filtered, "pos")
    nx.draw_networkx(
        small_G_filtered,
        pos,
        node_size=5,
        width=2,
        with_labels=False,
        edge_color="gray",
        alpha=0.5,
        node_color="black",
        ax=ax,
    )

    pos = nx.get_node_attributes(G_final_simplification, "pos")
    nx.draw_networkx(
        G_final_simplification,
        pos,
        node_size=5,
        width=3,
        with_labels=False,
        edge_color="black",
        alpha=1,
        node_color="black",
        ax=ax,
    )

    for node in terminals:
        if node in [terminals[entry]]:
            color = "green"
        else:
            color = "red"
        x = small_G_filtered.nodes[node]["pos"][0]
        y = small_G_filtered.nodes[node]["pos"][1]
        circle1 = plt.Circle((x, y), 0.015, color=color, fill=False, lw=4)
        ax.add_artist(circle1)

    plt.savefig(folder_name + "/simpl_graph+image", transparent=False)

    ## Filtering with highlighted terminals

    fig, ax = plt.subplots(1, 1, figsize=(15, 15))

    pos = nx.get_node_attributes(G_final_simplification, "pos")
    nx.draw_networkx(
        G_final_simplification,
        pos,
        node_size=5,
        width=3,
        with_labels=False,
        edge_color="black",
        alpha=1,
        node_color="black",
        ax=ax,
    )

    plt.savefig(folder_name + "/simpl_graph", transparent=False)

    fig, ax = plt.subplots(1, 1, figsize=(15, 15))

    pos = nx.get_node_attributes(G_final_simplification, "pos")
    nx.draw_networkx(
        G_final_simplification,
        pos,
        node_size=5,
        width=3,
        with_labels=False,
        edge_color="black",
        alpha=1,
        node_color="black",
        ax=ax,
    )

    for node in terminals:
        if node in [terminals[entry]]:
            color = "green"
        else:
            color = "red"
        x = small_G_filtered.nodes[node]["pos"][0]
        y = small_G_filtered.nodes[node]["pos"][1]
        circle1 = plt.Circle((x, y), 0.015, color=color, fill=False, lw=4)
        ax.add_artist(circle1)

    plt.savefig(folder_name + "/simpl_graph+terminals", transparent=False)

    with open(folder_name + "/simplified_graph.dat", "wb") as file:
        pkl.dump(G_final_simplification, file)

    return G_final_simplification


def img_pre_extr2filtering(
    image_path, filter_size, weighting_method_simplification, beta_d
):
    """
    This takes as input a path containing the bfs approximation of the pre-extracted graph. This pre-extracted graph has
     been obtained from an image. The output is the filtered graph.
    :param image_path: string.
    :param filter_size: radious of the filters for the terminal selection process.
    :param weighting_method_simplification: 'ER', 'IBP', 'BPW'.
    :param beta_d: beta input for the DMK solver.
    :return:
        G_final_simplification: filtered graph (networkx graph).
    """

    last_word = image_path.split("/")[-1]
    new_folder_name = last_word.split(".")[0]
    saving_path = "./runs/" + new_folder_name

    file = "/bfs_extracted_graph.pkl"

    with open(saving_path + file, "rb") as file:
        Graph = pkl.load(file)

    file = "/real_image.pkl"

    with open(saving_path + file, "rb") as file:
        color_dict = pkl.load(file)

    file = "/real_part_dict.pkl"

    with open(saving_path + file, "rb") as file:
        partition_dict = pkl.load(file)

    (
        nbr_graph,
        color_nbr,
        terminal_list,
        nodes_for_correction,
        filter_number,
    ) = terminal_computation.terminal_finder(filter_size, partition_dict, Graph)
    l = []
    for value in nodes_for_correction.values():
        l += value

    fig, ax = plt.subplots(1, 1, figsize=(15, 15))

    partition_dict_mask, _, _ = quality_measure.partition_set(filter_number + 1)
    patches = []
    for key in partition_dict_mask:
        square_edges = np.asarray(
            [partition_dict_mask[key][0]]
            + [partition_dict_mask[key][2]]
            + [partition_dict_mask[key][3]]
            + [partition_dict_mask[key][1]]
            + [partition_dict_mask[key][0]]
        )
        # print(square_edges)
        # print(len(square_edges))
        s1 = Polygon(square_edges)
        patches.append(s1)
    p = PatchCollection(
        patches, alpha=0.5, linewidth=1, edgecolor="b", facecolor="white"
    )
    ax.add_collection(p)

    patches2 = []
    for key in partition_dict:
        square_edges = np.asarray(
            [partition_dict[key][0]]
            + [partition_dict[key][2]]
            + [partition_dict[key][3]]
            + [partition_dict[key][1]]
            + [partition_dict[key][0]]
        )
        # print(square_edges)
        # print(len(square_edges))
        s1 = Polygon(square_edges)
        patches2.append(s1)
    p2 = PatchCollection(
        patches2, alpha=0.4, cmap="YlOrRd", linewidth=0.1, edgecolor="b"
    )

    colors = np.array(list(color_dict.values()))
    p2.set_array(colors)
    ax.add_collection(p2)

    pos = nx.get_node_attributes(nbr_graph, "pos")
    nx.draw_networkx(
        nbr_graph,
        pos,
        node_size=15,
        width=1.5,
        with_labels=False,
        edge_color="red",
        alpha=1,
        node_color=color_nbr,
        ax=ax,
    )

    pos = nx.get_node_attributes(Graph, "pos")
    nx.draw_networkx(
        Graph,
        pos,
        node_size=0,
        width=1.5,
        with_labels=False,
        edge_color="black",
        alpha=0.5,
        ax=ax,
    )

    for i in range(len(terminal_list)):
        node = terminal_list[i]
        # color=color_nbr[i]
        if node in l:
            color = "green"
            size = 1
        else:
            color = "black"
            size = 0.5
        x = Graph.nodes[node]["pos"][0]
        y = Graph.nodes[node]["pos"][1]
        circle1 = plt.Circle((x, y), 0.01, color=color, fill=False, lw=size)
        ax.add_artist(circle1)
        # label = ax.annotate(str(node), xy=(x, y), fontsize=12, ha="center")

    plt.savefig(saving_path + "/terminal_map.png")

    for node in [terminal_list[0]]:
        entry = terminal_list.index(node)
        G_final_simplification = filtering_from_image(
            Graph,
            beta_d,
            terminal_list,
            color_dict,
            partition_dict,
            weighting_method_simplification,
            entry,
            saving_path,
        )
    return G_final_simplification


def filtering(
    Graph,
    folder_name,
    beta_d,
    graph_type,
    weighting_method_simplification,
    weight_flag,
    min_,
    BP_weights,
    terminal_info,
    input_flag=None,
):
    """

    :param Graph: a networkx graph to be filtered.
    :param folder_name: folder path where the outputs will be stored. It should be written "./runs/folder_name".
    :param beta_d: beta input for the DMK solver.
    :param graph_type: 1 (to use edges and vertices of the grid), 2 (to use only edges), 3 (to use elements of the grid)
    :param weighting_method_simplification: 'ER', 'IBP', 'BPW'.
    :param weight_flag: 'length', to use the length of the edges; else, to use unit length edges.
    :param min_: threshold for the weights of the edges after filtering.
    :param BP_weights: 'BPtdens' to use optimal transport density as weights for edges, 'BPflux' to use optimal flux.
    :param terminal_info: for dat files (i.e. from continuous): [
            source_flag,
              sink_flag,
              btns_factor_source,
                btns_factor_sink].
                for images:
    terminal_info = [
            terminals,
            entry]
    :param input_flag: 'image' or None (for dat files)
    :return:
        G_final_simplification: filtered graph (networkx graph).
        newGraph: dictionary, s.t., newGraph[i]= i-th cc (labeled from 0 to len(cc)-1).
        ncc: number of connected components of Graph.
        possible_terminals_source: for each i, possible_terminals_source[i]= "sources" of i-th cc.
        possible_terminals_sink: for each i, possible_terminals_sink[i]= "sources" of i-th cc.
        mapping: for each i, mapping[i]: labels of i-th cc -------------> labels of Graph.
    """
    # ------------------------------------------------ filtering -------------------------------------------
    # Init dicts
    if len(terminal_info) == 2:  # this is for image processing
        terminals = terminal_info[0]
        entry = terminal_info[1]
    elif len(terminal_info) == 4:
        source_flag = terminal_info[0]
        sink_flag = terminal_info[1]
        btns_factor_source = terminal_info[2]
        btns_factor_sink = terminal_info[3]
    else:
        print("invalid terminal_info input!")

    newGraph = {}
    mapping = {}
    inv_mapping = {}
    possible_terminals_source = {}
    possible_terminals_sink = {}
    edge_mapping = {}
    G_simplification = {}

    # defining the beta_d for the simulations

    utils.updating_beta_discrete(beta_d)

    # Generating the cc-based graphs and the corresponding mappings
    (
        newGraphList,
        mappingList,
        inv_mappingList,
        [components_list],
    ) = utils.pickle2pygraph(Graph, graph_type)

    # Iterating over the subgraphs
    ncc = len(newGraphList)
    for i in range(1, ncc + 1):
        newGraph[i] = newGraphList[i - 1]
        mapping[i] = mappingList[i - 1]
        inv_mapping[i] = inv_mappingList[i - 1]
        # ------------------------------------  filtering: this is done in a different way for images -----------------
        if len(terminal_info) == 2:
            possible_terminals_source[i] = [
                inv_mapping[i][node] for node in [terminals[entry]]
            ]
            possible_terminals_sink[i] = [
                inv_mapping[i][node]
                for node in terminals
                if node not in [terminals[entry]]
            ]

        else:

            (
                possible_terminals_source[i],
                possible_terminals_sink[i],
            ) = terminals_from_cont(
                newGraph[i],
                source_flag,
                sink_flag,
                btns_factor_source,
                btns_factor_sink,
            )

        edge_mapping[i] = utils.pygraph2dat(
            newGraph[i],
            possible_terminals_source[i],
            possible_terminals_sink[i],
            i,
            folder_name,
            mapping[i],
            input_flag,
        )

        print("executing graph2incidence_matrix for the component %s" % i)
        utils.using_graph2incidence_matrix(folder_name, i, weight_flag)
        print(
            "_____________________________EXECUTING BP solver___________________________________________"
        )
        BP_solver(folder_name, i)
        data_folder_name = folder_name + "/component" + str(i)
        G_simplification[i] = utils.dat2pygraph(
            newGraph[i], data_folder_name, edge_mapping[i], min_, BP_weights
        )

        # Defining terminal labels for sources and sinks

        for node in G_simplification[i].nodes():
            node_in_original, _ = quality_measure.old_label(
                node, newGraph[i], G_simplification[i]
            )
            if node_in_original in possible_terminals_source[i]:
                ss_label = 1
            elif node_in_original in possible_terminals_sink[i]:
                ss_label = -1
            else:
                ss_label = 0
            G_simplification[i].node[node]["terminal"] = ss_label

    # Assigning opt_pot to the nodes

    # Joining all the simplifications into a single graph

    # G = newGraphList[0]
    G_final_simplification = G_simplification[1]
    for i in range(1, ncc):
        # G = nx.disjoint_union(G, newGraphList[i])
        G_final_simplification = nx.disjoint_union(
            G_final_simplification, G_simplification[i + 1]
        )

    # Adding the terminals (to track disconnectivities) (to do this we need to comment the nex line. But it's not working yet)

    G_final_simplification.remove_nodes_from(
        [
            x
            for x in G_final_simplification.nodes()
            if G_final_simplification.degree(x) == 0
        ]
    )

    # Reweighting the edges

    deg = nx.degree_centrality(G_final_simplification)
    posGsimpl = nx.get_node_attributes(G_final_simplification, "pos")
    if weighting_method_simplification == "ER":
        N = len(G_final_simplification.nodes())
        for edge in G_final_simplification.edges():
            if deg[edge[0]] * deg[edge[1]] != 0:
                G_final_simplification.edges[(edge[0], edge[1])][
                    "weight"
                ] = G_final_simplification.nodes[edge[0]]["weight"] / (
                    deg[edge[0]] * (N - 1)
                ) + G_final_simplification.nodes[
                    edge[1]
                ][
                    "weight"
                ] / (
                    deg[edge[1]] * (N - 1)
                )
    elif weighting_method_simplification == "IBP":
        print("relabel/reweig!")
        G_final_simplification_relabeled = relabeling(G_final_simplification, Graph)
        G_final_simplification = reweighting(G_final_simplification_relabeled, Graph)
        posGsimpl = nx.get_node_attributes(G_final_simplification, "pos")
    elif weighting_method_simplification == "BPW":
        pass

    return (
        G_final_simplification,
        newGraph,
        ncc,
        possible_terminals_source,
        possible_terminals_sink,
        mapping,
    )

    # ------------ end of filtering -----------------------------------------


def img2filtering(
    image_path, new_size, number_of_colors, t1, t2, number_of_cc, graph_type, beta_d
):
    """
    This takes as input an image and outputs the filtered graph.
    :param image_path: string.
    :param number_of_colors: number of colors for the output image.
    :param t1: noise threshold. If t=0, then all the new pixels are preserved with their new colors.
    :param t2: threshold for the weights of the edges after pre-extraction.
    :param number_of_cc: number of connected components of the graph represented by the image. If None, then only 1
    cc is assumed.
    :param graph_type: 1 (to use edges and vertices of the grid), 2 (to use only edges).
    :param beta_d: beta input for the DMK solver.
    :return:
        G_final_simplification: filtered graph (networkx graph).
    """

    # reading the image, doing pre extraction, getting bfs approx
    pre_extraction.bfs_preprocess(
        image_path, new_size, number_of_colors, t1, t2, number_of_cc, graph_type
    )
    # filtering the bfs graph
    G_final_simplification = img_pre_extr2filtering(
        image_path, filter_size, weighting_method_simplification, beta_d
    )

    return G_final_simplification


# -------------------------test1------------------------------------------------------

filter_size = 0.045
image_path = "./runs/graph_from_image/image.jpg"
weighting_method_simplification = "ER"
beta_d = 1.0

# img_pre_extr2filtering(image_path, filter_size, weighting_method_simplification, beta_d)

# --------------------------test2----------------------------------------------------

new_size = 100
ratio = new_size / 1200
# print('ratio:',ratio)
t1 = 0.09
t2 = 0.12
image_path = "./runs/graph_from_image/image.jpg"
number_of_cc = 1
number_of_colors = 50
graph_type = "1"

# img2filtering(image_path, new_size, number_of_colors, t1, t2, number_of_cc, graph_type, beta_d)