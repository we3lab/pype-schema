import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import dates as mdates
import pandas as pd
import collections
import csv
import numpy as np
from scipy import stats
from sklearn.linear_model import LinearRegression
from datetime import datetime
sns.set_theme(style="whitegrid")
plt.rcParams["font.family"] = "sans-serif"

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
    inv_tag_map = collections.defaultdict(str)
    for i, row in taglist.iterrows():
        tagMap[row["iGreen database tag name"]] = (
            row["Tag"],
            row["Description"],
            row["Units"],
            row['id'], 
        )
        if row['id'] == row['id']:
            inv_tag_map[row["Tag"]] = f'[{int(row["id"])}] {row["iGreen database tag name"]}'
        else:
            inv_tag_map[row["Tag"]] = row["iGreen database tag name"]

    return tagMap, inv_tag_map


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
        sub_parser = JSONParser(subnet_file)
        sub_net = sub_parser.initialize_network(name=subnet_name)
        net = parser.extend_node(
            sub_net, subnet_name, connection_file, verbose=False, inplace=True
        )
    return net


def load_data(csv_paths, columns=[], remove_outliers=False, replace_zero=False):
    dateparse = lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S")
    flows_series = collections.defaultdict(pd.Series)  # {tag: flow_series}
    time_series = None
    for csv_path in csv_paths:
        print(f"[*] processing {csv_path}...")
        df = pd.read_csv(csv_path)
        if remove_outliers:
            df = remove_outliers(df, columns=columns)
        if replace_zero:
            df = replace_zero(df, mode="median", threshold=1200, columns=columns)
        for c in df.columns:
            if c == "From date":
                time_series = df[c].map(dateparse)
                continue
            elif c == "To date":
                continue
            flows_series[c] = df[c]
    return flows_series, time_series


def flow_check(net, dfs):
    ng_tags = [tag.id for tag in net.select_objs(tag_type=TagType.Flow, recurse=True)]
    print(f"[*] total flow tags: {len(ng_tags)}")

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
    data_series, 
    tags, 
    inv_tag_map, 
    out_dir, 
    export_csv=True, 
    title="", 
    xlabel="time", 
    ylabel=""
):
    df = pd.DataFrame()
    for tag in tags:
        df[tag] = data_series[tag]
        label = inv_tag_map[tag] if tag in inv_tag_map.keys() else tag
        plt.plot(data_series[tag], label=label, alpha=0.7)
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

