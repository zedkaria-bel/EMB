import os
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ['DJANGO_SETTINGS_MODULE'] = 'embapp.settings'
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "embapp.settings")
import datetime
from operator import mod
import re
import django
import pandas as pd
import numpy as np
from openpyxl import load_workbook
import psycopg2
from django.conf import settings
import datetime
from sqlalchemy import create_engine, false, true
from sqlalchemy.orm import sessionmaker

con = psycopg2.connect(database=settings.DB, user=settings.DB_USER, password=settings.DB_PASSWORD, host=settings.DB_HOST, port=settings.DB_PORT)
con.autocommit = True
engine = create_engine(f'postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB}')
Session = sessionmaker(bind = engine)
session = Session()
cursor = con.cursor()

pd.set_option('display.max_rows', None)

def get_meta_workforce_df(df_meta_workforce, count):    
    # DATAFRAME META
    df_meta_workforce = df_meta_workforce.loc[df_meta_workforce['Unnamed: 0'].notnull()]
    df_meta_workforce = df_meta_workforce.copy()
    df_meta_workforce.drop(
        columns = ['Unnamed: 4']
    , inplace = True)
    df_meta_workforce.columns.values[2] = 'Unnamed: 2'
    df_tmp = df_meta_workforce
    df_meta_workforce = pd.DataFrame()
    unit = df_tmp.at[0, 'Unnamed: 1']
    dim = df_tmp.at[2, 'Unnamed: 1']
    code = df_tmp.at[4, 'Unnamed: 1']
    pds_brut_1000 = df_tmp.at[1, 'Unnamed: 5']
    if pds_brut_1000:
        pds_brut_1000 = str(pds_brut_1000)
        try:
            if '=' in pds_brut_1000:
                match = re.search(r'.*=\s+(\S+)', pds_brut_1000)
                pds_brut_1000 = match.group(1)
            pds_brut_1000 = int(pds_brut_1000.strip())
        except ValueError:
            pds_brut_1000 = float(pds_brut_1000.strip().replace(',', '.'))
    pds_net_1000 = df_tmp.at[2, 'Unnamed: 5']
    if pds_net_1000:
        pds_net_1000 = str(pds_net_1000)
        try:
            if '=' in pds_net_1000:
                match = re.search(r'.*=\s+(\S+)', pds_net_1000)
                pds_net_1000 = match.group(1)
            pds_net_1000 = int(pds_net_1000.strip())
        except ValueError:
            pds_net_1000 = float(pds_net_1000.strip().replace(',', '.'))
    nb_instal = df_tmp.at[3, 'Unnamed: 5']
    if nb_instal:
        nb_instal = str(nb_instal)
        try:
            nb_instal = int(nb_instal.strip())
        except ValueError:
            nb_instal = float(nb_instal.strip())
    phase_fab = df_tmp.at[4, 'Unnamed: 5']
    if phase_fab:
        phase_fab = str(phase_fab)
        try:
            phase_fab = int(phase_fab.strip())
        except ValueError:
            phase_fab = float(phase_fab.strip())
    if '…' in code or '..' in code:
        code = np.nan
    if len(dim.strip()) == 1 or 'mm' not in dim.lower():
        dim = np.nan
    if 'koub' in unit.lower():
        unit = 'KDU'
    elif 'azz' in unit.lower() or 'azd' in unit.lower():
        unit = 'AZDU'
    elif 'skik' in unit.lower() or 'skd' in unit.lower():
        unit = 'SKDU'
    df_meta_workforce['unit'] = pd.Series([unit])
    df_meta_workforce['product'] = pd.Series([df_tmp.at[1, 'Unnamed: 1']])
    df_meta_workforce['dim'] = pd.Series([dim])
    df_meta_workforce['num_instal'] = pd.Series([df_tmp.at[3, 'Unnamed: 1'].upper()])
    df_meta_workforce['code'] = pd.Series([code])
    df_meta_workforce['cob'] = pd.Series([df_tmp.at[0, 'Unnamed: 3'].upper()])
    df_meta_workforce['pds_brut_1000'] = pd.Series([pds_brut_1000])
    df_meta_workforce['pds_net_1000'] = pd.Series([pds_net_1000])
    df_meta_workforce['nb_instal'] = pd.Series([nb_instal])
    df_meta_workforce['phase_fab'] = pd.Series([phase_fab])
    df_meta_workforce.insert(0, 'id', count, count + 1)
    df_meta_workforce['date'] = datetime.date.today()
    return df_meta_workforce

