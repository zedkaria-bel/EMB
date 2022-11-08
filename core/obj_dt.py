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

con = psycopg2.connect(database=settings.DB, user=settings.DB_USER, password=settings.DB_PASSWORD, host=settings.DB_HOST, port=settings.DB_PORT)
con.autocommit = True
engine = create_engine(f'postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB}')
Session = sessionmaker(bind = engine)
session = Session()
cursor = con.cursor()

pd.set_option('display.max_rows', None)
locale.setlocale(locale.LC_ALL, 'fr_FR')

# xls filename
obj_file = r'C:\Users\zaki1\Desktop\Controle de Gestion\nassim  prg.xlsx'


# MODE >> IMPRIMERIE, MONTAGE

# MONTAGE >> Unité : KDU, AZDU & SKDU
#         >> ligne : None

# IMPRIMERIE >> Unité : KDU seul
#         >> ligne : VERNISSEUSE, TANDEM & PRESSE


book = load_workbook(obj_file)
xl = pd.ExcelFile(obj_file, engine='openpyxl') # pylint: disable=abstract-class-instantiated
unit_frames = []
for sheetname in xl.sheet_names:
    frames = []
    unit = sheetname.upper().strip()
    bg_df = pd.read_excel(obj_file, sheet_name=sheetname, skiprows=1, header=1)
    dfs = bg_df.index[bg_df['Unnamed: 0'].str.lower().str.contains('atelier|tandem|vernisseuse', na = False)].tolist()
    frames = []
    ligne = np.nan
    for idx, val in enumerate(dfs):
        df = pd.DataFrame()
        result_df = pd.DataFrame(columns=['unit', 'atelier', 'format', 'atelier_impr', 'category', 'date', 'prev'])
        try:
            df = bg_df.loc[val: dfs[idx+1]]
        except IndexError:
            df = bg_df.loc[val:]
        if 'montage' in df.iloc[0]['Unnamed: 0'].lower():
            atelier = 'Boite'
            ligne = np.nan
        elif 'presse' in df.iloc[0]['Unnamed: 0'].lower():
            atelier = 'Accessoire'
            ligne = np.nan
        else:
            atelier = 'Imprimerie'
            if 'vern' in df.iloc[0]['Unnamed: 0'].lower():
                ligne = 'VERNISSEUSE'
            elif 'tand' in df.iloc[0]['Unnamed: 0'].lower():
                ligne = 'TANDEM'
            else:
                ligne = np.nan
        df = df.iloc[1: , :]
        df.columns = df.iloc[0]
        df = df.iloc[1: , :]
        df = df.reset_index(drop = True)
        df = df.loc[:, ~df.columns.str.lower().str.contains('^unnamed|total', na = False)]
        df = df.loc[~df['Format'].isna()]
        df = df.loc[df['Format'] != ' ']
        IndexNames = df[df['Format'].str.lower().str.contains('atelier|vern|tand', na = False)].index
        df.drop(IndexNames, inplace=True)
        # if atelier != 'Accessoire' :
        #     df = df[:-2]
        # print(df['Format'].str.strip().unique())
        # print(df.loc[df['Format'].str.strip().str.lower().str.contains('1.*/.*2.*l.*108', na = False), 'Format'])
        # print(df.loc[df['Format'].str.strip().str.lower().str.contains('1.*/.*10.*52', na = False), 'Format'])
        df.loc[df['Format'].str.lower().str.contains('4.*oz', na = False), 'Format'] = '4 OZ'
        df.loc[df['Format'].str.strip().str.lower().str.contains('1.*/.*2.*l.*108', na = False), 'Format'] = '1/2 L Ø 108'
        df.loc[df['Format'].str.strip().str.lower().str.contains('1.*/.*10.*52', na = False), 'Format'] = '1/10'
        df.loc[df['Format'].str.lower().str.contains('1.*/.*4', na = False), 'Format'] = '1/4'
        df.loc[df['Format'].str.strip().str.lower().str.contains('^pails.*20.*', na = False), 'Format'] = '20 L'
        df.loc[df['Format'].str.lower().str.contains('(?!.*108).*1.*/.*2.*', na = False), 'Format'] = '1/2'
        df.loc[df['Format'].str.lower().str.contains('4.*/.*4', na = False), 'Format'] = '4/4'
        df.loc[df['Format'].str.lower().str.contains('5.*/.*1', na = False), 'Format'] = '5/1'
        df.loc[df['Format'].str.lower().str.contains('pails.*3,5.*', na = False), 'Format'] = '3 L'
        df.loc[df['Format'].str.lower().str.contains('16.*oz', na = False), 'Format'] = '16 OZ'
        df.loc[df['Format'].str.strip().str.lower().str.contains('^pails.*10.*', na = False), 'Format'] = '10 L'
        df.loc[df['Format'].str.lower().str.contains('1l.*108', na = False), 'Format'] = '1 L Ø 108'
        df.loc[df['Format'].str.lower().str.contains('1l.*83', na = False), 'Format'] = '1 L Ø 83'
        df.loc[df['Format'].str.lower().str.contains('(?!.*pl).*fds.*52.*', na = False), 'Format'] = 'FDS Ø 52.6'
        df.loc[df['Format'].str.lower().str.contains('fds.*73', na = False), 'Format'] = 'FDS Ø 73'
        df.loc[df['Format'].str.lower().str.contains('fds.*99', na = False), 'Format'] = 'FDS Ø 99'
        df.loc[df['Format'].str.lower().str.contains('fds.*153', na = False), 'Format'] = 'FDS Ø 153'
        df.loc[df['Format'].str.lower().str.contains('fds.*169', na = False), 'Format'] = 'FDS Ø 169'
        df.loc[df['Format'].str.lower().str.contains('bch.*180', na = False), 'Format'] = 'BCHS Ø 180'
        df.loc[df['Format'].str.lower().str.contains('cabo', na = False), 'Format'] = 'CABOCHONS'
        df.loc[df['Format'].str.lower().str.contains('fds.*52,6.*pl', na = False), 'Format'] = 'FDS Ø 52.6 PLAT'
        df.loc[df['Format'].str.lower().str.contains('bch.*52,6', na = False), 'Format'] = 'BCHS Ø 52.6'
        df.loc[df['Format'].str.lower().str.contains('fds.*pail.*20', na = False), 'Format'] = 'FDS PAILS 20 L'
        df.loc[df['Format'].str.lower().str.contains('fds.*pail.*10', na = False), 'Format'] = 'FDS PAILS 10 L'
        df.loc[df['Format'].str.lower().str.contains('cvs.*pail.*20', na = False), 'Format'] = 'CVS PAILS 20 L'
        df.loc[df['Format'].str.lower().str.contains('cvs.*pail.*10', na = False), 'Format'] = 'CVS PAILS 10 L'
        df.loc[df['Format'].str.lower().str.contains('fds.*108', na = False), 'Format'] = 'FDS Ø 108'
        df.loc[df['Format'].str.lower().str.contains('bag.*108', na = False), 'Format'] = 'BGS Ø 108'
        df.loc[df['Format'].str.lower().str.contains('bouch.*108', na = False), 'Format'] = 'BCHN Ø 108'
        df.loc[df['Format'].str.lower().str.contains('fds.*83', na = False), 'Format'] = 'FDS Ø 83'
        df.fillna(0, inplace=True)
        # df = df[:-1]
        df.columns.values[1] = 'x_1'
        df.columns.values[2] = 'x_2'
        df.columns.values[3] = 'x_3'
        df.columns.values[4] = 'x_4'
        df.columns.values[5] = 'x_5'
        df.columns.values[6] = 'x_6'
        df.columns.values[7] = 'x_7'
        df.columns.values[8] = 'x_8'
        df.columns.values[9] = 'x_9'
        df.columns.values[10] = 'x_10'
        df.columns.values[11] = 'x_11'
        df.columns.values[12] = 'x_12'
        df['atelier'] = atelier
        df['atelier_impr'] = df['Format']
        df.loc[~df['atelier_impr'].str.lower().str.contains('total', na = False), 'atelier_impr'] = np.nan
        df['atelier_impr'].fillna(method='bfill', inplace=True)
        df['category'] = df['atelier_impr']
        df.loc[df['atelier_impr'].str.lower().str.contains('acc', na = False), 'atelier_impr'] = 'Accessoire'
        df.loc[~df['atelier_impr'].str.lower().str.contains('acc', na = False), 'atelier_impr'] = 'Boite'
        df.loc[df['atelier'] != 'Imprimerie', 'atelier_impr'] = np.nan
        df.loc[df['category'].str.lower().str.contains('cons', na = False), 'category'] = 'CONSERVE'
        df.loc[df['category'].str.lower().str.contains('div', na = False), 'category'] = 'DIVERSE'
        IndexNames = df[df['Format'].str.lower().str.contains('total', na = False)].index
        df.drop(IndexNames, inplace=True)
        IndexNames = df[df['Format'].str.lower().str.contains('div', na = False)].index
        df.drop(IndexNames, inplace=True)
        if unit == 'AZDU':
            df['category'] = 'CONSERVE'
        elif unit == 'SKDU':
            df['category'] = 'DIVERSE'
        # if unit == 'AZDU' and atelier == 'BOITE':
        #     df = df.groupby(['Format', 'atelier', 'atelier_impr', 'category']).sum()[['x_1', 'x_2', 'x_3', 'x_4', 'x_5', 'x_6', 'x_7', 'x_8', 'x_9', 'x_10']]
        # if unit != 'KDU':
        #     print(df)
        #     print('\n')
        # ----------------------------------------------------------------------------------------------
        # | Unité | Atelier | format | Atelier_IMPR | ligne_IMPR | category | date | prev | 
        # ----------------------------------------------------------------------------------------------
        for row in df.iterrows():
            for month in range(1, 13):
                new_row = {
                    'unit': unit,
                    'atelier': atelier,
                    'format': row[1]['Format'],
                    'atelier_impr': row[1]['atelier_impr'],
                    'ligne_impr': ligne,
                    'category': row[1]['category'],
                    'date': datetime.date(datetime.datetime.today().year, month, 25),
                    'prev': row[1]['x_' + str(month)]
                }
                result_df = result_df.append(new_row, ignore_index = True)
        frames.append(result_df)
    result_df = pd.concat(frames)
    result_df = result_df.reset_index(drop = True)
    unit_frames.append(result_df)
    # print(result_df)
    # print('\n')
    # break
final_df = pd.concat(unit_frames)
final_df['prev'] = final_df['prev'].astype(float)
print(final_df)
print(type(final_df['prev']))


final_df.insert(0, 'ID', range(1, 1 + len(final_df)))
final_df.to_sql('PROGRAMME_DT', engine, if_exists='append', index=False)

# with engine.connect() as con:
#     con.execute('ALTER TABLE PROGRAMME_DT ADD PRIMARY KEY (path);')