def plot_flow_loss(flows_series, time_series, net, tagMap, inv_tag_map, days=1, start_date=0, shift=0):
    loss_tag = net.get_tag("FlowLostWithinIntermediateTanksAndFilters", recurse=True)
    lossRatio_tag = net.get_tag("FlowLostWithinIntermediateTanksAndFiltersRatio", recurse=True)
    loss_val = loss_tag.calculate_values(flows_series)
    lossRatio_val = lossRatio_tag.calculate_values(flows_series)

    accumulated_leakage = np.zeros(len(loss_val))
    for i in range(1, len(loss_val)):
        accumulated_leakage[i] = accumulated_leakage[i-1] + loss_val[i]*15

    time_series = list(time_series)

    idx = pd.date_range(time_series[0], time_series[-1], periods=len(time_series))
    h_fmt = mdates.DateFormatter('%m/%d')
    dates = mdates.date2num(time_series)

    if days is not None:
        partial = int(4*24*days)
        if start_date is None:
            start_date = 0
        if shift is None:
            shift = 0
        start_date = (start_date * 4*24) + int(shift * 4*24)
        idx = idx[start_date:start_date+partial]
        dates = dates[start_date:start_date+partial]
        loss_val = loss_val[start_date:start_date+partial]
        lossRatio_val = lossRatio_val[start_date:start_date+partial]
        accumulated_leakage = accumulated_leakage[start_date:start_date+partial]
        for k, v in flows_series.items():
            flows_series[k] = v[start_date:start_date+partial]
        if partial > 4*24*3:
            date_loc = mdates.DayLocator(interval = 1)
            h_fmt = mdates.DateFormatter('%m/%d')
            stride = 240
        elif partial > 4*24:
            date_loc = mdates.HourLocator(interval = 4)
            h_fmt = mdates.DateFormatter('%m/%d %H:%M')
            stride = 64
        elif partial < 4*4:
            date_loc = mdates.MinuteLocator(interval = 15)
            h_fmt = mdates.DateFormatter('%m/%d %H:%M')
            stride = 1
        else:
            date_loc = mdates.MinuteLocator(interval = 60)
            h_fmt = mdates.DateFormatter('%m/%d %H:%M')
            stride = 8
    else:
        date_loc = mdates.DayLocator(interval = 1)
        h_fmt = mdates.DateFormatter('%m/%d')
        stride = 240

    fig, axs = plt.subplots(2, 1, sharex=True, gridspec_kw={'height_ratios': [1, 1]}, figsize=(6, 6))
    ax1 = axs[0]
    colors = ["#88419d", "#006d2c", "#4eb3d3", "#084081"]
    tags = ["FIT_200_001A_P.PV", "Q_400_002A"]
    tag_to_description = {
        "FIT_200_001A_P.PV": "inlet flow Rate",
        "Q_400_002A": "outlet flow Rate",
    }
    ax1.set_xlabel('time')
    ax1.set_ylabel('flow rate (GPM)')
    for i, tag in enumerate(tags):
        ax1.plot(idx, flows_series[tag], label=tag_to_description[tag], color=colors[i])
    ax1.plot(idx, loss_val, color="#d7191c", label="flow residual", alpha=0.7, linestyle='--', linewidth=1.5)

    ax1.tick_params(axis='y')
    ax1.xaxis.set_major_locator(date_loc)
    ax1.xaxis.set_major_formatter(h_fmt)
    ax1.set_xticks(idx[0::stride])

    color2 = '#d7191c'
    # ax2 = axs[1]
    # ax2.plot(dates, lossRatio_val, color=color2, alpha=0.9, linewidth=1.5)
    # ax2.set_ylabel('residual (%)')
    # ax2.set_ylim(-100, 100)
    # ax2.tick_params(axis='y')

    # plot accumulated leakage
    ax3 = axs[1]
    ax3.plot(dates, accumulated_leakage, label="accumulated residual", color=color2, linewidth=1.5)
    ax3.axhline(y = 1690*2, color = 'gray', linestyle = '-') 
    ax3.set_ylabel('accumulated\nresidual (G)')
    ax3.tick_params(axis='y')   

    fig.suptitle('Flow Residual in Tanks And Filters')
    fig.tight_layout()  
    fig.autofmt_xdate()
    fig.legend(loc="upper right", bbox_to_anchor=(1.45, 0.95), fontsize="16")
    fig.savefig(f"vis/{date}_{days}_flow_loss_A.png", bbox_inches="tight")

