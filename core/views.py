from django.shortcuts import render, get_object_or_404
from django.views.generic import DetailView, ListView, View
from django.http import HttpRequest, HttpResponse, JsonResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect
from django.db.models import Max, Min, Sum, Q
from django.shortcuts import reverse
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
import datetime
from django.utils import timezone
from django.template.loader import render_to_string
import calendar
from dateutil.relativedelta import relativedelta
from django.views.decorators.csrf import csrf_protect
import pandas as pd
import numpy as np
import json
import re
from django.shortcuts import render
from openpyxl import load_workbook
import dateparser
# pylint: disable=import-error
from django_pandas.io import read_frame
from .models import (
    Production,
    Vente,
    Trs,
    Tcr,
)
from .flasah_test import get_prod_phy
from .prod_val_boites import missing_prod_in_val, get_val_df
from .prod_acc import get_acc_df
from .ventes import get_vente_df
from .trs import get_trs_df
import psycopg2
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker

con = psycopg2.connect(database="EMB", user="postgres", password="zaki1690", host="localhost", port="5432")
con.autocommit = True
engine = create_engine('postgresql://postgres:zaki1690@localhost:5432/EMB')
Session = sessionmaker(bind = engine)
session = Session()
cursor = con.cursor()

# Create your views here.

def home_view(request):
    if not request.user.is_authenticated:
        return redirect('account_login')
    else:
        return redirect(reverse('core:prod-view'))

class prodSummary(LoginRequiredMixin, ListView):
    model = Production
    template_name = 'core/home.html'
    ordering = ['-date', '-unite', '-ligne']
    paginate_by = 40

    def get_queryset(self):
        if self.request.GET.get('date'):
            date = datetime.datetime.strptime(self.request.GET.get('date'), '%Y-%m-%d').date()
        else:
            date = datetime.date.today()
        # pylint: disable=no-member
        qs = Production.objects.filter(date=date)
        # print(qs.count())
        if self.request.GET.get('unit') and self.request.GET.get('unit') != 'all':
            qs = qs.filter(unite = self.request.GET.get('unit').strip())
        if self.request.GET.get('lines') and self.request.GET.get('lines') != 'all':
            qs = qs.filter(ligne__icontains = self.request.GET.get('lines').strip())
        if self.request.GET.get('prod') and self.request.GET.get('prod') != 'all':
            qs = qs.filter(produit__contains = self.request.GET.get('prod').strip())
        return qs

    def get_context_data(self, *args,**kwargs):
        context = super(prodSummary, self).get_context_data(*args, **kwargs)
        # pylint: disable=no-member
        lines = list(Production.objects.values('ligne').distinct().order_by('ligne'))
        context['lines'] = [line['ligne'].upper().strip() if line['ligne'] else line['ligne'] for line in lines]
        context['lines'].remove(None)
        # print(context['lines'])
        lines = context['lines']
        context['lines'] = []
        for line in lines:
            m = re.search(r'(.*\d{1,})([A-Z]+)', line)
            if m:
                context['lines'].append(m.group(1) + ' ' + m.group(2))
            else:
                context['lines'].append(line)
        context['lines'] = list(dict.fromkeys(context['lines']))
        if self.request.GET.get('date'):
            date = datetime.datetime.strptime(self.request.GET.get('date'), '%Y-%m-%d').date()
        else:
            date = datetime.date.today()
        context['date'] = date
        if self.request.GET.get('unit'):
            context['unit'] = self.request.GET.get('unit')
        if self.request.GET.get('lines'):
            context['ligne'] = self.request.GET.get('lines')
        if self.request.GET.get('prod'):
            context['prod'] = self.request.GET.get('prod')
        context['count'] = self.get_queryset().count()
        context['req'] = 'P R O D U C T I O N'
        return context

