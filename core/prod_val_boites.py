import pandas as pd
import numpy as np
import re
import datetime


# C:\Users\zaki1\Downloads\prod_val_boites_19122021.xlsx
pd.set_option('display.max_rows', None)

# Checking are there any missed products in 'Prod. Physique' that aren't in 'Prod. Valorisé' 
def missing_prod_in_val(df_prod, result):
    df_prod['Unité'] = df_prod['Unité'].ffill()
    result['Unité'] = result['Unité'].ffill()
    # print(result.head(10))
    # print(result.columns)
    result = result.loc[:, ~result.columns.str.contains('^Unnamed')]
    # df_prod['date'] = df_prod['date'].dt.date
    dts = df_prod['date'].unique().tolist()
    # print(df_prod['produit'].unique().tolist())
    # print(dts)
    frames = []
    for dt in dts:
        df_sub_prod = df_prod.loc[df_prod['date'] == dt]
        df = result.loc[result['date'] == dt]
        units = df_sub_prod['Unité'].unique().tolist()
        for unit in units:
            df_prod_svg_dt = df_sub_prod
            df_res_svg_dt = df
            df_prod_svg_dt = df_prod_svg_dt.loc[df_prod_svg_dt['Unité'] == unit]
            df_res_svg_dt = df_res_svg_dt.loc[df_res_svg_dt['Unité'] == unit]
            lines = df_prod_svg_dt['Ligne'].unique().tolist()
            # print(lines)
            # print(dt, unit)
            # print(df_prod_svg_dt.shape[0], df_res_svg_dt.shape[0])
            for line in lines:
                df_prod_svg_unit = df_prod_svg_dt
                df_res_svg_unit = df_res_svg_dt
                # df_prod_svg_unit.Ligne = df_prod_svg_unit.Ligne.astype(str)
                # df_res_svg_unit.Ligne = df_res_svg_unit.Ligne.astype(str)
                # print(line)
                df_prod_svg_unit = df_prod_svg_unit.loc[df_prod_svg_unit['Ligne'].str.lower() == line.lower()]
                df_res_svg_unit = df_res_svg_unit.loc[df_res_svg_unit['Ligne'].str.lower() == line.lower()]
                frames.append(df_res_svg_unit)
                if df_prod_svg_unit.shape[0] != df_res_svg_unit.shape[0]:
                    # Cheking the rows we want to adjust in order to start
                    # Start by checking the print result
                    # Adding the last one ( the last one was ommitted due to the drag )
                    # Correct for the non-last ones.
                    # print(df_prod_svg_unit.iloc[-1])
                    if df_prod_svg_unit.shape[0] > df_res_svg_unit.shape[0]:
                        dict = {
                            'Unité': df_prod_svg_unit['Unité'].iloc[-1],
                            'Ligne': df_prod_svg_unit['Ligne'].iloc[-1],
                            'Désignation': df_prod_svg_unit['Désignation'].iloc[-1],
                            'Client': df_prod_svg_unit['Client'].iloc[-1],
                            'PU_coutRev': 0,
                            'montant_journee_coutRev': 0,
                            'MontantCumul_coutRev': 0,
                            'PU_prix_vente': 0,
                            'montant_journee_prix_vente': 0,
                            'MontantCumul_prix_vente': 0,
                        }
                        df_res_svg_unit = df_res_svg_unit.append(dict, ignore_index = True)
                        frames = frames[:-1]
                        frames.append(df_res_svg_unit)
                    else:
                        df_res_svg_unit = pd.DataFrame()
                        print('start loop')
                        for idx, row in df_prod_svg_unit.iterrows():
                            dict = {
                                'Unité': df_prod_svg_unit.loc[idx, 'Unité'],
                                'Ligne': df_prod_svg_unit.loc[idx, 'Ligne'],
                                'Désignation': df_prod_svg_unit.loc[idx, 'Désignation'],
                                'Client': df_prod_svg_unit.loc[idx, 'Client'],
                                'PU_coutRev': 0,
                                'montant_journee_coutRev': 0,
                                'MontantCumul_coutRev': 0,
                                'PU_prix_vente': 0,
                                'montant_journee_prix_vente': 0,
                                'MontantCumul_prix_vente': 0,
                            }
                            df_res_svg_unit = df_res_svg_unit.append(dict, ignore_index = True)
                            frames = frames[:-1]
                            frames.append(df_res_svg_unit)
                        # raise ValueError('Erreur! Les données production/valorisation ne correspondent pas (Date : ' + str(dt) + ', Unité : ' + unit + ', Ligne : ' + line + ')')
                    # print(dt, unit, line, df_prod_svg_unit['Désignation'].iloc[-1])
    result_fin = pd.concat(frames)
    subdf = result_fin.iloc[: , 4:10]
    return subdf
    # result_fin.to_excel('result_fin.xlsx', index = False)
    # print(result_fin.shape)


