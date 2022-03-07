import os
import django
import pandas as pd
import numpy as np
import datetime
import re
# pylint: disable=import-error
from flasah_test import get_prod_phy

new_act_journ = r'C:\Users\zaki1\Downloads\Activité journalière au 02 mars 2022.xlsx'

bg_df = pd.read_excel(new_act_journ, sheet_name='01 Prod Physique Boites', skiprows=7, header=1)
# Rename the first column so we could address it
bg_df.columns.values[0] = 'Unnamed: 0'
bg_df.columns.values[1] = 'Unnamed: 1'
bg_df.columns.values[2] = 'Unnamed: 2'
bg_df.columns.values[3] = 'Unnamed: 3'
bg_df.columns.values[6] = 'Unnamed: 6'

# For the old ones (september w etle3)
# bg_df = bg_df.iloc[: , :21]
# bg_df.loc[bg_df['Unnamed: 0'].str.lower().str.contains(r'^\s*unité\s*kdu\s*$', na = False, regex = True), 'Unnamed: 0'] = 'KDU'
# bg_df.loc[bg_df['Unnamed: 0'].str.lower().str.contains(r'^\s*unité\s*azdu\s*$', na = False, regex = True), 'Unnamed: 0'] = 'AZDU'
# bg_df.loc[bg_df['Unnamed: 0'].str.lower().str.contains(r'^\s*skdu\s*$', na = False, regex = True), 'Unnamed: 0'] = 'SKDU'
result = pd.DataFrame()
dfs = bg_df.index[bg_df['Unnamed: 0'].str.contains('Unité', na = False)].tolist()
frames = []
for idx, val in enumerate(dfs):
    df = pd.DataFrame()
    # print(val, dfs[idx+1])
    try:
        df = bg_df.loc[val: dfs[idx+1]]
    except IndexError:
        df = bg_df.loc[val:]
    # df = df.iloc[3: , :]
    df = df.reset_index(drop=True)
    dte = df['Unnamed: 6'][1]
    # print(dte)
    if isinstance(dte, datetime.datetime):
        date = dte.date()
    else:
        match = re.search(r'\d{2}\s*/\d{2}\s*/\d{4}', dte)
        date = datetime.datetime.strptime(match.group(), '%d/%m/%Y').date()
    # print(date)
    max_dt = datetime.date(2020, 1, 1)
    if date > max_dt:
        df.drop(df.tail(1).index,inplace=True)
        df_prod, obj_cap_prod_df = get_prod_phy(df)


# print(bg_df.head())