class prodDetails(LoginRequiredMixin, DetailView):
    model = Production
    template_name = 'core/prod-details.html'

    def get_context_data(self, *args,**kwargs):
        context = super(prodDetails, self).get_context_data(*args, **kwargs)
        # pylint: disable=no-member
        context['obj'] = Production.objects.get(id=self.get_object().pk)
        context['taux_rebut'] = round(context['obj'].taux_rebut * 100, 2)
        context['taux_real'] = round(context['obj'].taux_real * 100, 2)
        context['req'] = 'P R O D U C T I O N'
        return context

class EditProd(View):
    def post(self, request):
        dic = dict(request.POST)
        del dic['csrfmiddlewaretoken']
        dic_values = dic.items()
        for key, value in dic_values:
            try:
                dic[key] = int(value[0].strip())
            except ValueError:
                try:
                    dic[key] = float(value[0].strip())
                except ValueError:
                    try:
                        dic[key] = datetime.datetime.strptime(value[0].strip(), '%Y-%m-%d')
                    except ValueError:
                        dic[key] = value[0].strip()
        # pylint: disable=unused-variable
        # pylint: disable=no-member
        # Get the old object before editing
        # print(dic)
        old_obj = Production.objects.get(id = int(request.POST.get('id')))
        obj, created = Production.objects.update_or_create(
            id = int(request.POST.get('id')),
            defaults = dic
        )
        obj.brute_jour = obj.conforme_jour + obj.rebut_jour
        obj.brute_mois = old_obj.brute_mois - old_obj.brute_jour + (obj.conforme_jour + obj.rebut_jour)
        obj.conforme_mois = old_obj.conforme_mois - old_obj.conforme_jour + obj.conforme_jour
        obj.rebut_mois = old_obj.rebut_mois - old_obj.rebut_jour + obj.rebut_jour
        # MAJ des champs calculé auto
        try:
            obj.taux_jour = obj.brute_jour / obj.capacite_jour
        except ZeroDivisionError:
            obj.taux_jour = 0
        try:
            obj.taux_real = obj.brute_mois / obj.obj
            # print((obj.brute_mois / obj.obj) / 100)
        except ZeroDivisionError:
            obj.taux_real = 0
        try:
            obj.taux_rebut = obj.rebut_mois / obj.brute_mois
        except ZeroDivisionError:
            obj.taux_rebut = 0
        obj.save()
        messages.success(request, 'Modification effectuée avec succès!')
        return HttpResponseRedirect(reverse('core:prod-details', kwargs={
            'pk' : int(request.POST.get('id'))
        }))

class saleSummary(LoginRequiredMixin, ListView):
    model = Vente
    template_name = 'core/salesummary.html'
    ordering = ['-date', '-unite', '-category']
    paginate_by = 40

    def get_queryset(self):
        if self.request.GET.get('date'):
            date = datetime.datetime.strptime(self.request.GET.get('date'), '%Y-%m-%d').date()
        else:
            date = datetime.date.today()
        # pylint: disable=no-member
        qs = Vente.objects.filter(date=date)
        # print(qs.count())
        if self.request.GET.get('unit') and self.request.GET.get('unit') != 'all':
            qs = qs.filter(unite = self.request.GET.get('unit').strip())
        if self.request.GET.get('category') and self.request.GET.get('category') != 'all':
            qs = qs.filter(category__icontains = self.request.GET.get('category').strip())
        return qs

    def get_context_data(self, *args,**kwargs):
        context = super(saleSummary, self).get_context_data(*args, **kwargs)
        # pylint: disable=no-member
        if self.request.GET.get('date'):
            date = datetime.datetime.strptime(self.request.GET.get('date'), '%Y-%m-%d').date()
        else:
            date = datetime.date.today()
        context['date'] = date
        if self.request.GET.get('unit'):
            context['unit'] = self.request.GET.get('unit')
        if self.request.GET.get('category'):
            context['category'] = self.request.GET.get('category')
        context['count'] = self.get_queryset().count()
        context['req'] = 'V E N T E'
        return context

