import matplotlib.pyplot as plt
import pandas as pd
import collections
import csv
import numpy as np
from scipy import stats

from pype_schema.parse_json import JSONParser
from pype_schema.visualize import draw_graph
from pype_schema.tag import Tag, VirtualTag
from pype_schema.node import Pump
from pype_schema.tag import TagType

taglist_path = "data/SBData/TagList.xlsx"


def create_vtag_from_node(
    network,
    node,
    direction,
    contents_type=None,
    visited=[],
    recurse=True,
    exclude=[],
    subtract=[],
    parent_id=None,
):
    """Creates a virtual tag to recursively aggregate everything coming in/out of `node`

    Parameters
    ----------
    network: pype_schema.network.Network

    node : pype_schema.node.Node

    contents : pype_schema.utils.ContentsType

    direction : ["in", "out", "net"]

    visited : list of pype_schema.node.Node
        list of nodes already visited

    exclude: list
        list of tag id strings to exclude from the virtual tag

    subtract: list
        list of tag id strings to subtract from the virtual tag (instead of adding)

    parent_id: str, None
        Optional parent_id for the virtual tag (if `None`, is set to 'ParentNetwork')
        This is the id of the object the virtual tag is associated with

    Returns
    -------
    pype_schema.tag.VirtualTag or pype_schema.tag.Tag
    """
    visited.append(node)
    if direction == "net":
        if (
            node.input_contents != node.output_contents
            or len(node.input_contents) > 1
            and contents_type is None
        ):
            raise ValueError(
                """
                    There are multiple input or output contents and/or they do not match AND `contents_type`
                    is not specified, please specify a contents type
                """
            )
        else:
            contents_type = node.input_contents[0]
        tag_type = "NetFlow"
        inflow = create_vtag_from_node(
            network, node, contents=contents_type, direction="in", visited=visited
        )
        outflow = create_vtag_from_node(
            network, node, contents=contents_type, direction="out", visited=visited
        )
        return VirtualTag(
            "_".join([node.id, contents_type, "NetFlow"]),
            [inflow, outflow],
            operations="lambda tag1,tag2: tag1-tag2",
            units=inflow.units,
            parent_id=node.id,
            contents=node.input_contents[0],
        )
    elif direction == "in":
        if len(node.input_contents) > 1 and contents_type is None:
            raise ValueError(
                """
                    There are multiple input contents and `contents_type`
                    is not specified, please specify a `contents_type`
                """
            )
        else:
            contents_type = node.input_contents[0]
        tag_type = "InFlow"
        conns = network.get_all_connections_to(node)
    elif direction == "out":
        if len(node.output_contents) > 1 and contents_type is None:
            raise ValueError(
                """
                    There are multiple output contents and `contents_type`
                    is not specified, please specify a `contents_type`
                """
            )
        else:
            contents_type = node.output_contents[0]
        tag_type = "OutFlow"
        conns = network.get_all_connections_from(node)
    else:
        raise ValueError("Invalid direction " + direction)
    tags, variables, operations = [], "", ""
    if contents_type:
        conns = [conn for conn in conns if conn.contents == contents_type]
    for conn in conns:
        if recurse and not conn.tags:
            if conn.contents == contents_type:
                if direction == "in":
                    new_node = conn.source
                elif direction == "out":
                    new_node = conn.destination
                if new_node not in visited:
                    tag = create_vtag_from_node(
                        network,
                        new_node,
                        contents_type=contents_type,
                        direction=direction,
                        visited=visited,
                    )
                    visited.append(new_node)
                    tags.append(tag)
        else:
            vtags = [tag for tag in conn.tags.values() if isinstance(tag, VirtualTag)]
            if vtags:
                if len(vtags) > 1:
                    raise ValueError(
                        "There is more than one virtual tag for connection object "
                        + conn.id
                    )
                else:
                    for tag in vtags:
                        if tag not in exclude:
                            tags.append(tag)
                            variables += f"tag{len(tags)}" + ","
                            operations += (
                                f"-tag{len(tags)}"
                                if tag in subtract
                                else f"+tag{len(tags)}"
                            )
            else:
                for tag in conn.tags.values():
                    if (
                        tag.source_unit_id == "total"
                        and tag.dest_unit_id == "total"
                        and tag not in exclude
                    ):
                        tags.append(tag)
                        variables += f"tag{len(tags)}" + ","
                        operations += (
                            f"-tag{len(tags)}"
                            if tag in subtract
                            else f"+tag{len(tags)}"
                        )
    variables, operations = variables.strip()[:-1], operations.strip()
    func_ = f"lambda {variables}: {operations}"
    return VirtualTag(
        "_".join([node.id, contents_type.name, tag_type]),
        tags,
        operations=func_,
        parent_id=parent_id,
        units=tags[0].units,
        contents=contents_type,
    )


