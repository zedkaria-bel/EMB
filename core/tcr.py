import pandas as pd
import numpy as np
import re
import datetime
import os
from openpyxl import load_workbook
import dateparser

file_str = r'C:\Users\zaki1\Desktop\Controle de Gestion\TCR DCGSI 2020 2021 ZAKI\TCR 2020 EMB (RSLT 19MDA).xlsx'

book = load_workbook(file_str)
xl = pd.ExcelFile(file_str, engine='openpyxl') # pylint: disable=abstract-class-instantiated
for sheetname in xl.sheet_names:
    if re.match("^[0-9 ]+$", sheetname):
        # print(sheetname)
        df = pd.read_excel(file_str, sheet_name=sheetname, header=1)
        # print(df)
        period = df['Unnamed: 0'][2]
        match = re.search(r'\w*\s(\w+)-(\d{4})', period)
        month = dateparser.parse(match.group(1)).month
        year = dateparser.parse(match.group(2)).year
        df = pd.read_excel(file_str, sheet_name=sheetname, header=1, skiprows=4)
        last_idx = df[df['N°'].str.contains('RATIO', na = False)].index.to_list()[0]
        df = df[['Désignation ', 'SIEGE', 'KDU', 'SKDU', 'AZDU', 'ENTREPRISE']]
        df = df.iloc[0: last_idx - 1 , :]
        df = df.T
        df.columns = df.iloc[0]
        df = df.iloc[1: , :]
        df['date'] = datetime.date(year, month, 28)
        df.fillna(0, inplace = True)
        if month < 10:
            month = '0' + str(month)
        else:
            month = str(month)
        folder = r'C:\Users\zaki1\Desktop\Controle de Gestion\Scripts\TCR'
        file_name = 'TCR_' + str(month) + '_' + str(year) + '.xlsx'
        df.reset_index(level=0, inplace=True)
        df.rename(columns={ df.columns[0]: "Unité" }, inplace = True)

        # Only for tcr 2020
        df.insert(9, 'Consommation inter-unités', 0)

        df.to_excel(folder + '\\' + file_name, index = False)
        # print(df)
        # break
