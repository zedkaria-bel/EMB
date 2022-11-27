import os
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ['DJANGO_SETTINGS_MODULE'] = 'embapp.settings'
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "embapp.settings")
import datetime
from operator import mod, ne
import re
import django
import pandas as pd
import numpy as np
import locale
from openpyxl import load_workbook
import psycopg2
from django.conf import settings
import datetime
from sqlalchemy import create_engine, false, true
from sqlalchemy.orm import sessionmaker
import json

con = psycopg2.connect(database=settings.DB, user=settings.DB_USER, password=settings.DB_PASSWORD, host=settings.DB_HOST, port=settings.DB_PORT)
con.autocommit = True
engine = create_engine(f'postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB}')
Session = sessionmaker(bind = engine)
session = Session()
cursor = con.cursor()

pd.set_option('display.max_rows', None)
locale.setlocale(locale.LC_ALL, 'fr_FR')

table_name = 'public."Flash_Impression"'

df = pd.read_sql_query('select * from ' + table_name, con=engine)

# df['atelier_impr'] = np.nan
# df['category'] = np.nan
# df['format_prod'] = np.nan
# df['format_subst'] = np.nan

# df['format_prod'] = df['des'].str.lower().replace({
#     r'^.*(\d\s*/\s*\d).*(sub|sb).*(\d\s*/\s*\d).*': r'\1 \2 \3'
# }, regex=True)

regex_exps = {
    'sub': [
        r'^.*?(\d\s*/\s*\d).*(sub.+|sb.+).*(\d\s*/\s*\d).*',
        r'^.*?(\d\s*/\s*\d).*(sub.+|sb.+).*(\d+\s*kg).*',
        r'^.*?(\d\s*/\s*\d).*(sub.+|sb.+).*(\w{3}.*\d{2}(,|.)?\d*)',
        r'^.*?(\d\s*/\s*\d).*(sub.+|sb.+).*(\d+\s*\w+).*',
        r'^.*?(\w{3}.*\d{2,}).*(sub.+|sb.+).*(\w{3}.*\d{2}(,|.)?\d*)',
        r'^.*?(\d+\s*\w+).*(sub.+|sb.+).*(\d+\s*kg).*',
        r'^.*?(\d+\s*\w+).*(sub.+|sb.+).*(\d\s*/\s*\d).*',
        r'^.*?(\d+\s*\w+).*(sub.+|sb.+).*(\d{1,}\s*(.|,)?\d).*',
        r'^.*?(\d+\s*\w+).*(sub.+|sb.+).*(\d+\s*\w+).*',
    ],
    'non-sub': [
        r'^.*?(\d\s*/\s*\d).*',
        r'^.*?(0\s*(\,|\.)\s*8\d*\s*l)',
        r'^.*?(\w{3}\s*(:|/)*\s*\d{1,}\s*\w{1,})',
        r'^.*?(\w{3}.*\d{2,})',
        r'^.*?(\d+\s*\w+).*',
        r'^(?=.*/)(?!.*\d).*',
        r'^(?=.*\w)(?!.*\d).*',
    ]
}


for idx, row in df.iterrows():
    des = df.iloc[idx]['des'].lower()
    sub_idx = 0
    nonsub_idx = 0
    match = None
    exc = False
    while True:
        if 'sub' in des or 'sb' in des:
            if sub_idx == len(regex_exps['sub']):
                exc = True
                break
            match = re.search(regex_exps['sub'][sub_idx], des)
            if match:
                df.at[idx, 'format_prod'] = str(match.group(1)).upper()
                if 'kg' in des:
                    df.at[idx, 'format_subst'] = None
                else:
                    df.at[idx, 'format_subst'] = str(match.group(3)).upper()
        else:
            if nonsub_idx == len(regex_exps['non-sub']):
                exc = True
                break
            match = re.search(regex_exps['non-sub'][nonsub_idx], des)
            if match:
                # print(match.groups())
                if regex_exps['non-sub'][nonsub_idx] == r'^(?=.*/)(?!.*\d).*' or regex_exps['non-sub'][nonsub_idx] == r'^(?=.*\w)(?!.*\d).*':
                    df.at[idx, 'format_prod'] = None
                else:
                    df.at[idx, 'format_prod'] = str(match.group(1)).upper()
                df.at[idx, 'format_subst'] = None
        sub_idx += 1
        nonsub_idx += 1
        if match:
            break
    if exc:
        break
if exc:
    print(des.upper())