def get_tags(taglist_path, save_path=None):
    taglist = pd.read_excel(taglist_path)

    tagMap = collections.defaultdict(str)
    for i, row in taglist.iterrows():
        tagMap[row["iGreen database tag name"]] = (
            row["Tag"],
            row["Description"],
            row["Units"],
        )

    return tagMap


def convert_to_tag(tagMap, df, save_path=None):
    colmap = {c: c.replace("_Weighted Avg", "") for c in df.columns}
    colmap2 = collections.defaultdict(str)

    save_tags = []
    df = df.rename(columns=colmap)
    for c in df.columns[2:]:
        tag = tagMap[c][0]
        colmap2[c] = tag
        save_tags.append(tagMap[c])

    if save_path is not None:
        with open(save_path, "w") as csvfile:
            csvfile.write("description,tag,units,type,contents\n")
            for t in save_tags:
                csvfile.write(f"{t[0]},{t[1]},{t[2]}" + "\n")

    df = df.rename(columns=colmap2)
    return df


def remove_outliers(df, columns=[]):
    if len(columns) == 0:
        columns = df.columns
    for c in df.columns:
        if c not in columns:
            continue
        z = np.abs(stats.zscore(df[c]))
        df = df[z < 3]
    return df


def replace_zero(df, columns=[], mode="median", threshold=None):
    for c in df.columns:
        if c not in columns:
            continue
        # replace colunm with 0 to NaN
        if threshold is not None:
            df.loc[df[c] < threshold, c] = 0
        if (df[c] == 0).all() or df[c].isnull().values.all():
            # print(f'[*] column {c} all zeros!')
            continue
        if mode == "median":
            target = df[c].replace(0, np.NaN).median()
        elif mode == "mode":
            target = df[c].replace(0, np.NaN).mode()
        elif mode == "mean":
            target = df[c].replace(0, np.NaN).mean()
        elif mode == "nan":
            target = np.NaN
        else:
            print(f"[*] mode {mode} not supported!")
            return df
        if target is not np.NaN:
            df[c] = df[c].replace(0, target)

    return df


def build_network(infile, name, extend_dict={}):
    parser = JSONParser(infile)
    net = parser.initialize_network(name=name)

    for k, v in extend_dict.items():
        subnet_name = k
        subnet_file, connection_file = v
        print(subnet_name, subnet_file, connection_file)
        sub_parser = JSONParser(subnet_file)
        sub_net = sub_parser.initialize_network(name=subnet_name)
        net = parser.extend_node(
            sub_net, subnet_name, connection_file, verbose=False, inplace=True
        )
    return net


def load_data(csv_paths, columns=[]):
    flows_series = collections.defaultdict(pd.Series)  # {tag: flow_series}
    for csv_path in csv_paths:
        print(f"[*] processing {csv_path}...")
        df = pd.read_csv(csv_path)
        # df = remove_outliers(df, columns=columns)
        df = replace_zero(df, mode="median", threshold=300, columns=columns)
        for c in df.columns:
            if c in ["From date", "To date"]:
                continue
            flows_series[c] = df[c]
    return flows_series


def flow_check(net, csv_paths):
    ng_tags = [tag.id for tag in net.select_objs(tag_type=TagType.Flow, recurse=True)]
    print(f"[*] total flow tags: {len(ng_tags)}")
    print(ng_tags)

    number_of_timepoints = len(dfs[0])
    print(f"[*] number of timepoints: {number_of_timepoints}")

    # check flow consistency in connections
    connections = net.get_all_connections()
    flag = False
    for connection in connections:
        if flag:
            break
        src = connection.source
        dst = connection.destination
        src_tags = []
        dst_tags = []
        for tag in src.tags:
            if tag in ng_tags:
                src_tags.append(tag)
        for tag in dst.tags:
            if tag in ng_tags:
                dst_tags.append(tag)
        if len(src_tags) == 0 or len(dst_tags) == 0:
            continue
        in_flows = [0] * number_of_timepoints
        out_flows = [0] * number_of_timepoints

        for t in range(number_of_timepoints):
            if flag:
                break
            for tag_name in src_tags:
                if tag_name not in flows_series.keys():
                    print(f"[*] tag {tag_name} not found in flows_series")
                    continue
                in_flows[t] += flows_series[tag_name].at[t]
            for tag_name in dst_tags:
                if tag_name not in flows_series.keys():
                    print(f"[*] tag {tag_name} not found in flows_series")
                    continue
                out_flows[t] += flows_series[tag_name].at[t]
            # print(f'[*] connection {connection.id} at timepoint {t}: in_flows: {in_flows[t]}, out_flows: {out_flows[t]}')
            if in_flows[t] != out_flows[t]:
                print(f"[*] flow inconsistency in connection {connection.id} !")
                print(f"Tag: {tag}, timepoint: {t} with tags {src_tags} -> {dst_tags}")
                print(f"[*] in_flows: {in_flows[t]}, out_flows: {out_flows[t]}")
                flag = True

    # plt.plot(ng_import_timeseries, label="SB all")
    # plt.xlabel("Time")
    # plt.ylabel("ROFeedPump Intake")
    # plt.legend(loc="upper right", bbox_to_anchor=(1.45, 1.0))
    # plt.savefig("vis/ROFeedPump-plot.png", bbox_inches="tight")