class saleDetails(LoginRequiredMixin, DetailView):
    model = Vente
    template_name = 'core/sale-details.html'

    def get_context_data(self, *args,**kwargs):
        context = super(saleDetails, self).get_context_data(*args, **kwargs)
        # pylint: disable=no-member
        context['obj'] = Vente.objects.get(id=self.get_object().pk)
        context['req'] = 'V E N T E'
        return context

class EditSale(View):
    def post(self, request):
        dic = dict(request.POST)
        del dic['csrfmiddlewaretoken']
        dic_values = dic.items()
        for key, value in dic_values:
            try:
                dic[key] = int(value[0].strip())
            except ValueError:
                try:
                    dic[key] = float(value[0].strip())
                except ValueError:
                    try:
                        dic[key] = datetime.datetime.strptime(value[0].strip(), '%Y-%m-%d')
                    except ValueError:
                        dic[key] = value[0].strip()
        # pylint: disable=unused-variable
        # pylint: disable=no-member
        # Get the old object before editing
        print(dic)
        old_obj = Vente.objects.get(id = int(request.POST.get('id')))
        obj, created = Vente.objects.update_or_create(
            id = int(request.POST.get('id')),
            defaults = dic
        )
        obj.qte_cumul = obj.qte_cumul - old_obj.qte_journ + obj.qte_journ
        obj.montant_cumul = obj.montant_cumul - old_obj.montant_journee + obj.montant_journee
        obj.save()
        messages.success(request, 'Modification effectuée avec succès!')
        return HttpResponseRedirect(reverse('core:sale-details', kwargs={
            'pk' : int(request.POST.get('id'))
        }))

class trsSummary(LoginRequiredMixin, ListView):
    model = Trs
    template_name = 'core/trssummary.html'
    ordering = ['-date', '-unite']
    paginate_by = 40

    def get_queryset(self):
        if self.request.GET.get('date'):
            date = datetime.datetime.strptime(self.request.GET.get('date'), '%Y-%m-%d').date()
        else:
            date = datetime.date.today()
        # pylint: disable=no-member
        qs = Trs.objects.filter(date=date)
        # print(qs.count())
        if self.request.GET.get('unit') and self.request.GET.get('unit') != 'all':
            qs = qs.filter(unite = self.request.GET.get('unit').strip())
        return qs
    
    def get_context_data(self, *args,**kwargs):
        context = super(trsSummary, self).get_context_data(*args, **kwargs)
        # pylint: disable=no-member
        if self.request.GET.get('date'):
            date = datetime.datetime.strptime(self.request.GET.get('date'), '%Y-%m-%d').date()
        else:
            date = datetime.date.today()
        context['date'] = date
        if self.request.GET.get('unit'):
            context['unit'] = self.request.GET.get('unit')
        context['count'] = self.get_queryset().count()
        context['req'] = 'Taux de rendement synthétique'.upper()
        return context

class trsDetails(LoginRequiredMixin, DetailView):
    model = Trs
    template_name = 'core/trs-details.html'

    def get_context_data(self, *args,**kwargs):
        context = super(trsDetails, self).get_context_data(*args, **kwargs)
        # pylint: disable=no-member
        context['obj'] = Trs.objects.get(id=self.get_object().pk)
        context['req'] = 'Taux de rendement synthétique'.upper()
        context['taux_dispo'] = context['obj'].taux_dispo * 100
        context['taux_perf'] = context['obj'].taux_perf * 100
        context['taux_qualit'] = context['obj'].taux_qualit * 100
        context['trs'] = context['obj'].trs * 100
        return context