def get_val_df(df):
    # df = pd.read_excel(file_str, sheet_name='Sheet1')
    # check the data type
    dte = df['Unnamed: 4'][3]
    if isinstance(dte, datetime.datetime):
        date = dte.date()
    else:
        match = re.search(r'\d{2}/\d{2}/\d{4}', dte)
        date = datetime.datetime.strptime(match.group(), '%d/%m/%Y').date()
    df.drop(index=df.index[:4], 
        axis=0, 
        inplace=True)
    df['Unnamed: 0'].fillna(method='ffill', inplace = True)
    df['Unnamed: 1'].fillna(method='ffill', inplace = True)
    df['date'] = date
    # df = pd.read_excel(file_str, sheet_name='Sheet1', skiprows=3).copy()
    # PU_coutRev_Col = df.columns[4]
    # df.columns.values[5] = 'None'
    df.rename(columns = {
        'Unnamed: 0': 'Unité',
        'Unnamed: 1': 'Ligne',
        'Unnamed: 2': 'Désignation',
        'Unnamed: 3': 'Client',
        'Unnamed: 4': 'PU_coutRev',
        'Unnamed: 5': 'montant_journee_coutRev',
        'Unnamed: 6': 'MontantCumul_coutRev',
        'Unnamed: 7': 'PU_prix_vente',
        'Unnamed: 8': 'montant_journee_prix_vente',
        'Unnamed: 9': 'MontantCumul_prix_vente',
    }, inplace = True)
    indexNames = df[(df['Ligne'].str.contains('TOTAL', na = False))].index
    df.drop(indexNames , inplace=True)
    indexNames = df[(df['Client'].str.contains('TOTAL', na = False))].index
    df.drop(indexNames , inplace=True)
    # indexNames = df[df['MontantCumul_coutRev'] == 0].index
    # df.drop(indexNames , inplace=True)
    # df.dropna(subset = ['Désignation'], inplace=True)
    indexNames = df[(df['Désignation'].isnull()) & (df['PU_coutRev'].isnull())].index
    df.drop(indexNames , inplace=True)
    df.loc[df['Unité'].str.contains('1', na = False), 'Unité'] = 'KDU'
    subdf = df.iloc[: , 4:10]
    subdf =  df.iloc[: , :]
    subdf = subdf.replace(['-'],0)
    subdf.fillna(0, inplace=True)
    # print(date)
    # print(df.iloc[:, :10])
    return subdf

file_str = r'C:\Users\zaki1\Desktop\Controle de Gestion\Scripts\PRODUCTION V2\Activité journalière au 19 janvier 2022.xlsx'
prod_file_str = r'C:\Users\zaki1\Desktop\Controle de Gestion\Scripts\Flash_Journ_PROD_PHY_01_2022.xlsx'

if __name__ == '__main__':
    df_prod = pd.read_excel(prod_file_str, sheet_name='Sheet1')
    bg_df = pd.read_excel(file_str, sheet_name='02 Prod Valorisée Boites', skiprows=8, header=1)
    bg_df.columns.values[0] = 'Unnamed: 0'
    bg_df.columns.values[1] = 'Unnamed: 1'
    bg_df.columns.values[2] = 'Unnamed: 2'
    bg_df.columns.values[3] = 'Unnamed: 3'
    # print(bg_df.columns)
    dfs = bg_df.index[bg_df['Unnamed: 0'].str.contains('Unité', na = False)].tolist()
    new_subdf = pd.DataFrame()
    frames = [new_subdf]
    for idx, val in enumerate(dfs):
        df = pd.DataFrame()
        # print(val, dfs[idx+1])
        try:
            df = bg_df.loc[val: dfs[idx+1]]
        except IndexError:
            df = bg_df.loc[val:]
        # df = df.iloc[3: , :]
        df = df.reset_index(drop=True)
        df.drop(df.tail(1).index,inplace=True)
        # print(df.iloc[:, : 8])
        df = get_val_df(df)
        frames.append(df)
        result = pd.concat(frames)


    # print(result)
    # print(result.shape)
    df = pd.DataFrame()
    df = missing_prod_in_val(df_prod, result)
    df = df.reset_index(drop = True)
    df_prod[['PU_cout_revient', 'montant_journee_coutRev', 'MontantCumul_coutRev', 'PU_prix_vente', 'montant_journee_prix_vente', 'MontantCumul_prix_vente']] = df[['PU_coutRev', 'montant_journee_coutRev', 'MontantCumul_coutRev', 'PU_prix_vente', 'montant_journee_prix_vente', 'MontantCumul_prix_vente']]
    print(df_prod.shape)

    # Last reglage : unify strings : Pails 10l => Pails 10 L
    idx = df_prod.index[df_prod['Ligne'].str.startswith('Pails')].tolist()
    for x in idx:
        match = re.search(r'Pails (\d{2})\s*([l|L])', df_prod['Ligne'][x])
        if match:
            df_prod.at[x, 'Ligne'] = 'Pails ' + str(match.group(1)) + ' ' + str(match.group(2)).upper()
    # print(df_prod['Ligne'][df_prod['Ligne'].str.startswith('Pails')])
    # fr = [re.sub(r'Pails \d{2}\s*[l|L]','Pails', str(x)) for x in df_prod['Ligne']]
    month = df_prod['date'].loc[0].month
    df_prod.to_excel('Production_' + str(month) + '_2021.xlsx', index = False)
# print(df.head())

# Comment the fonction section in order to add the ID column

# df.insert(0, 'ID', range(int(max_id) + 1, 1 + int(max_id) + len(df)))