def get_consom_workforce_df(df_consom_workforce):
    df_consom = df_consom_workforce.copy()
    consom_workforce_end = df_consom.index[df_consom['Unnamed: 1'].str.lower().str.contains('total', na = False)].tolist()
    consom_workforce_begin = df_consom.index[df_consom['Unnamed: 0'].str.lower().str.contains('main', na = False)].tolist()
    frames = []
    for i in range(2):
        df_consom_workforce = df_consom.loc[consom_workforce_begin[i]:consom_workforce_end[i]-1]
        df_consom_workforce.reset_index(drop = True, inplace = True)
        mode = df_consom_workforce.at[0, 'Unnamed: 0']
        if 'indi' in mode.lower() or 'moi' in mode.lower():
            mode = 'MOI'
        else:
            mode = 'MOD'
        df_consom_workforce = df_consom_workforce.loc[df_consom_workforce['Unnamed: 1'].notnull()]
        df_consom_workforce = df_consom_workforce.iloc[1:]
        df_consom_workforce.rename(columns={
            df_consom_workforce.columns.values[0]:'code',
            df_consom_workforce.columns.values[1]:'des',
            df_consom_workforce.columns.values[2]:'nb_post',
            df_consom_workforce.columns.values[3]:'nb_agent',
            df_consom_workforce.columns.values[4]:'real_cad_hor',
            df_consom_workforce.columns.values[5]:'time_consum_thsd'
        }, inplace = True)
        try:
            df_consom_workforce['time_consum_thsd'] = (df_consom_workforce['nb_agent'] * 1000) / df_consom_workforce['real_cad_hor']
        except:
            df_consom_workforce['time_consum_thsd'] = 0
        df_consom_workforce['mode'] = mode
        frames.append(df_consom_workforce)
    df_consom_workforce = pd.concat(frames)
    return df_consom_workforce


workforce_file = r"C:\Users\zaki1\Desktop\Controle de Gestion\DCG\Mise à jour fiches main d'oeuvres standard EPE EMB Spa 2022.xlsx"

book = load_workbook(workforce_file)
xl = pd.ExcelFile(workforce_file, engine='openpyxl') # pylint: disable=abstract-class-instantiated
count = 1
count_consom = 1
meta_frames = []
consom_frames = []
for sheetname in xl.sheet_names:
    if 'page' not in sheetname.lower() and 'somm' not in sheetname.lower():
        # print(sheetname)
        df = pd.read_excel(workforce_file, sheet_name=sheetname)
        dfs = df.index[df['Unnamed: 0'].str.lower().str.contains('unite', na = False)].tolist()

        for idx, val in enumerate(dfs):
            # print(idx, val)
            try:
                sub_df = df.loc[val: dfs[idx+1]]
            except IndexError:
                sub_df = df.loc[val:]
            sub_df.reset_index(drop = True, inplace = True)
            meta_workforce_end = sub_df.index[sub_df['Unnamed: 0'].str.lower().str.contains('direct', na = False)].tolist()[0]
            df_meta_workforce = sub_df.loc[0:meta_workforce_end-2]
            df_meta_workforce = get_meta_workforce_df(df_meta_workforce, count)
            df_consom_workforce = sub_df.loc[meta_workforce_end:]
            df_consom_workforce = get_consom_workforce_df(df_consom_workforce)
            df_consom_workforce['id_meta'] = df_meta_workforce.at[0, 'id']
            count += 1
            # print(df_consom_workforce)
            meta_frames.append(df_meta_workforce)
            consom_frames.append(df_consom_workforce)
        df_meta_workforce = pd.concat(meta_frames)
        df_consom_workforce = pd.concat(consom_frames)
        count_consom += len(df_consom_workforce)

# print(df_meta_workforce)
df_consom_workforce.reset_index(drop = True, inplace = True)
df_consom_workforce.insert(0, 'id', range(1, len(df_consom_workforce) + 1))
df_consom_workforce = df_consom_workforce.loc[:, ~df_consom_workforce.columns.str.contains('^Unnamed')]
# print(df_consom_workforce)
# df_meta_workforce.to_sql()
df_meta_workforce.to_sql('Workforce_Meta', engine, if_exists='append', index=False)
df_consom_workforce.to_sql('Workforce_Consom', engine, if_exists='append', index=False)