def plot_MPD_leakage_and_BW(flows_series, time_series, net, tagMap, inv_tag_map, days=0, start_date=0, shift=0):
    LeakageWithinMPD_tag = net.get_tag("LeakageWithinMPD", recurse=True)
    LeakageWithinMPDRatio_tag = net.get_tag("LeakageWithinMPDRatio", recurse=True)
    BWFraction_tag = net.get_tag("BWFraction", recurse=True)
    ResidualBeforeRO_tag = net.get_tag("ResidualBeforeRO", recurse=True)
    Leakage_val = LeakageWithinMPD_tag.calculate_values(flows_series)
    LeakageRatio_val = LeakageWithinMPDRatio_tag.calculate_values(flows_series)
    BW_val = BWFraction_tag.calculate_values(flows_series)
    ResidualBeforeRO_val = ResidualBeforeRO_tag.calculate_values(flows_series)
    # calculate accumulated leakage from Leakage_val
    accumulated_leakage = np.zeros(len(Leakage_val))
    for i in range(1, len(Leakage_val)):
        accumulated_leakage[i] = accumulated_leakage[i-1] + Leakage_val[i]*15

    time_series = list(time_series)
    idx = pd.date_range(time_series[0], time_series[-1], periods=len(time_series))
    dates = mdates.date2num(time_series)
    
    if days is not None:
        partial = int(4*24*days)
        if start_date is None:
            start_date = 0
        if shift is None:
            shift = 0
        start_date = (start_date * 4*24) + int(shift * 4*24)
        idx = idx[start_date:start_date+partial]
        dates = dates[start_date:start_date+partial]
        Leakage_val = Leakage_val[start_date:start_date+partial]
        LeakageRatio_val = LeakageRatio_val[start_date:start_date+partial]
        accumulated_leakage = accumulated_leakage[start_date:start_date+partial]
        ResidualBeforeRO_val = ResidualBeforeRO_val[start_date:start_date+partial]
        BW_val = BW_val[start_date:start_date+partial]
        print(f'[*] partial: {partial}, start_date: {start_date}, shift: {shift}')
        for k, v in flows_series.items():
            flows_series[k] = v[start_date:start_date+partial]
        if partial > 4*24*3:
            date_loc = mdates.DayLocator(interval = 1)
            h_fmt = mdates.DateFormatter('%m/%d')
            stride = 240
        elif partial > 4*24:
            date_loc = mdates.HourLocator(interval = 4)
            h_fmt = mdates.DateFormatter('%m/%d %H:%M')
            stride = 64
        elif partial < 4*4:
            date_loc = mdates.MinuteLocator(interval = 15)
            h_fmt = mdates.DateFormatter('%m/%d %H:%M')
            stride = 1
        else:
            date_loc = mdates.MinuteLocator(interval = 60)
            h_fmt = mdates.DateFormatter('%m/%d %H:%M')
            stride = 8
    else:
        date_loc = mdates.DayLocator(interval = 1)
        h_fmt = mdates.DateFormatter('%m/%d')
        stride = 240

    fig, axs = plt.subplots(2, 1, sharex=True, gridspec_kw={'height_ratios': [1, 1]}, figsize=(6, 6))
    ax1 = axs[0]
    colors = ["#88419d", "#006d2c", "#4eb3d3", "#084081"]
    tags = ["FIT_200_001A_P.PV", "FIT_200_004A_P.PV", "FIT_400_001A_P.PV", "FIT_400_002A_P.PV"]
    tag_to_description = {
        "FIT_200_001A_P.PV": "inlet flow rate",
        "FIT_200_004A_P.PV": "blackwash flow rate",
        "FIT_400_001A_P.PV": "brine flow rate",
        "FIT_400_002A_P.PV": "product flow rate",
        "PT_200A_Tags.Q_Filtrate_PV": "Feed Flow to RO", 
    }
    ax1.plot(dates, Leakage_val, color="#d7191c", label="flow residual", alpha=0.7, linestyle='--', linewidth=1.5)
    ax1.set_xlabel('time')
    ax1.set_ylabel('flow rate (GPM)')
    for i, tag in enumerate(tags):
        ax1.plot(idx, flows_series[tag], label=tag_to_description[tag], color=colors[i], alpha=0.9)
    ax1.tick_params(axis='y')
    ax1.xaxis.set_major_locator(date_loc)
    ax1.xaxis.set_major_formatter(h_fmt)
    ax1.set_xticks(idx[0::stride])

    # ax2 = axs[1]

    color2 = '#d7191c'
    # ax2.plot(dates, LeakageRatio_val, color=color2, alpha=0.9, linewidth=1.5)
    # ax2.set_ylabel('residual (%)')
    # ax2.set_ylim(-100, 100)
    # ax2.tick_params(axis='y')

    # plot accumulated leakage
    ax3 = axs[1]
    ax3.plot(dates, accumulated_leakage, label="accumulated residual", color=color2, linewidth=1.5)
    ax3.axhline(y = 1690*2, color = 'gray', linestyle = '-') 
    ax3.set_ylabel('accumulated\nresidual (G)')
    ax3.tick_params(axis='y')   

    fig.suptitle('Flow Residual in MPDA (a month)')
    fig.tight_layout()  
    fig.autofmt_xdate()
    fig.legend(loc="upper right", bbox_to_anchor=(1.3, 0.9))
    fig.savefig(f"vis/{date}_{days}_MPDLeakage_A.png", bbox_inches="tight")

    plt.clf()

    fig, ax1 = plt.subplots()
    colors = ['tab:green', 'tab:blue']
    tags = ["FIT_200_004A_P.PV", "FIT_200_001A_P.PV"]
    ax1.set_xlabel('time')
    ax1.set_ylabel('Flow Rate (GPM)', color=colors[0])
    for i, tag in enumerate(tags):
        ax1.plot(idx, flows_series[tag], label=tag_to_description[tag], color=colors[i], alpha=0.7)
    
    ax1.tick_params(axis='y', labelcolor=colors[0])
    ax1.xaxis.set_major_locator(date_loc)
    ax1.xaxis.set_major_formatter(h_fmt)
    ax1.set_xticks(idx[0::stride])

    ax2 = ax1.twinx() 

    color2 = 'tab:red'
    ax2.set_ylabel('BW fraction', color=color2)
    ax2.plot(dates, BW_val, color=color2, label="BW fraction", alpha=0.7, linestyle='--', linewidth=2)
    ax2.tick_params(axis='y', labelcolor=color2)

    fig.suptitle('BW fraction MPDA')
    fig.tight_layout()  
    fig.autofmt_xdate()
    fig.legend(loc="upper right", bbox_to_anchor=(1.6, 1.0))
    fig.savefig(f"vis/{date}_{days}_BWfraction_A.png", bbox_inches="tight")