class EditTrs(View):
    def post(self, request):
        dic = dict(request.POST)
        # print(dic)
        del dic['csrfmiddlewaretoken']
        dic_values = dic.items()
        for key, value in dic_values:
            try:
                dic[key] = int(value[0].strip())
            except ValueError:
                try:
                    dic[key] = float(value[0].strip())
                except ValueError:
                    try:
                        dic[key] = datetime.datetime.strptime(value[0].strip(), '%Y-%m-%d')
                    except ValueError:
                        dic[key] = value[0].strip()
        # pylint: disable=unused-variable
        # pylint: disable=no-member
        # Get the old object before editing
        old_obj = Trs.objects.get(id = int(request.POST.get('id')))
        obj, created = Trs.objects.update_or_create(
            id = int(request.POST.get('id')),
            defaults = dic
        )
        obj.qte_prod = obj.qte_conf + obj.qte_rebut
        obj.ecarts_cadences = obj.arret_non_plan + obj.arret_plan
        obj.temps_req = obj.temps_ouv - obj.arret_plan
        obj.temps_fct = obj.temps_req - obj.arret_non_plan
        obj.taux_dispo = obj.temps_fct / obj.temps_req
        obj.temps_net = obj.temps_fct - obj.ecarts_cadences
        obj.taux_perf = obj.temps_net / obj.temps_fct
        obj.temps_util = obj.temps_net - (obj.temps_ouv - (obj.temps_ouv * obj.qte_conf / obj.qte_prod))
        obj.taux_qualit = obj.temps_util / obj.temps_net
        obj.trs = obj.taux_dispo * obj.taux_perf * obj.taux_qualit
        obj.save()
        messages.success(request, 'Modification effectuée avec succès!')
        return HttpResponseRedirect(reverse('core:trs-details', kwargs={
            'pk' : int(request.POST.get('id'))
        }))

