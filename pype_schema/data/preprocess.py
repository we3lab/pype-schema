import pandas as pd
import sys
import collections

taglist_path = "./SBData/TagList.xlsx"


def load_taglist(taglist_path):
    taglist = pd.read_excel(taglist_path)
    tagMap = collections.defaultdict(str)
    for i, row in taglist.iterrows():
        tagMap[row["iGreen database tag name"]] = (
            row["Tag"],
            row["Description"],
            row["Units"],
        )
    return tagMap


def process_raw(xlsx_path, tagMap, tag_mapping=None):
    df = pd.read_excel(
        xlsx_path, skiprows=range(6), index_col=None, header=0, engine="openpyxl"
    )
    new_cols = dict()
    for i, c in enumerate(df.columns):
        k = c.strip().replace("\n", "").replace("Weighted Avg", "")
        if i < 2:
            new_cols[c] = k
            continue
        if k not in tagMap:
            print(f"Warning: tag {k} not found in taglist")
            df = df.drop(columns=[c])
            continue
        new_cols[c] = tagMap[k][0]
        if tag_mapping is not None:
            tag_mapping[k] = tagMap[k][0]
    df.rename(columns=new_cols, inplace=True)
    return df, tag_mapping


if __name__ == "__main__":
    tag_mapping = collections.defaultdict(str)
    date = "2023_06"
    xlsx_names = [
        f"SBData/{date}/EnergyDataMPDA",
        f"SBData/{date}/EnergyDataMPDB",
        f"SBData/{date}/EnergyDataMPDC",
        f"SBData/{date}/EnergyDataNonMPD",
    ]
    tagMap = load_taglist(taglist_path)
    for name in xlsx_names:
        new_df, tag_mapping = process_raw(name + ".xlsx", tagMap, tag_mapping)
        new_df.to_csv(name + ".csv", index=False, float_format="%.2f")
    # with open('SBData/Name2Tags.csv', 'w') as csvfile:
    #     csvfile.write('name,tag\n')
    #     for k, v in tag_mapping.items():
    #         csvfile.write(f'{k},{v}\n')