else:
    df.loc[(df['format_prod'].str.upper().str.contains('1\s*(L|Ø|D)', na = False)) & (df['des'].str.contains('108', na = False)), 'format_prod'] = '0.8 / 1 L Ø 108'
    df.loc[(df['format_prod'].str.upper().str.contains('1\s*L', na = False)) & (df['des'].str.contains('83', na = False)), 'format_prod'] = '1 L Ø 83'
    df.loc[df['format_prod'].str.contains('\s*1 L$', na = False), 'format_prod'] = None
    df.loc[df['format_prod'].str.contains('3/1', na = False), 'format_prod'] = '5/1'
    df.loc[df['format_prod'].str.contains('3\s*L', na = False), 'format_prod'] = '3 L'
    df.loc[df['format_prod'].str.contains('6\s*OZ', na = False), 'format_prod'] = '16 OZ'
    df.loc[df['format_subst'].str.contains('6\s*OZ', na = False), 'format_subst'] = '16 OZ'
    df.loc[df['format_prod'].str.contains('4\s*OZ', na = False), 'format_prod'] = '4 OZ'
    df.loc[df['des'].str.contains('FDS.*73', na = False), 'format_prod'] = 'FDS Ø 73'
    df.loc[df['des'].str.contains('0\s*(\,|\.)\s*8\d*\s*L', na = False), 'format_prod'] = '0.8 / 1 L Ø 108'
    df.loc[df['format_subst'].str.contains('0\s*(\,|\.)\s*8', na = False), 'format_subst'] = '0.8 L Ø 108'
    df.loc[df['des'].str.contains('(18\s*L|20\s*L)|(PAILS\s*18)|(PAILS\s*20)', na = False), 'format_prod'] = '18 / 20 L'
    df.loc[df['des'].str.contains('10\s*L', na = False), 'format_prod'] = '10 L'
    df.loc[df['des'].str.contains('CAT.*AMOU', na = False), 'format_prod'] = '1/2'
    df.loc[df['format_prod'].str.contains('108', na = False) & df['format_subst'].str.contains('1/2', na = False), 'format_subst'] = '1/2 L Ø 108'
    df.loc[df['des'].str.lower().str.contains(r'(sub\w+|sb\w+).*1\s*8\s*l?', na = False) & df['format_prod'].str.contains('18 / 20 L', na = False), 'format_subst'] = '18 L'
    df.loc[(df['des'].str.upper().str.contains('FDS', na = False)) & (df['des'].str.contains('153', na = False)), 'format_prod'] = 'FDS Ø 153'
    df.loc[(df['des'].str.upper().str.contains('FDS', na = False)) & (df['des'].str.contains('65', na = False)), 'format_prod'] = 'FDS Ø 65'
    df.loc[(df['format_prod'].str.upper().str.contains('5/1', na = False)) & (df['des'].str.lower().str.contains('sub|sb', na = False)) & (~df['des'].str.lower().str.contains('kg', na = False)), 'format_subst'] = '3/1'

    # print(df.loc[~df['des'].str.lower().str.contains('sub|sb', na = False), ['des', 'format_prod', 'format_subst']])

    # Filling atelier_impr and category cols

    table_name = 'public."PROGRAMME_DT"'
    pg_dt_df = pd.read_sql_query('select * from ' + table_name, con=engine)

    pg_dt_df = pg_dt_df.loc[pg_dt_df['atelier'] == 'Imprimerie']
    pg_dt_bte_df = pg_dt_df.loc[pg_dt_df['atelier_impr'] == 'Boite']
    df.loc[df['format_prod'].isin(pg_dt_bte_df['format'].unique()), 'atelier_impr'] = 'Boite'

    pg_dt_bte_cons_df = pg_dt_bte_df.loc[pg_dt_bte_df['category'] == 'CONSERVE']
    df.loc[df['format_prod'].isin(pg_dt_bte_cons_df['format'].unique()), 'category'] = 'CONSERVE'
    pg_dt_bte_cons_df = pg_dt_bte_df.loc[pg_dt_bte_df['category'] == 'DIVERSE']
    df.loc[df['format_prod'].isin(pg_dt_bte_cons_df['format'].unique()), 'category'] = 'DIVERSE'



    pg_dt_bte_df = pg_dt_df.loc[pg_dt_df['atelier_impr'] == 'Accessoire']
    df.loc[df['format_prod'].isin(pg_dt_bte_df['format'].unique()), 'atelier_impr'] = 'Accessoire'

    pg_dt_bte_cons_df = pg_dt_bte_df.loc[pg_dt_bte_df['category'] == 'CONSERVE']
    df.loc[df['format_prod'].isin(pg_dt_bte_cons_df['format'].unique()), 'category'] = 'CONSERVE'
    pg_dt_bte_cons_df = pg_dt_bte_df.loc[pg_dt_bte_df['category'] == 'DIVERSE']
    df.loc[df['format_prod'].isin(pg_dt_bte_cons_df['format'].unique()), 'category'] = 'DIVERSE'


    # print(pg_dt_bte_cons_df['format'].unique())

    tab_name = 'Flash_Impression'
    cursor.execute('TRUNCATE TABLE public."' + tab_name + '"')
    df.to_sql(tab_name, engine, if_exists='append', index=False)


    # formats = df['format_subst'].unique()
    # formats = sorted(formats, key=lambda x: str(x))
    # for f in formats:
    #     print("'" + str(f) + "'")