class tcrSummary(LoginRequiredMixin, ListView):
    model = Tcr
    template_name = 'core/tcrsummary.html'

    def get_queryset(self):
        if self.request.GET.get('year') and self.request.GET.get('month'):
            # pylint: disable=no-member
            qs = Tcr.objects.filter(date__year = int(self.request.GET.get('year')), date__month = int(self.request.GET.get('month')))
        else:
            month_bef_date = (datetime.date.today() - datetime.timedelta(days=30))
            # pylint: disable=no-member
            qs = Tcr.objects.filter(date__year = month_bef_date.year, date__month = month_bef_date.month)
        if self.request.GET.get('unit') and self.request.GET.get('unit') != 'all':
            qs = qs.filter(unite = self.request.GET.get('unit').strip())
        df = read_frame(qs)
        # print(df)
        # print(df.T)
        df = df.T
        df = df.iloc[2: , :]
        df['des'] = df.index
        df['des'] = df['des'].str.replace('ca', 'Chiffre d\'affaires')
        df['des'] = df['des'].str.replace('cessions_et_produits', 'Cessions et produits')
        df['des'] = df['des'].str.replace('var_stock_fini_encours', 'Variation stocks produits finis et en cours')
        df['des'] = df['des'].str.replace('prod_immob', 'Production immobilisée')
        df['des'] = df['des'].str.replace('subv_expl', 'Subventions d\'exploitation')
        df['des'] = df['des'].str.replace('prod_exerc', 'PRODUCTION DE L\'EXERCICE (I)')
        df['des'] = df['des'].str.replace('achats_consom', 'Achats consommés')
        df['des'] = df['des'].str.replace('serv_ext_other_consom', 'Services extérieurs et autres consommations')
        df['des'] = df['des'].str.replace('consom_inter_unit', 'Consommation inter-unités')
        df['des'] = df['des'].str.replace('consom_exerc', 'CONSOMMATIONS DE L\'EXERCICE (II)')
        df['des'] = df['des'].str.replace('v_ajoute', 'VALEUR AJOUTÉE (I - II)')
        df['des'] = df['des'].str.replace('charge_pers', 'Charges de personnel')
        df['des'] = df['des'].str.replace('impot_tax_vers_ass', 'Impôts, taxes et versements assimiles')
        df['des'] = df['des'].str.replace('exced_brut_exploit', 'EXCEDENT BRUT D\'EXPLOITATION')
        df['des'] = df['des'].str.replace('other_prod_op', 'Autres produits opérationnels')
        df['des'] = df['des'].str.replace('other_charge_op', 'Autres charges opérationnels')
        df['des'] = df['des'].str.replace('prod_inter_unit', 'Produits inter unités')
        df['des'] = df['des'].str.replace('charge_inter_unit', 'Charges inter unités')
        df['des'] = df['des'].str.replace('dot_amort_prov_pert_val', 'Dotation aux amortissements, provisions et pertes de valeur')
        df['des'] = df['des'].str.replace('repr_pert_val_prov', 'Reprise sur pertes de valeur et provisions')
        df['des'] = df['des'].str.replace('res_op', 'RESULTAT OPERATIONNEL')
        df['des'] = df['des'].str.replace('prod_fin', 'Produits financiers')
        df['des'] = df['des'].str.replace('charge_financ', 'Charges financières')
        df['des'] = df['des'].str.replace('res_financ', 'RESULTAT FINANCIER')
        df['des'] = df['des'].str.replace('res_ord_pre_impot', 'RESULTAT ORDINAIRE AVANT IMPOTS (V + VI)')
        df['des'] = df['des'].str.replace('impot_exig_res_ord', 'Impôts exigibles sur résultats ordinaires')
        df['des'] = df['des'].str.replace('impot_diff_res_ord', 'Impôts différés (Variations) sur résultats ordinaires')
        df['des'] = df['des'].str.replace('tot_prod_act_ord', 'Total des produits des activités ordinaires')
        df['des'] = df['des'].str.replace('tot_charge_act_ord', 'Total des charges des activités ordinaires')
        df['des'] = df['des'].str.replace('res_net_act_ord', 'RESULTAT NET DES ACTIVITES ORDINAIRES')
        df['des'] = df['des'].str.replace('elem_extraord_prod', 'Eléments extraordinaires produits')
        df['des'] = df['des'].str.replace('elem_extraord_charge', 'Eléments extraordinaires charges')
        df['des'] = df['des'].str.replace('res_extraord', 'RESULTAT EXTRAORDINAIRE')
        df['des'] = df['des'].str.replace('res_net_exerc', 'RESULTAT NET DE L\'EXERCICE')
        # print(df)
        return df
    
    def get_context_data(self, *args,**kwargs):
        context = super(tcrSummary, self).get_context_data(*args, **kwargs)
        if self.request.GET.get('year') and self.request.GET.get('month'):
            month = int(self.request.GET.get('month'))
            year = int(self.request.GET.get('year'))
        else:
            month_bef_date = (datetime.date.today() - datetime.timedelta(days=30))
            year = month_bef_date.year
            month = month_bef_date.month
        # pylint: disable=no-member
        max_year = Tcr.objects.latest('date').date.year
        min_year = Tcr.objects.earliest('date').date.year
        context['years'] = [year for year in range(min_year, max_year + 1)]
        context['Year'] = year
        context['Month'] = month
        if self.request.GET.get('unit') and self.request.GET.get('unit') != 'all':
            context['unit'] = self.request.GET.get('unit')
        context['req'] = 'TCR - '.upper() + datetime.date(year, month, 28).strftime('%B') + ' ' + datetime.date(year, month, 28).strftime('%Y')
        context['qs'] = self.get_queryset()
        return context

def add_act_journ(request):
    context = {
        'title' : "ACtivité journalière".upper(),
        'req' : "ACtivité journalière".upper(),
    }
    return render(request, 'core/add_act_journ.html', context)