def estimate_volumn(flows_series, time_series, net, tagMap, inv_tag_map, days=1, start_date=None, shift=None):
    level = flows_series["LT_200_002A_P.PV"] # feet
    BWResidual = net.get_tag("BWResidual", recurse=True)
    BWResidual_val = BWResidual.calculate_values(flows_series)

    time_series = list(time_series)
    idx = pd.date_range(time_series[0], time_series[-1], periods=len(time_series))
    dates = mdates.date2num(time_series)

    if days is not None:
        partial = int(4*24*days)
        if start_date is None:
            start_date = 0
        if shift is None:
            shift = 0
        start_date = (start_date * 4*24) + int(shift * 4*24)
        idx = idx[start_date:start_date+partial]
        dates = dates[start_date:start_date+partial]
        level = level[start_date:start_date+partial]
        BWResidual_val = BWResidual_val[start_date:start_date+partial]
        for k, v in flows_series.items():
            flows_series[k] = v[start_date:start_date+partial]
        if partial > 4*24*3:
            date_loc = mdates.DayLocator(interval = 1)
            h_fmt = mdates.DateFormatter('%m/%d')
            stride = 240
        elif partial > 4*24:
            date_loc = mdates.HourLocator(interval = 4)
            h_fmt = mdates.DateFormatter('%m/%d %H:%M')
            stride = 64
        elif partial < 4*4:
            date_loc = mdates.MinuteLocator(interval = 15)
            h_fmt = mdates.DateFormatter('%m/%d %H:%M')
            stride = 1
        else:
            date_loc = mdates.MinuteLocator(interval = 60)
            h_fmt = mdates.DateFormatter('%m/%d %H:%M')
            stride = 8
    else:
        date_loc = mdates.DayLocator(interval = 1)
        h_fmt = mdates.DateFormatter('%m/%d')
        stride = 240

    fig, axs = plt.subplots(2, 1, sharex=True, gridspec_kw={'height_ratios': [1, 1]}, figsize=(8, 6))
    ax1 = axs[0]
    colors = ["#88419d", "#006d2c"]
    tags = ["FIT_200_004A_P.PV", "FIT_200_002A_P.PV"]
    tag_to_description = {
        "FIT_200_002A_P.PV": "pump discharge flow rate",
        "FIT_200_004A_P.PV": "tank feed flow rate"
    }
    ax1.set_xlabel('time')
    ax1.set_ylabel('flow Rate (GPM)')
    for i, tag in enumerate(tags):
        ax1.plot(idx, flows_series[tag], label=tag_to_description[tag], color=colors[i])
    
    # plot difference between two flow rate
    ax1.plot(idx, BWResidual_val, label="flow rate difference", color='#4eb3d3', alpha=0.8, linestyle='--', linewidth=1.5)

    # use regression on different betwen two flow rate to estimate the area of the tank
    # diffenece unit: gallons per minute, time step: 15 minutes
    # estimate volumn change: diff * 15
    # volumn = level * area
    volumn = np.zeros(len(level))
    for i in range(1, len(level)):
        volumn[i] = volumn[i-1] + BWResidual_val[i]*15

    # plot level
    color2 = "#084081"
    ax2 = axs[1]
    ax2.plot(idx, level, label="tank level", color=color2)
    ax2.set_ylabel('level (feet)', color=color2)
    ax2.tick_params(axis='y', labelcolor=color2)
    ax2.xaxis.set_major_locator(date_loc)
    ax2.xaxis.set_major_formatter(h_fmt)
    ax2.set_xticks(idx[0::stride])

    color3 = "#d7191c"
    ax3 = ax2.twinx()
    ax3.plot(idx, volumn, label="estimeted volumn", color=color3)
    ax3.set_ylabel('volumn (G)', color=color3)
    ax3.tick_params(axis='y', labelcolor=color3)

    X = np.array(level).reshape(-1, 1)
    reg = LinearRegression().fit(X, volumn)
    print(f'[*] regression score: {reg.score(X, volumn)}')
    print(f'[*] regression coef: {reg.coef_}')
    print(f'[*] regression intercept: {reg.intercept_}')

    fig.suptitle('I/O Flow Rate and Tank Level in Backwash')
    fig.tight_layout()  
    fig.autofmt_xdate()
    fig.legend(loc="upper right", bbox_to_anchor=(1.3, 0.95), fontsize="16")
    fig.savefig(f"vis/{date}_{days}_BWTankEsti_A.png", bbox_inches="tight")