def plot_by_tags(
    data_series, tags, out_dir, export_csv=True, title="", xlabel="time", ylabel=""
):
    df = pd.DataFrame()
    for tag in tags:
        df[tag] = data_series[tag]
        plt.plot(data_series[tag], label=tag, alpha=0.7)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
    if title == "":
        title = "plot"
    plt.title(title)
    plt.legend(loc="upper right", bbox_to_anchor=(1.45, 1.0))
    plt.savefig(out_dir + f"{title}_plot.png", bbox_inches="tight")
    print(f'[*] plot saved to {out_dir + f"{title}_plot.png"}')
    if export_csv:
        df.to_csv(out_dir + f"{title}_plot.csv")
        print(f'[*] csv saved to {out_dir + f"{title}_plot.csv"}')


if __name__ == "__main__":
    # dates = ["2023_01", "2023_04", "2023_05", "2023_06"]
    dates = ["2023_01"]

    tagMap = get_tags(taglist_path)

    extend_dict = {
        "MPDA": ("data/SBDesal/MPDA.json", "data/SBDesal/MPD2sb_desal.json"),
        # "MPDB": ("data/SBDesal/MPDB.json", "data/SBDesal/MPD2sb_desal.json"),
        # "MPDC": ("data/SBDesal/MPDC.json", "data/SBDesal/MPD2sb_desal.json"),
        "PostTreatment": (
            "data/SBDesal/PostTreatment.json",
            "data/SBDesal/PostTreatment2sb_desal.json",
        ),
    }

    # target_tags = ['FIT_400_001A_P.PV', 'FIT_400_002A_P.PV', 'Q_400_001A_P.PV'] # MPDA
    # target_tags = ['FIT_400_001B_P.PV', 'FIT_400_002B_P.PV', 'Q_400_001B_P.PV'] # MPDB
    # target_tags = ['FIT_400_001C_P.PV', 'FIT_400_002C_P.PV', 'Q_400_001C_P.PV'] # MPDC
    # target_tags = ['FIT_100_001_P.PV', 'FIT_900_002_P.PV', 'FIT_1000_001_P.PV'] # Top
    # target_tags = ['FIT_200_002A_P.PV', 'FIT_200_004A_P.PV', 'PT_200A_Tags.Q_Filtrate_PV'] # BW System
    # target_tags = ['FIT_200_002A_P.PV', 'FIT_200_004A_P.PV'] # BW System
    target_tags = [
        "FIT_200_001A_P.PV",
        "Q_400_002A",
        "FlowLostWithinIntermediateTanksAndFilters",
    ]  # TOP+MPD

    # net = build_network("data/SBDesal/sb_desal.json", "sb_desal", extend_dict)
    net = build_network("data/SBDesal/MPDA.json", "MPDA", {})

    for date in dates:
        data_files = [
            f"data/SBData/{date}/processed/EnergyDataMPDA.csv",
        ]
        # f"data/SBData/{date}/processed/EnergyDataMPDB,.csv",
        # f"data/SBData/{date}/processed/EnergyDataMPDC.csv",
        # f"data/SBData/{date}/processed/EnergyDataNonMPD.csv"]
        flows_series = load_data(data_files, columns=target_tags)
        plt.clf()
        plot_by_tags(
            flows_series,
            target_tags,
            "vis/",
            export_csv=True,
            title=f"{date}_FlowLostWithinIntermediateTanksAndFilters_A",
            xlabel="time",
            ylabel="flow",
        )

    # flow_check(net, data_files)
    # draw_graph(net, pyvis=False, output_file="vis/CompleteDesal.png")