class AddAct(View):
    def post(self, request):
        if request.FILES['file_pg']:
            myfile = request.FILES['file_pg']
            fs = FileSystemStorage()
            filename = fs.save(myfile.name, myfile)
            uploaded_file_path = fs.path(filename)
            new_act_journ = uploaded_file_path

            try:
                # Order of exec

                # Acc --> Prod. Phy. --> Prod. Valorisé --> Merge

                tab_name = 'Production'

                cursor.execute('SELECT MAX("date") FROM public."' + tab_name + '"')
                max_dt = cursor.fetchone()[0]
                # print(max_dt)
                # max_dt = datetime.date(2022, 1, 16)

                # ACC
                bg_df = pd.read_excel(new_act_journ, sheet_name='03 Prod Accessoires', skiprows=8, header=1)
                # Rename the first column so we could address it
                bg_df.columns.values[0] = 'Unnamed: 0'
                bg_df.columns.values[1] = 'Unnamed: 1'
                bg_df.columns.values[2] = 'Unnamed: 2'
                pd.set_option('display.max_rows', None)
                # # Delimiter les dataframes
                dfs = bg_df.index[bg_df['Unnamed: 0'].str.contains('Unité', na = False)].tolist()
                frames = []
                for idx, val in enumerate(dfs):
                    # print(idx, val)
                    df = pd.DataFrame()
                    # print(val, dfs[idx+1])
                    try:
                        df = bg_df.loc[val: dfs[idx+1]]
                    except IndexError:
                        df = bg_df.loc[val:]
                    df = df.reset_index(drop=True)
                    dte = df['Unnamed: 5'][1]
                    # print(dte)
                    if isinstance(dte, datetime.datetime):
                        date = dte.date()
                    else:
                        match = re.search(r'\d{2}/\d{2}/\d{4}', dte)
                        date = datetime.datetime.strptime(match.group(), '%d/%m/%Y').date()
                    # print(date)
                    if date > max_dt:
                        # print(date)
                        # df = df.iloc[3: , :]
                        df.drop(df.tail(1).index,inplace=True)
                        # break
                        acc_df = get_acc_df(df)
                        frames.append(acc_df)
                        result = pd.concat(frames)
                        # print(acc_df)

                acc_df = result
                # PROD PHY
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
                        match = re.search(r'\d{2}/\d{2}/\d{4}', dte)
                        date = datetime.datetime.strptime(match.group(), '%d/%m/%Y').date()
                    # print(date)
                    if date > max_dt:
                        df.drop(df.tail(1).index,inplace=True)
                        # print(df.iloc[:, : 8])
                        # print('Done')
                        # if last line, then remove last meaningless lines
                        # if val == dfs[-1]:
                        # print(date)
                        df_prod = get_prod_phy(df)
                        frames.append(df_prod)
                        result = pd.concat(frames)
                        # print(df_prod)

                
                df_prod = result
                # PROD VAL
                bg_df = pd.read_excel(new_act_journ, sheet_name='02 Prod Valorisée Boites', skiprows=8, header=1)
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
                    # print(df['Unnamed: 4'][3])
                    # break
                    dte = df['Unnamed: 4'].values[3]
                    # print(dte)
                    if isinstance(dte, datetime.datetime):
                        date = dte.date()
                    else:
                        match = re.search(r'\d{2}/\d{2}/\d{4}', dte)
                        date = datetime.datetime.strptime(match.group(), '%d/%m/%Y').date()
                    if date > max_dt:
                        df = df.reset_index(drop=True)
                        df.drop(df.tail(1).index,inplace=True)
                        # print(df.iloc[:, : 8])
                        df = get_val_df(df)
                        frames.append(df)
                        result = pd.concat(frames)
                        # print(result)


                # print(result)
                # print(result.shape)
                df = pd.DataFrame()
                df = missing_prod_in_val(df_prod, result)
                df = df.reset_index(drop = True)
                df_prod[['PU_cout_revient', 'montant_journee_coutRev', 'MontantCumul_coutRev', 'PU_prix_vente', 'montant_journee_prix_vente', 'MontantCumul_prix_vente']] = df[['PU_coutRev', 'montant_journee_coutRev', 'MontantCumul_coutRev', 'PU_prix_vente', 'montant_journee_prix_vente', 'MontantCumul_prix_vente']]
                df_prod = df_prod.reset_index(drop=True)

                print(df_prod.loc[df_prod['Ligne'].str.contains('Pails')])
                # Last reglage : unify strings : Pails 10l => Pails 10 L
                idx = df_prod.index[df_prod['Ligne'].str.startswith('Pails')].tolist()
                for x in idx:
                    print(df_prod.at[x, 'Ligne'])
                    match = re.search(r'Pails (\d{2})\s*([l|L])', df_prod['Ligne'][x])
                    if match:
                        df_prod.at[x, 'Ligne'] = 'Pails ' + str(match.group(1)) + ' ' + str(match.group(2)).upper()
                    # print('loop idx')


                # # MERGE ACC and PROD

                acc_df.rename(columns = {
                    'PU_coutRev': 'PU_cout_revient'
                }, inplace = True)
                df_prod = pd.concat([df_prod, acc_df], ignore_index=True)

                tab_name = 'Production'
                if tab_name != 'TCR':
                    cursor.execute('SELECT MAX("ID") FROM public."' + tab_name + '"')
                    max_id = cursor.fetchone()[0]
                    df_prod.insert(0, 'ID', range(int(max_id) + 1, 1 + int(max_id) + len(df_prod)))
                df_prod.to_sql(tab_name, engine, if_exists='append', index=False)

                # df_prod['date'] = df_prod['date'].dt.date
                # print(df_prod)
                print(df_prod.shape)


                # Vente

                tab_name = 'Vente'

                cursor.execute('SELECT MAX("date") FROM public."' + tab_name + '"')
                max_dt = cursor.fetchone()[0]
                print(max_dt)

                bg_df = pd.read_excel(new_act_journ, sheet_name='04 Ventes', skiprows=8, header=1)
                bg_df.columns.values[0] = 'Unnamed: 0'
                bg_df.columns.values[1] = 'Unnamed: 1'
                bg_df.columns.values[2] = 'Unnamed: 2'
                bg_df.columns.values[3] = 'Unnamed: 3'
                dfs = bg_df.index[bg_df['Unnamed: 0'].str.contains('Unité', na = False)].tolist()
                for idx, val in enumerate(dfs):
                    df = pd.DataFrame()
                    try:
                        df = bg_df.loc[val: dfs[idx+1]]
                    except IndexError:
                        df = bg_df.loc[val:]
                    dte = df['Unnamed: 4'].values[0]
                    if isinstance(dte, datetime.datetime):
                        date = dte.date()
                    else:
                        match = re.search(r'\d{2}/\d{2}/\d{4}', dte)
                        date = datetime.datetime.strptime(match.group(), '%d/%m/%Y').date()
                    if date > max_dt:
                        df = df.reset_index(drop=True)
                        df = get_vente_df(df)
                        if tab_name != 'TCR':
                            cursor.execute('SELECT MAX("ID") FROM public."' + tab_name + '"')
                            max_id = cursor.fetchone()[0]
                            df.insert(0, 'ID', range(int(max_id) + 1, 1 + int(max_id) + len(df)))
                        df.to_sql(tab_name, engine, if_exists='append', index=False)
                        # print(df)


                # TRS

                tab_name = 'TRS'

                cursor.execute('SELECT MAX("date") FROM public."' + tab_name + '"')
                max_dt = cursor.fetchone()[0]
                print(max_dt)


                bg_df = pd.read_excel(new_act_journ, sheet_name='06 TRS', skiprows=8, header=1)
                bg_df.columns.values[0] = 'Unnamed: 0'
                bg_df.columns.values[1] = 'Unnamed: 1'
                dfs = bg_df.index[bg_df['Unnamed: 0'].str.contains('Unité', na = False)].tolist()
                for idx, val in enumerate(dfs):
                    df = pd.DataFrame()
                    try:
                        df = bg_df.loc[val: dfs[idx+1]]
                    except IndexError:
                        df = bg_df.loc[val:]
                    dte = df['Unnamed: 5'].values[0]
                    if isinstance(dte, datetime.datetime):
                        date = dte.date()
                    else:
                        match = re.search(r'\d{2}/\d{2}/\d{4}', dte)
                        date = datetime.datetime.strptime(match.group(), '%d/%m/%Y').date()
                    if date > max_dt:
                        df = df.reset_index(drop=True)
                        df = get_trs_df(df)
                        if tab_name != 'TCR':
                            cursor.execute('SELECT MAX("ID") FROM public."' + tab_name + '"')
                            max_id = cursor.fetchone()[0]
                            df.insert(0, 'ID', range(int(max_id) + 1, 1 + int(max_id) + len(df)))
                        df.to_sql(tab_name, engine, if_exists='append', index=False)
            except (KeyError, pd.errors.ParserError):
                messages.error(request, "Erreur ! Noms de feuilles Excel erronés, ou bien la structure du fichier ( d'un tableau ) a été modifiée.")
                return redirect('core:add-act-journ')
            except UnboundLocalError:
                messages.error(request, "Erreur ! Les données des dates concernées ont déjà été chargées.")
                return redirect('core:add-act-journ')
        messages.success(request, "Le données ont été stockés avec succès !")
        return redirect('core:add-act-journ')