if __name__ == "__main__":
    dates = ["2023_01", "2023_04", "2023_05", "2023_06"]
    # dates = ["2023_01"]

    tagMap, inv_tag_map = get_tags(taglist_path)

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
    days = 1
    start_date = 0
    shift = 0

    for date in dates:
        data_files = [
            f"data/SBData/{date}/processed/EnergyDataMPDA.csv",
        ]
        # f"data/SBData/{date}/processed/EnergyDataMPDB,.csv",
        # f"data/SBData/{date}/processed/EnergyDataMPDC.csv",
        # f"data/SBData/{date}/processed/EnergyDataNonMPD.csv"]
        flows_series, time_series = load_data(data_files, columns=target_tags)

        plt.clf()
        # plot_MPD_leakage_and_BW(flows_series, time_series, net, tagMap, inv_tag_map, days=days, start_date=start_date, shift=shift)
        plot_flow_loss(flows_series, time_series, net, tagMap, inv_tag_map, days=days, start_date=start_date, shift=shift)
        # estimate_volumn(flows_series, time_series, net, tagMap, inv_tag_map, days=days, start_date=start_date, shift=shift)
        # draw_graph(net, pyvis=False, output_file="vis/CompleteDesal.png")

        # plot_by_tags(
        #     flows_series,
        #     target_tags,
        #     inv_tag_map, 
        #     "vis/",
        #     export_csv=False,
        #     title=f"{date}_FlowLostWithinIntermediateTanksAndFilters_A",
        #     xlabel="time",
        #     ylabel="flow",
        # )

    # flow_check(net, data_files)
    # draw_graph(net, pyvis=False, output_file="vis/CompleteDesal.png")