def add_tcr(request):
    context = {
        'title' : "Nouveau TCR".upper(),
        'req' : "Nouveau TCR".upper(),
    }
    return render(request, 'core/add_tcr.html', context)


class AddTcr(View):
    def post(self, request):
        if request.FILES['file_pg']:
            myfile = request.FILES['file_pg']
            fs = FileSystemStorage()
            filename = fs.save(myfile.name, myfile)
            uploaded_file_path = fs.path(filename)
            file_str = uploaded_file_path
            book = load_workbook(file_str)
            tab_name = 'TCR'
            cursor.execute('SELECT MAX("date") FROM public."' + tab_name + '"')
            max_dt = cursor.fetchone()[0]
            xl = pd.ExcelFile(file_str, engine='openpyxl') # pylint: disable=abstract-class-instantiated
            no_error = True
            try:
                for sheetname in xl.sheet_names:
                    if re.match("^[0-9 ]+$", sheetname):
                        # print(sheetname)
                        df = pd.read_excel(file_str, sheet_name=sheetname, header=1)
                        # print(df)
                        period = df['Unnamed: 0'][2]
                        match = re.search(r'\w*\s(\w+)-(\d{4})', period)
                        month = dateparser.parse(match.group(1)).month
                        year = dateparser.parse(match.group(2)).year
                        if datetime.date(year, month, 28) > max_dt.date():
                            no_error = False
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
                            df.reset_index(level=0, inplace=True)
                            df.rename(columns={ df.columns[0]: "Unité" }, inplace = True)
                            df.insert(0, 'ID', '')
                            df['ID'] = df.apply (lambda row: row['Unité'] + '_' + str(row['date'].month) + '_' + str(row['date'].year), axis=1)
                            df.to_sql(tab_name, engine, if_exists='append', index=False)
                if no_error:
                    raise UnboundLocalError('Data already processed.')
            except (KeyError, pd.errors.ParserError):
                messages.error(request, "Erreur ! Noms de feuilles Excel erronés, ou bien la structure du fichier ( d'un tableau ) a été modifiée.")
                return redirect('core:add-tcr')
            except UnboundLocalError:
                messages.error(request, "Erreur ! Les données des dates concernées ont déjà été chargées.")
                return redirect('core:add-tcr')
            messages.success(request, "Le données ont été stockés avec succès !")
            return redirect('core:add-tcr')
                    
