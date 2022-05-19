import calendar
import datetime
import imp
import os
import re
import sys
import traceback
from difflib import SequenceMatcher

import dateparser
import numpy as np
import pandas as pd
import psycopg2
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.db.models import Max, Sum
from django.http import (HttpResponseRedirect,
                         JsonResponse)
from django.shortcuts import redirect, render, reverse
from django.views.generic import DetailView, ListView, View
# pylint: disable=import-error
from django_pandas.io import read_frame
from sqlalchemy import create_engine, false, true
from sqlalchemy.orm import sessionmaker

from .flasah_test import get_prod_phy
from .models import (AuditLog, 
Flash_Impression, 
ObjectifCapaciteProduction,
Production,
Production_Capacite_Imp,
Tcr,
Trs,
Vente, do_something_if_changed
)
from .prod_acc import get_acc_df
from .prod_val_boites import get_val_df, missing_prod_in_val
from .trs import get_trs_df
from .ventes import get_vente_df


def similar(a, b):
    a_digit_seq = []
    b_digit_seq = []
    if (a is None) ^ (b is None):
        return 0, False 
    for c in a:
        if c.isdigit():
            a_digit_seq.append(c)
    for c in b:
        if c.isdigit():
            b_digit_seq.append(c)
    return SequenceMatcher(None, a, b).ratio(), a_digit_seq == b_digit_seq

# CALCULATED FIELDS FOR DIFF TABS
calc_fields_prod = ['brute_jour', 'taux_jour', 'brute_mois', 'conforme_mois', 'rebut_mois', 'taux_real', 'taux_rebut', 'montant_journee_coutrev', 'montantcumul_coutrev', 'montant_journee_prix_vente', 'montantcumul_prix_vente']
no_calc_fields_trs = ['id', 'unite', 'ligne', 'arret_plan', 'arret_non_plan', 'capacite_theo', 'qte_conf', 'qte_rebut', 'temps_ouv', 'date']
calc_fields_sale = ['qte_cumul', 'montant_journee', 'montant_cumul']
calc_fields_tcr = ['prod_exerc', 'consom_exerc', 'v_ajoute', 'exced_brut_exploit', 'res_financ', 'res_ord_pre_impot', 'tot_prod_act_ord', 'tot_charge_act_ord', 'res_net_act_ord', 'res_extraord', 'res_net_exerc']
full_labels = ['prep_line',
'pause_eat',
'chg_form',
'lvg',
'manque_prog',
'panne',
'reglages',
'autres',
'abs']

# FIELDS PRETTY NAMING
pretty_naming = {
    'id': 'ID',
    'unite': 'Unité',
    'ligne': 'Ligne',
    'des': 'Désignation',
    'client': 'Client',
    'obj': 'Objectif',
    'capacite_jour': 'Capacité Jout',
    'conforme_jour': 'Conforme Jour',
    'rebut_jour': 'Rebut Jour',
    'pu_cout_revient': 'PU - Avec coût de revient',
    'pu_prix_vente': 'PU - Avec prix de vente',
    'date': 'Date',
    'volume': 'Volume',
    'category': 'Catégorie',
    'produit': 'Produit',
    'arret_plan': 'Arrêts planifiés (Minutes)',
    'arret_non_plan': 'Arrêts non planifiés (Minutes)',
    'capacite_theo': 'Capacité théorique',
    'qte_conf': 'Quantité conforme',
    'qte_rebut': 'Quantité rebutée',
    'temps_ouv': 'Temps d\'ouverture',
    'qte_journ': 'Quantité journalière',
    'pu' : 'Prix Unitaire',
    'ca': 'Chiffre d\'affaire',
    'cessions_et_produits': 'Cessions et produits',
    'var_stock_fini_encours': 'Variations stocks produits finis et en cours',
    'prod_immob': 'Production immobilisée',
    'subv_expl': 'Subvention d\'exploitation',
    'achats_consom': 'Achats consommés',
    'serv_ext_other_consom': 'Service exterieurs et autres consommations',
    'consom_inter_unit': 'Consommation inter-unités',
    'charge_pers': 'Charges du personnel',
    'impot_tax_vers_ass': 'Impôts, taxes et versements assimilés',
    'other_prod_op': 'Autres produits opérationnels',
    'other_charge_op': 'Autres charges opérationnels',
    'prod_inter_unit': 'Produits inter-unité',
    'charge_inter_unit': 'Charges inter-unité',
    'dot_amort_prov_pert_val': 'Dotation aux amortissement, provisions et pertes de valeur',
    'repr_pert_val_prov': 'Reprise sur perte de valeurs',
    'prod_fin': 'Produits financiers',
    'charge_financ': 'Charges financiers',
    'impot_exig_res_ord': 'Impôts exigibles sur résultats ordinaire',
    'impot_diff_res_ord': 'Impôts différés sur résultats ordinaire',
    'elem_extraord_prod': 'Eléments extraordinaire produits',
    'elem_extraord_charges': 'Eléments extraordinaire charges',
}

con = psycopg2.connect(database=settings.DB, user=settings.DB_USER, password=settings.DB_PASSWORD, host=settings.DB_HOST, port=settings.DB_PORT)
con.autocommit = True
engine = create_engine(f'postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB}')
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
        context['Year'] = date.year
        context['Month'] = date.month
        if self.request.GET.get('unit'):
            context['unit'] = self.request.GET.get('unit')
        if self.request.GET.get('lines'):
            context['ligne'] = self.request.GET.get('lines')
        if self.request.GET.get('prod'):
            context['prod'] = self.request.GET.get('prod')
        context['count'] = self.get_queryset().count()
        context['req'] = 'PRODUCTION'
        if context['count'] == 0:
            context['empty_qs'] = False
        else:
            context['empty_qs'] = True
        context['max_dt_prod'] = Production.objects.latest('date').date
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
        context['req'] = 'PRODUCTION'
        context['cat_list'] = Vente.objects.values_list('category', flat=True).distinct().order_by('category')
        context['title'] = 'Détails de production'
        return context

class EditProd(LoginRequiredMixin, View):
    def post(self, request):
        dic = dict(request.POST)
        # print(request.POST)
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
                        dic[key] = datetime.datetime.strptime(value[0].strip(), '%Y-%m-%d').date()
                    except ValueError:
                        dic[key] = value[0].strip()
        # pylint: disable=unused-variable
        # pylint: disable=no-member
        # Get the old object before editing
        old_obj = Production.objects.get(id = int(request.POST.get('id')))
        dic['brute_jour'] = dic['conforme_jour'] + dic['rebut_jour']
        dic['brute_mois'] = old_obj.brute_mois - old_obj.brute_jour + (dic['conforme_jour'] + dic['rebut_jour'])
        dic['conforme_mois'] = old_obj.conforme_mois - old_obj.conforme_jour + dic['conforme_jour']
        dic['rebut_mois'] = old_obj.rebut_mois - old_obj.rebut_jour + dic['rebut_jour']
        # MAJ des champs calculé auto
        try:
            dic['taux_jour'] = dic['brute_jour'] / dic['capacite_jour']
        except ZeroDivisionError:
            dic['taux_jour'] = 0
        try:
            dic['taux_real'] = dic['brute_mois'] / dic['obj']
            # print((dic['brute_mois'] / dic['obj']) / 100)
        except ZeroDivisionError:
            dic['taux_real'] = 0
        try:
            dic['taux_rebut'] = dic['rebut_mois'] / dic['brute_mois']
        except ZeroDivisionError:
            dic['taux_rebut'] = 0
        # print(dic)
        obj, created = Production.objects.update_or_create(
            id = int(request.POST.get('id')),
            defaults = dic
        )
        # print('save 2')
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
        context['req'] = 'VENTE'
        context['Year'] = date.year
        context['Month'] = date.month
        if context['count'] == 0:
            context['empty_qs'] = False
        else:
            context['empty_qs'] = True
        context['max_dt_prod'] = Vente.objects.latest('date').date
        return context

class saleDetails(LoginRequiredMixin, DetailView):
    model = Vente
    template_name = 'core/sale-details.html'

    def get_context_data(self, *args,**kwargs):
        context = super(saleDetails, self).get_context_data(*args, **kwargs)
        # pylint: disable=no-member
        context['obj'] = Vente.objects.get(id=self.get_object().pk)
        context['req'] = 'VENTE'
        context['title'] = 'VENTE'
        context['cat_list'] = Vente.objects.values_list('category', flat=True).distinct().order_by('category')
        return context

class EditSale(LoginRequiredMixin, View):
    def post(self, request):
        # print(request.POST)
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
        old_obj = Vente.objects.get(id = int(request.POST.get('id')))
        dic['qte_cumul'] = dic['qte_cumul'] - old_obj.qte_journ + dic['qte_journ']
        dic['montant_journee'] = dic['qte_journ'] * dic['pu']
        dic['montant_cumul'] = dic['montant_cumul'] - old_obj.montant_journee + dic['montant_journee']
        obj, created = Vente.objects.update_or_create(
            id = int(request.POST.get('id')),
            defaults = dic
        )
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
        context['Year'] = date.year
        context['Month'] = date.month
        if self.request.GET.get('unit'):
            context['unit'] = self.request.GET.get('unit')
        context['count'] = self.get_queryset().count()
        context['req'] = 'Taux de rendement synthétique'.upper()
        if context['count'] == 0:
            context['empty_qs'] = False
        else:
            context['empty_qs'] = True
        context['max_dt_prod'] = Trs.objects.latest('date').date
        return context

class trsDetails(LoginRequiredMixin, DetailView):
    model = Trs
    template_name = 'core/trs-details.html'

    def get_context_data(self, *args,**kwargs):
        context = super(trsDetails, self).get_context_data(*args, **kwargs)
        # pylint: disable=no-member
        context['obj'] = Trs.objects.get(id=self.get_object().pk)
        context['req'] = 'Taux de rendement synthétique'.upper()
        context['title'] = 'Taux de rendement synthétique'.upper()
        context['taux_dispo'] = context['obj'].taux_dispo * 100
        context['taux_perf'] = context['obj'].taux_perf * 100
        context['taux_qualit'] = context['obj'].taux_qualit * 100
        context['trs'] = context['obj'].trs * 100
        return context

class EditTrs(LoginRequiredMixin, View):
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
        dic['qte_prod'] = dic['qte_conf'] + dic['qte_rebut']
        dic['ecarts_cadences'] = dic['arret_non_plan'] + dic['arret_plan']
        dic['temps_req'] = dic['temps_ouv'] - dic['arret_plan']
        dic['temps_fct'] = dic['temps_req'] - dic['arret_non_plan']
        dic['taux_dispo'] = dic['temps_fct'] / dic['temps_req']
        dic['temps_net'] = dic['temps_fct'] - dic['ecarts_cadences']
        dic['taux_perf'] = dic['temps_net'] / dic['temps_fct']
        dic['temps_util'] = dic['temps_net'] - (dic['temps_ouv'] - (dic['temps_ouv'] * dic['qte_conf'] / dic['qte_prod']))
        dic['taux_qualit'] = dic['temps_util'] / dic['temps_net']
        dic['trs'] = dic['taux_dispo'] * dic['taux_perf'] * dic['taux_qualit']
        obj, created = Trs.objects.update_or_create(
            id = int(request.POST.get('id')),
            defaults = dic
        )        
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
            month_bef_date = (datetime.date.today() - datetime.timedelta(days=31))
            # pylint: disable=no-member
            qs = Tcr.objects.filter(date__year = month_bef_date.year, date__month = month_bef_date.month)
        if self.request.GET.get('unit') and self.request.GET.get('unit') != 'all':
            qs = qs.filter(unite = self.request.GET.get('unit').strip())
        df = read_frame(qs)
        # print(df)
        # print(df.T)
        df = df.T
        df.columns = df.loc['unite']
        df = df.iloc[2: , :]
        # print(df.head())
        if not df.empty and len(df.columns) > 1:
            cols = ['SIEGE', 'KDU', 'SKDU', 'AZDU', 'ENTREPRISE']
            df = df[cols]
        # print(df.head())
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
        # df = df[[4, 3, 2, 1, 0, 'des']]
        return df
    
    def get_context_data(self, *args,**kwargs):
        context = super(tcrSummary, self).get_context_data(*args, **kwargs)
        if self.request.GET.get('year') and self.request.GET.get('month'):
            month = int(self.request.GET.get('month'))
            year = int(self.request.GET.get('year'))
        else:
            month_bef_date = (datetime.date.today() - datetime.timedelta(days=31))
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
        context['req'] = 'TCR - '.upper() + datetime.date(year, month, 28).strftime('%B').upper() + ' ' + datetime.date(year, month, 28).strftime('%Y')
        context['qs'] = self.get_queryset()
        context['count'] = context['qs'].shape[1]
        if context['count'] == 1:
            context['empty_qs'] = False
        else:
            context['empty_qs'] = True
        return context

@login_required
def add_act_journ(request):
    context = {
        'title' : "ACtivité journalière".upper(),
        'req' : "ACtivité journalière".upper(),
    }
    return render(request, 'core/add_act_journ.html', context)

def safe_float_convert(x):
    try:
        float(x)
        return True # numeric, success!
    except ValueError:
        return False # not numeric
    except TypeError:
        return False # null type

class AddAct(LoginRequiredMixin, View):
    def post(self, request):
        if request.FILES['file_pg']:
            myfile = request.FILES['file_pg']
            fs = FileSystemStorage()
            filename = fs.save(myfile.name, myfile)
            uploaded_file_path = fs.path(filename)
            new_act_journ = uploaded_file_path
            month_crn = 0
            year_crn = 0
            if 'edit-tcr-month' in request.POST:
                month_crn = int(request.POST['edit-tcr-month'])
                year_crn = int(request.POST['edit-tcr-year'])
                dte = datetime.date(year_crn, month_crn, 28)

                # First check if le mois et l'année concerné match avec le mois et l'année concerné dans le nv fichier act journ
                bg_df = pd.read_excel(new_act_journ, sheet_name='03 Prod Accessoires', skiprows=8, header=1)
                bg_df.columns.values[0] = 'Unnamed: 0'
                bg_df.columns.values[1] = 'Unnamed: 1'
                bg_df.columns.values[2] = 'Unnamed: 2'
                dfs = bg_df.index[bg_df['Unnamed: 0'].str.contains('Unité', na = False)].tolist()
                for idx, val in enumerate(dfs):
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
                        match = re.search(r'\d{2}\s*/\d{2}\s*/\d{4}', dte)
                        date = datetime.datetime.strptime(match.group(), '%d/%m/%Y').date()
                    break
                if month_crn != date.month or year_crn != date.year:
                    messages.error(request, "Vous avez choisi de modifier l'activité du mois de " + str(calendar.month_name[month_crn]) + " " + str(year_crn) + ". Or, le fichier d'activité mentionné concerne " + str(calendar.month_name[date.month]) + " " + str(date.year) + ".")
                    return redirect('core:prod-view')

                # pylint: disable=no-member
                # print(Production.objects.filter(date__year = year_crn, date__month = month_crn).count())
                # print(year_crn, month_crn)
                Production.objects.filter(date__year = year_crn, date__month = month_crn).delete()
                Vente.objects.filter(date__year = year_crn, date__month = month_crn).delete()
                Trs.objects.filter(date__year = year_crn, date__month = month_crn).delete()
            

            try:
                # Order of exec

                # Acc --> Prod. Phy. --> Prod. Valorisé --> Merge

                tab_name = 'Production'

                cursor.execute('SELECT MAX("date") FROM public."' + tab_name + '"')
                max_dt = cursor.fetchone()[0]
                dst_dates = list(Production.objects.values_list('date', flat=True).distinct().order_by('-date'))
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
                        match = re.search(r'\d{2}\s*/\d{2}\s*/\d{4}', dte)
                        date = datetime.datetime.strptime(match.group(), '%d/%m/%Y').date()
                    # print(date)
                    if date > max_dt:
                        # print(date)
                        # df = df.iloc[3: , :]
                        df.drop(df.tail(1).index,inplace=True)
                        # break
                        acc_df, obj_cap_acc_df = get_acc_df(df)
                        indexNames = acc_df[acc_df['Conforme_mois'] == 0].index
                        acc_df.drop(indexNames , inplace=True)
                        acc_df.loc[~acc_df['Unité'].str.lower().str.contains('kdu|skdu|azdu', na = False), 'Unité'] = np.nan
                        acc_df['Unité'].fillna(method='ffill', inplace = True)
                        print(acc_df[['Unité', 'Désignation', 'Brute_mois', 'Conforme_mois', 'date', 'category', 'produit']])
                        

                       
                        # OBJECTIF AND CAPACITE PART
                        tab_name = 'OBJ_CAP_PRODUCTION'
                        # REPLACE THE OBJ AND CAPACITE FOR THE CURRENT MONTH
                        # pylint: disable=no-member
                        ObjectifCapaciteProduction.objects.filter(produit='Accessoire', date__year = date.year, date__month = date.month).delete()

                        cursor.execute('SELECT MAX("ID") FROM public."' + tab_name + '"')
                        max_id = cursor.fetchone()[0]
                        if not max_id:
                            max_id = 0
                        obj_cap_acc_df = obj_cap_acc_df[['Unité', 'Objectif', 'Capacité jour', 'date', 'Volume', 'category', 'produit']]
                        obj_cap_acc_df.insert(0, 'ID', range(int(max_id) + 1, 1 + int(max_id) + len(obj_cap_acc_df)))
                        # obj_cap_acc_df['Ligne'] = obj_cap_acc_df['Ligne'].str.upper().str.strip()
                        obj_cap_acc_df.to_sql(tab_name, engine, if_exists='append', index=False)
                        idx_line_num = acc_df['Ligne'].map(safe_float_convert)
                        acc_df.loc[idx_line_num, 'Ligne'] = np.nan
                        acc_df['Ligne'].fillna(method='ffill', inplace = True)
                        acc_df['Ligne'] = acc_df['Ligne'].str.upper().str.strip()
                        pails_idx = acc_df.index[~acc_df['Ligne'].isnull()].tolist()
                        # print(pails_idx)
                        for x in pails_idx:
                            # print(acc_df['Ligne'][x])
                            match = re.search(r'(\w+)\s*(\d{1,2})\s*(L|OZ)', acc_df['Ligne'][x])
                            if match:
                                acc_df.at[x, 'Ligne'] = str(match.group(1)) + ' ' + str(match.group(2)) + ' ' + str(match.group(3)).upper()
                            match = re.search(r'(\w+)\s*Ø\s*(\d+)', acc_df['Ligne'][x])
                            if match:
                                acc_df.at[x, 'Ligne'] = str(match.group(1)) + ' Ø ' + str(match.group(2))

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
                        match = re.search(r'\d{2}\s*/\d{2}\s*/\d{4}', dte)
                        date = datetime.datetime.strptime(match.group(), '%d/%m/%Y').date()
                    # print(date)
                    if date > max_dt:
                        df.drop(df.tail(1).index,inplace=True)
                        # print(df.iloc[:, : 8])
                        # print('Done')
                        # if last line, then remove last meaningless lines
                        # if val == dfs[-1]:
                        # print(date)
                        df_prod, obj_cap_prod_df = get_prod_phy(df)
                        # indexNames = df_prod[df_prod['Brute_mois'] == 0].index
                        # df_prod.drop(indexNames , inplace=True)

                        # OBJECTIF AND CAPACITE PART
                        tab_name = 'OBJ_CAP_PRODUCTION'
                        # REPLACE THE OBJ AND CAPACITE FOR THE CURRENT MONTH
                        # pylint: disable=no-member
                        ObjectifCapaciteProduction.objects.filter(produit='Boite', date__year = date.year, date__month = date.month).delete()
                        obj_cap_prod_df = obj_cap_prod_df[['Unité', 'Objectif', 'Capacité jour', 'date', 'Volume', 'category', 'produit']]
                        cursor.execute('SELECT MAX("ID") FROM public."' + tab_name + '"')
                        max_id = cursor.fetchone()[0]
                        if not max_id:
                            max_id = 0
                        obj_cap_prod_df.insert(0, 'ID', range(int(max_id) + 1, 1 + int(max_id) + len(obj_cap_prod_df)))
                        obj_cap_prod_df.to_sql(tab_name, engine, if_exists='append', index=False)
                        
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
                        match = re.search(r'\d{2}\s*/\d{2}\s*/\d{4}', dte)
                        date = datetime.datetime.strptime(match.group(), '%d/%m/%Y').date()
                    if date > max_dt:
                        df = df.reset_index(drop=True)
                        df.drop(df.tail(1).index,inplace=True)
                        # print(df.iloc[:, : 8])
                        df = get_val_df(df)
                        frames.append(df)
                        result = pd.concat(frames)
                        # print(result)


                idx = (result['Unité'] != 'KDU') & (result['Unité'] != 'AZDU') & (result['Unité'] != 'SKDU')
                # print(idx)
                result.loc[idx, 'Unité'] = 'KDU'
                # print(result)
                # print(result.shape)
                df = pd.DataFrame()
                # print(df_prod)
                df = missing_prod_in_val(df_prod, result)
                df = df.reset_index(drop = True)
                # print(df)
                df_prod = df_prod.reset_index(drop=True)
                df_prod[['PU_cout_revient', 'montant_journee_coutRev', 'MontantCumul_coutRev', 'PU_prix_vente', 'montant_journee_prix_vente', 'MontantCumul_prix_vente']] = df[['PU_coutRev', 'montant_journee_coutRev', 'MontantCumul_coutRev', 'PU_prix_vente', 'montant_journee_prix_vente', 'MontantCumul_prix_vente']]

                df_prod['Ligne'] = df_prod['Ligne'].str.upper().str.strip()

                pails_idx = df_prod.index.tolist()
                # print(pails_idx)
                for x in pails_idx:
                    # print(df_prod.at[x, 'Ligne'])
                    match = re.search(r'(\w+)\s*(\d{1,2})\s*(L|OZ)', df_prod['Ligne'][x])
                    if match:
                        df_prod.at[x, 'Ligne'] = str(match.group(1)) + ' ' + str(match.group(2)) + ' ' + str(match.group(3)).upper()
                    match = re.search(r'^(\w{1})\s*(\d{1})(\s*-\s*(\d{1})\s*/(\d{1}))*', df_prod['Ligne'][x])
                    if match:
                        if match.group(4):
                            df_prod.at[x, 'Ligne'] = str(match.group(1)) + str(match.group(2)) + ' - ' + str(match.group(4)) + '/' + str(match.group(5))
                        else:
                            df_prod.at[x, 'Ligne'] = str(match.group(1)) + str(match.group(2))
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
                df_prod['Ligne'] = df_prod['Ligne'].str.upper().str.strip()
                df_prod.to_sql(tab_name, engine, if_exists='append', index=False)
                # df_prod.to_excel(r'C:\Users\zaki1\Desktop\Controle de Gestion\Scripts\PROD_02_2022.xlsx', index = False)

                # df_prod['date'] = df_prod['date'].dt.date
                # print(df_prod)
                last_obj = Production.objects.latest('id')
                last_obj.save()
                print(df_prod.shape)
                print('END PROD')

                # Vente

                tab_name = 'Vente'

                cursor.execute('SELECT MAX("date") FROM public."' + tab_name + '"')
                max_dt = cursor.fetchone()[0]
                print('VENTEEEE')
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
                        match = re.search(r'\d{2}\s*/\d{2}\s*/\d{4}', dte)
                        date = datetime.datetime.strptime(match.group(), '%d/%m/%Y').date()
                    if date > max_dt:
                        print('in if')
                        df = df.reset_index(drop=True)
                        df = get_vente_df(df)
                        print('after get vente')
                        if tab_name != 'TCR':
                            cursor.execute('SELECT MAX("ID") FROM public."' + tab_name + '"')
                            max_id = cursor.fetchone()[0]
                            # print('about to insert')
                            df.insert(0, 'ID', range(int(max_id) + 1, 1 + int(max_id) + len(df)))
                        df.to_sql(tab_name, engine, if_exists='append', index=False)
                        last_obj = Vente.objects.latest('id')
                        last_obj.save()
                        # print(df)


                # TRS

                tab_name = 'TRS'
                print('TRSSSSS')
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
                        match = re.search(r'\d{2}\s*/\d{2}\s*/\d{4}', dte)
                        date = datetime.datetime.strptime(match.group(), '%d/%m/%Y').date()
                    print(date, max_dt)
                    if date > max_dt:
                        df = df.reset_index(drop=True)
                        df = get_trs_df(df)
                        if tab_name != 'TCR':
                            cursor.execute('SELECT MAX("ID") FROM public."' + tab_name + '"')
                            max_id = cursor.fetchone()[0]
                            if not max_id:
                                max_id = 0
                            df.insert(0, 'ID', range(int(max_id) + 1, 1 + int(max_id) + len(df)))
                        df['Ligne'] = df['Ligne'].str.upper().str.strip()
                        df.to_sql(tab_name, engine, if_exists='append', index=False)
                        last_obj = Trs.objects.latest('id')
                        last_obj.save()
            except (KeyError, pd.errors.ParserError):
                messages.error(request, "Erreur ! Noms de feuilles Excel erronés, ou bien la structure du fichier ( d'un tableau ) a été modifiée.")
                print(str(KeyError))
                return redirect('core:add-act-journ')
            except UnboundLocalError:
                messages.error(request, "Erreur ! Les données des dates concernées ont déjà été chargées.")
                return redirect('core:add-act-journ')
            except ValueError as v:
                messages.error(request, str(v))
                return redirect('core:add-act-journ')
            except:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                # print(exc_type, fname, exc_tb.tb_lineno)
                messages.error(request, "Erreur ! ")
                print(exc_type, fname, exc_tb.tb_lineno, traceback.format_exc())
                return redirect('core:add-act-journ')
            fs.delete(uploaded_file_path)
        messages.success(request, "Opération terminé avec succès !")
        return redirect('core:add-act-journ')

@login_required
def add_tcr(request):
    context = {
        'title' : "Nouveau TCR".upper(),
        'req' : "Nouveau TCR".upper(),
    }
    return render(request, 'core/add_tcr.html', context)

class AddTcr(LoginRequiredMixin, View):
    def post(self, request):
        if request.FILES['file_pg']:
            month_crn = 0
            year_crn = 0
            if 'edit-tcr-month' in request.POST:
                month_crn = int(request.POST['edit-tcr-month'])
                year_crn = int(request.POST['edit-tcr-year'])
                dte = datetime.date(year_crn, month_crn, 28)
                # pylint: disable=no-member
                Tcr.objects.filter(date = dte).delete()
            myfile = request.FILES['file_pg']
            fs = FileSystemStorage()
            filename = fs.save(myfile.name, myfile)
            uploaded_file_path = fs.path(filename)
            file_str = uploaded_file_path
            tab_name = 'TCR'
            xl = pd.ExcelFile(file_str, engine='openpyxl') # pylint: disable=abstract-class-instantiated
            no_error = True
            try:
                do_something = False
                for sheetname in xl.sheet_names:
                    if re.match("^[0-9 ]+$", sheetname):
                        # print(sheetname)
                        df = pd.read_excel(file_str, sheet_name=sheetname, header=1)
                        # print(df)
                        period = df['Unnamed: 0'][2]
                        match = re.search(r'\w*\s(\w+)-(\d{4})', period)
                        month = dateparser.parse(match.group(1)).month
                        year = dateparser.parse(match.group(2)).year
                        today = datetime.date.today()
                        cursor.execute('SELECT COUNT(*) FROM public."' + tab_name + '" WHERE "date" = \'' + str(datetime.date(year, month, 28)) + '\';')
                        count = cursor.fetchone()[0]
                        if (count == 0 and datetime.date(year, month, 28) == datetime.date(today.year, today.month - 1, 28) ) or (month == month_crn and year == year_crn):
                            # print(month, year)
                            do_something = True
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
                            # df.insert(0, 'ID', '')
                            # df['ID'] = df.apply (lambda row: row['Unité'] + '_' + str(row['date'].month) + '_' + str(row['date'].year), axis=1)
                            df.to_sql(tab_name, engine, if_exists='append', index=False)
                            for i in range(0, 5):
                                max_id = Tcr.objects.latest('id').id - i
                                # pylint: disable=no-member
                                obj = Tcr.objects.get(id = max_id)
                                obj.save()
                if not do_something:
                    messages.error(request, "Aucun nouveau TCR ajouté ! Les dates concernés existent déjà.")
                    return redirect('core:add-tcr')
                if no_error:
                    raise UnboundLocalError('Data already processed.')
            except (KeyError, pd.errors.ParserError):
                messages.error(request, "Erreur ! Noms de feuilles Excel erronés, ou bien la structure du fichier ( d'un tableau ) a été modifiée.")
                return redirect('core:add-tcr')
            except UnboundLocalError:
                messages.error(request, "Erreur ! Les données des dates concernées ont déjà été chargées.")
                return redirect('core:add-tcr')
            if 'edit-tcr-month' in request.POST:
                messages.success(request, "Le données ont été stockés avec succès !")
                return redirect('core:tcr-view')
        messages.success(request, "Le données ont été stockés avec succès !")
        return redirect('core:add-tcr')

@login_required
def add_act_journ_man(request):
    # pylint: disable=no-member
    dstc_volumes = list(Production.objects.values_list('volume', flat=True).distinct().order_by('volume'))
    dstc_cats = Production.objects.values_list('category', flat=True).distinct().order_by('category')
    prod_lines = Production.objects.values_list('ligne', flat=True).distinct().order_by('ligne')
    trs_lines = Trs.objects.values_list('ligne', flat=True).distinct().order_by('ligne')
    cats = [i for i in dstc_cats if i]
    prod_lines = [i for i in prod_lines if i]
    trs_lines = [i for i in trs_lines if i]
    volumes = [i for i in dstc_volumes if i]
    context = {
        'title' : "ACtivité journalière".upper(),
        'req' : "ACtivité journalière".upper(),
        'cats': cats,
        'prod_lines': prod_lines,
        'trs_lines': trs_lines,
        'volumes': volumes,
    }
    return render(request, 'core/add_act_journ_man.html', context)

class AddActMan(LoginRequiredMixin, View):
    def post(self, request):
        dic = dict(request.POST)
        del dic['csrfmiddlewaretoken']
        dic_values = dic.items()
        for key, value in dic_values:
            dic[key] = value
        nb_prod = len(dic['line'])
        nb_sale = len(dic['qte_journ'])
        nb_trs = len(dic['ligne'])
        # print(dic)
        # print('\n')

        # pylint: disable=no-member
        max_dt = Production.objects.earliest('date')
        dt = datetime.datetime.strptime(dic['date'][0], '%Y-%m-%d').date()
        if dt < max_dt.date:
            messages.error(request, "La date renseignée est déjà couverte !")
            return redirect('core:add-act-journ-manual')
        

        # PRODUCTION
        dic_prod = dict()
        for i in range(0, nb_prod):
            dic_prod['unite'] = dic['unit'][0]
            dic_prod['ligne'] = dic['line'][i]
            dic_prod['des'] = dic['des'][i]
            dic_prod['client'] = dic['client'][i]
            dic_prod['obj'] = int(dic['obj'][i])
            dic_prod['capacite_jour'] = int(dic['capacite_jour'][i])
            dic_prod['brute_jour'] = int(dic['conforme_jour'][i]) + int(dic['rebut_jour'][i])
            dic_prod['conforme_jour'] = int(dic['conforme_jour'][i])
            dic_prod['rebut_jour'] = int(dic['rebut_jour'][i])
            try:
                dic_prod['taux_jour'] = int(dic_prod['brute_jour']) / int(dic['capacite_jour'][i])
            except ZeroDivisionError:
                dic_prod['taux_jour'] = 0
            # print(dic['unit'][0], dic['category'][i])
            # pylint: disable=no-member
            qs = Production.objects.filter(unite__icontains=dic['unit'][0], category__icontains=dic['category'][i]).order_by('-id')
            # print(dic_prod['des'])
            obj = None
            for prod in qs:
                sim_txt = similar(dic_prod['des'], prod.des)[0]
                sim_dig = similar(dic_prod['des'], prod.des)[1]
                if sim_txt > 0.9 and sim_dig:
                    obj = prod
                    # print(obj.id, obj.des, obj.date)
                    break
            conf_mois = 0
            reb_mois = 0
            if obj:
                conf_mois = int(obj.conforme_mois)
                reb_mois = int(obj.rebut_mois)
            dic_prod['conforme_mois'] = conf_mois + int(dic_prod['conforme_jour'])
            dic_prod['rebut_mois'] = reb_mois + int(dic_prod['rebut_jour'])
            dic_prod['brute_mois'] = dic_prod['conforme_mois'] + dic_prod['rebut_mois']
            try:
                dic_prod['taux_real'] = int(dic_prod['brute_mois']) / int(dic['obj'][i])
            except ZeroDivisionError:
                dic_prod['taux_real'] = 0
            try:
                dic_prod['taux_rebut'] = int(dic_prod['rebut_mois']) / int(dic_prod['brute_mois'])
            except ZeroDivisionError:
                dic_prod['taux_rebut'] = 0
            dic_prod['pu_cout_revient'] = float(dic['pu_cout_revient'][i])
            dic_prod['montant_journee_coutrev'] = dic_prod['pu_cout_revient'] * dic_prod['conforme_jour']
            dic_prod['montantcumul_coutrev'] = dic_prod['pu_cout_revient'] * dic_prod['conforme_mois']
            dic_prod['pu_prix_vente'] = float(dic['pu_prix_vente'][i])
            try:
                dic_prod['montant_journee_prix_vente'] = dic_prod['pu_prix_vente'] * (dic_prod['montant_journee_coutrev'] / dic_prod['pu_cout_revient'])
            except ZeroDivisionError:
                dic_prod['montant_journee_prix_vente'] = 0
            try:
                dic_prod['montantcumul_prix_vente'] = dic_prod['pu_prix_vente'] * (dic_prod['montantcumul_coutrev'] / dic_prod['pu_cout_revient'])
            except ZeroDivisionError:
                dic_prod['montantcumul_prix_vente'] = 0
            dic_prod['date'] = dic['date'][0]
            dic_prod['category'] = dic['category'][i]
            dic_prod['produit'] = dic['produit'][i]
            if dic_prod['produit'] == 'Boite':
                dic_prod['volume'] = dic['volume'][i]
            else:
                dic_prod['volume'] = None
            new_id = Production.objects.aggregate(Max('id')).get('id__max') + 1
            obj, created = Production.objects.update_or_create(
                id = new_id,
                defaults = dic_prod
            )
            # CHECK FOR OBJECTIVES
            # IF NEW MONTH, THEN ADD EMPTY OBJECTIVES WITH 0 ONLY
            # IF SAME MONTH OF YEAR - PRODUCT - CATEGORY - VOLUME ( if prod = boite ) then obj already exists
            month = dt.month
            year = dt.year
            qs = ObjectifCapaciteProduction.objects.filter(produit = dic_prod['produit'],
                    category = dic_prod['category'],
                    date__month = month,
                    date__year = year,
                    unite = dic_prod['unite'])
            if dic_prod['produit'] == 'Boite':
                qs = qs.filter(volume = dic_prod['volume'])
            if qs.count() == 0:
                # Production ajouté, pas d'objectif
                dic_new_obj = dict()
                new_id = ObjectifCapaciteProduction.objects.aggregate(Max('id')).get('id__max') + 1
                dic_new_obj['unite'] = dic_prod['unite']
                dic_new_obj['obj'] = 0
                dic_new_obj['capacite_jour'] = 0
                dic_new_obj['date'] = dic_prod['date']
                dic_new_obj['category'] = dic_prod['category']
                dic_new_obj['produit'] = dic_prod['produit']
                if dic_new_obj['produit'] == 'Boite':
                    dic_new_obj['volume'] = dic_prod['volume']
                else:
                    dic_new_obj['volume'] = None
                obj, created = ObjectifCapaciteProduction.objects.update_or_create(
                    id = new_id,
                    defaults = dic_new_obj
                )
                

        dic_sale = dict()
        for i in range(0, nb_sale):
            dic_sale['unite'] = dic['unit'][0]
            dic_sale['des'] = dic['des'][i + nb_prod]
            dic_sale['client'] = dic['client'][i + nb_prod]
            dic_sale['qte_journ'] = int(dic['qte_journ'][i])
            # pylint: disable=no-member
            qs = Vente.objects.filter(unite__icontains=dic['unit'][0]).order_by('-id')
            obj = None
            for sale in qs:
                # print(sale)
                sim_des_txt = similar(dic_sale['des'], sale.des)[0]
                sim_des_dig = similar(dic_sale['des'], sale.des)[1]
                sim_client = similar(dic_sale['client'], sale.client)[0]
                if sim_des_txt > 0.9 and sim_des_dig and sim_client > 0.93:
                    obj = sale
                    break
            qte_cumul = 0
            if obj:
                qte_cumul = int(obj.qte_cumul)
            dic_sale['qte_cumul'] = qte_cumul + dic_sale['qte_journ']
            dic_sale['pu'] = float(dic['pu'][i])
            dic_sale['montant_journee'] = dic_sale['pu'] * dic_sale['qte_journ']
            dic_sale['montant_cumul'] = dic_sale['pu'] * dic_sale['qte_cumul']
            dic_sale['date'] = dic['date'][0]
            dic_sale['category'] = dic['category'][i + nb_prod]
            new_id = Vente.objects.aggregate(Max('id')).get('id__max') + 1
            obj, created = Vente.objects.update_or_create(
                id = new_id,
                defaults = dic_sale
            )
        
        dic_trs = dict()
        for i in range(0, nb_trs):
            dic_trs['unite'] = dic['unit'][0]
            dic_trs['ligne'] = dic['ligne'][i]
            dic_trs['arret_plan'] = int(dic['arret_plan'][i])
            dic_trs['arret_non_plan'] = int(dic['arret_non_plan'][i])
            dic_trs['ecarts_cadences'] = dic_trs['arret_plan'] + dic_trs['arret_non_plan']
            dic_trs['capacite_theo'] = int(dic['capacite_theo'][i])
            dic_trs['qte_conf'] = int(dic['qte_conf'][i])
            dic_trs['qte_rebut'] = int(dic['qte_rebut'][i])
            dic_trs['qte_prod'] = dic_trs['qte_conf'] + dic_trs['qte_rebut']
            dic_trs['temps_ouv'] = int(dic['temps_ouv'][i])
            dic_trs['temps_req'] = dic_trs['temps_ouv'] - dic_trs['arret_plan']
            dic_trs['temps_fct'] = dic_trs['temps_req'] - dic_trs['arret_non_plan']
            try:
                dic_trs['taux_dispo'] = dic_trs['temps_fct'] / dic_trs['temps_req']
            except ZeroDivisionError:
                dic_trs['taux_dispo'] = 0
            dic_trs['temps_net'] = dic_trs['temps_fct'] - dic_trs['ecarts_cadences']
            try:
                dic_trs['taux_perf'] = dic_trs['temps_net'] / dic_trs['temps_fct']
            except ZeroDivisionError:
                dic_trs['taux_perf'] = 0
            try:
                dic_trs['temps_util'] = dic_trs['temps_net'] - (dic_trs['temps_ouv'] - (dic_trs['temps_ouv'] * dic_trs['qte_conf'] / dic_trs['qte_prod']))
            except ZeroDivisionError:
                dic_trs['temps_util'] = 0
            try:
                dic_trs['taux_qualit'] = dic_trs['temps_util'] / dic_trs['temps_net']
            except ZeroDivisionError:
                dic_trs['taux_qualit'] = 0
            dic_trs['trs'] = dic_trs['taux_dispo'] * dic_trs['taux_perf'] * dic_trs['taux_qualit']
            dic_trs['date'] = dic['date'][0]
            new_id = Trs.objects.aggregate(Max('id')).get('id__max') + 1
            obj, created = Trs.objects.update_or_create(
                id = new_id,
                defaults = dic_trs
            )
        messages.success(request, "Le données ont été traitées avec succès !")
        return redirect('core:add-act-journ-manual')

class AuditSummary(LoginRequiredMixin, ListView):
    model = AuditLog
    template_name = 'core/audit_summary.html'
    paginate_by = 30
    
    def get_queryset(self):
        # pylint: disable=no-member
        qs = AuditLog.objects.all().order_by('-dt')
        if self.request.GET.get('tab') and self.request.GET.get('tab') != 'all':
            qs = qs.filter(tab=self.request.GET.get('tab'))
        else:
            qs = qs.filter(tab = 'Production')
        if self.request.GET.get('date'):
            date = datetime.datetime.strptime(self.request.GET.get('date'), '%Y-%m-%d').date()
            qs = qs.filter(dt__date = date)
        if self.request.GET.get('op') and self.request.GET.get('op') != 'all':
            qs = qs.filter(op=self.request.GET.get('op'))
        if self.request.GET.get('user'):
            user = User.objects.get(username=self.request.GET.get('user'))
            qs = qs.filter(user=user)
        else:
            qs = qs.filter(user = self.request.user)
        return qs

    def get_context_data(self, *args,**kwargs):
        context = super(AuditSummary, self).get_context_data(*args, **kwargs)
        context['title'] = 'historique des modifications'.upper()
        context['req'] = 'historique des modifications'.upper()
        context['count'] = self.get_queryset().count
        # pylint: disable=no-member
        context['tables'] = list(AuditLog.objects.values_list('tab', flat=True).distinct())
        if self.request.GET.get('op') and self.request.GET.get('op') != 'all':
            context['op'] = self.request.GET.get('op')
        qs = self.get_queryset().first()
        if qs:
            context['table'] = qs.tab
            context['user_n'] = qs.user
        else:
            context['table'] = self.request.GET.get('tab')
            context['user_n'] = User.objects.get(username = self.request.GET.get('user')    )
        context['ops'] = list(AuditLog.objects.values_list('op', flat=True).distinct())
        context['users'] = list(User.objects.all())
        return context

class AuditDetails(LoginRequiredMixin, DetailView):
    model = AuditLog
    template_name = 'core/audit-details.html'

    def get_context_data(self, *args,**kwargs):
        context = super(AuditDetails, self).get_context_data(*args, **kwargs)
        # pylint: disable=no-member
        obj = AuditLog.objects.get(id=self.get_object().pk)
        if obj.tab == 'TCR':
            context['obj_rel'] = Tcr.objects.get(id = obj.line_id)
        context['req'] = 'détails de l\'opération : '.upper() + obj.op
        context['title'] = 'détails de l\'opération'.upper()
        context['op'] = obj.op
        calc_fields = []
        if obj.tab == 'Production':
            calc_fields = calc_fields_prod
        elif obj.tab == 'Vente':
            calc_fields = calc_fields_sale
        elif obj.tab == 'TCR':
            calc_fields = calc_fields_tcr
        else:
            calc_fields = [f.name for f in Trs._meta.get_fields() if f.name not in no_calc_fields_trs ]
        details = obj.details
        details_edit = dict()
        for key, val in details.items():
            if key not in calc_fields:
                for k, v in pretty_naming.items():
                    if k == key:
                        details_edit[v] = val
        context['details'] = details_edit
        context['obj'] = obj
        return context

@login_required
def add_tcr_man(request):
    # pylint: disable=no-member
    years = list(Tcr.objects.values_list('date__year', flat=True).distinct())
    if datetime.datetime.today().month == 2:
        years.append(datetime.datetime.today().year)
    context = {
        'title' : "nouveau tcr".upper(),
        'req' : "nouveau tcr".upper(),
        'years': years,
        'nb_years': len(years),
        'mode': 'add',
        'units': list(Tcr.objects.exclude(unite = 'ENTREPRISE').values_list('unite', flat=True).distinct())
    }
    return render(request, 'core/add_tcr_man.html', context)

class TcrMan(LoginRequiredMixin, ListView):
    model = Tcr
    template_name = 'core/add_tcr_man.html'

    def get_queryset(self):
        # pylint: disable=no-member
        qs = Tcr.objects.filter(date__year = self.kwargs['year'], date__month = self.kwargs['month'])
        return qs
    
    def get_context_data(self, *args,**kwargs):
        context = super(TcrMan, self).get_context_data(*args, **kwargs)
        context['title'] = 'Modification tcr - '.upper() + calendar.month_name[self.kwargs['month']] + ' ' + str(self.kwargs['year'])
        context['req'] = context['title']
        context['mode'] = 'edit'
        context['qs'] = self.get_queryset()
        context['units'] = list(Tcr.objects.exclude(unite = 'ENTREPRISE').values_list('unite', flat=True).distinct())
        context['units'].insert(0, context['units'].pop(2))
        context['month'] = self.kwargs['month']
        context['year'] = self.kwargs['year']
        return context

class AddTcrMan(LoginRequiredMixin, View):
    def post(self, request):
        dic = dict(request.POST)
        del dic['csrfmiddlewaretoken']
        dic_values = dic.items()
        for key, value in dic_values:
            val = list()
            for v in value:
                try:
                    val.append(int(v))
                except ValueError:
                    try:
                        val.append(float(v))
                    except ValueError:
                        val.append(v)
            dic[key] = val
        month = int(dic['month'][0])
        year = int(dic['year'][0])
        dt = datetime.datetime(year, month, 28, 0, 0, 0)
        # pylint: disable=no-member
        if dic['mode'][0] == 'add' and Tcr.objects.filter(date__date = dt.date()).count() > 0:
            messages.error(request, "Le TCR " + calendar.month_name[month].upper() + " " + str(year) + " existe déjà ! Veuillez le modifier si vous désirez ainsi.")
            return redirect('core:add-tcr-man')
        del dic['month']
        del dic['year']
        mode = dic['mode']
        del dic['mode']
        for unit in range(0, len(dic['unite'])):
            dic_tcr = dict()
            # id = dic['unite'][unit] + '_' + str(month) + '_' + str(year)
            # dic_tcr['id'] = id
            if mode == 'edit':
                id = dic['id'][unit]
            else:
                # pylint: disable=no-member
                id = Tcr.objects.aggregate(Max('id')).get('id__max') + 1
                # print(id)
            for key, val in dic.items():
                if key != 'id':
                    dic_tcr[key] = dic[key][unit]
            dic_tcr['prod_exerc'] = dic_tcr['ca'] + dic_tcr['cessions_et_produits'] + dic_tcr['var_stock_fini_encours'] + dic_tcr['prod_immob'] + dic_tcr['subv_expl']
            dic_tcr['consom_exerc'] = dic_tcr['achats_consom'] + dic_tcr['serv_ext_other_consom'] + dic_tcr['consom_inter_unit']
            dic_tcr['v_ajoute'] = dic_tcr['prod_exerc'] - dic_tcr['consom_exerc']
            dic_tcr['exced_brut_exploit'] = dic_tcr['v_ajoute'] - dic_tcr['charge_pers'] - dic_tcr['impot_tax_vers_ass']
            dic_tcr['res_op'] = dic_tcr['exced_brut_exploit'] + dic_tcr['other_prod_op'] + dic_tcr['repr_pert_val_prov'] - (dic_tcr['other_charge_op'] + dic_tcr['prod_inter_unit'] + dic_tcr['charge_inter_unit'] + dic_tcr['dot_amort_prov_pert_val'])
            dic_tcr['res_financ'] = dic_tcr['prod_fin'] - dic_tcr['charge_financ']
            dic_tcr['res_ord_pre_impot'] = dic_tcr['res_op'] + dic_tcr['res_financ']
            dic_tcr['tot_prod_act_ord'] = dic_tcr['prod_exerc'] + dic_tcr['other_prod_op'] + dic_tcr['prod_fin'] + dic_tcr['repr_pert_val_prov']
            dic_tcr['tot_charge_act_ord'] = dic_tcr['consom_exerc'] + dic_tcr['charge_pers'] + dic_tcr['impot_tax_vers_ass'] + dic_tcr['dot_amort_prov_pert_val'] + dic_tcr['other_charge_op'] + dic_tcr['charge_financ'] + dic_tcr['impot_diff_res_ord'] + dic_tcr['impot_exig_res_ord']
            dic_tcr['res_net_act_ord'] = dic_tcr['tot_prod_act_ord'] - dic_tcr['tot_charge_act_ord']
            dic_tcr['res_extraord'] = dic_tcr['elem_extraord_prod'] - dic_tcr['elem_extraord_charge']
            dic_tcr['res_net_exerc'] = dic_tcr['res_net_act_ord'] + dic_tcr['res_extraord']
            dic_tcr['date'] = dt
            print(dic_tcr)

            # pylint: disable=no-member
            obj, created = Tcr.objects.update_or_create(
                id = id,
                defaults = dic_tcr
            )
        unit = 'ENTREPRISE'
        # id = unit + '_' + str(month) + '_' + str(year)
        dic_tcr = {}
        # dic_tcr['id'] = id
        dic_tcr['unite'] = unit
        # dt = datetime.datetime(2021, 12, 28, 0, 0, 0)
        dic_tcr['date'] = dt
        # pylint: disable=no-member
        fields = Tcr._meta.get_fields()
        qs = Tcr.objects.filter(date__date=dt.date()).exclude(unite = unit)
        for field in fields:
            if field.name != 'id' and field.name != 'unite' and field.name != 'date':
                dic_tcr[field.name] = qs.aggregate(Sum(field.name)).get(field.name + '__sum')
        # print(dic_tcr)
        id = Tcr.objects.aggregate(Max('id')).get('id__max') + 1
        obj, created = Tcr.objects.update_or_create(
            id = id,
            defaults = dic_tcr
        )
        messages.success(request, "L'opération s'est terminé avec succès !")
        return redirect('core:tcr-view')

class ObjCapacitySummary(LoginRequiredMixin, ListView):
    model = ObjectifCapaciteProduction
    template_name = 'core/goals-summary.html'
    paginate_by = 30
    
    def get_queryset(self):
        # pylint: disable=no-member
        qs = ObjectifCapaciteProduction.objects.all().order_by('-date')
        dates = list(qs.values_list('date', flat=True).distinct())
        dates.append(datetime.date(2022, 2, 20))
        if not self.request.GET.get('date'):
            date = [dates[0].month, dates[0].year]
        else:
            date = [int(self.request.GET.get('date').split('-')[0]), int(self.request.GET.get('date').split('-')[1])]
        if self.request.GET.get('prod'):
            prod = self.request.GET.get('prod')
        else:
            prod = 'Boite'
        # pylint: disable=no-member
        qs = ObjectifCapaciteProduction.objects.filter(produit = prod, date__month = date[0], date__year = date[1])
        return qs.order_by('-date')

    def get_context_data(self, *args,**kwargs):
        context = super(ObjCapacitySummary, self).get_context_data(*args, **kwargs)
        context['title'] = 'Objectifs et capacités'.upper()
        context['req'] = 'Objectifs et capacités'.upper()
        context['count'] = self.get_queryset().count()
        context['mode'] = self.kwargs['mode']
        if context['mode'] == 'add':
            volumes = list(Production.objects.filter(produit = 'Boite').values_list('volume', flat=True).distinct())
            volumes = [x for x in volumes if x is not None]
            volumes = list(map(lambda x: x.upper().strip(), volumes))
            volumes.sort()
            context['volumes'] = volumes
            context['years'] = []
            for year in range(datetime.datetime.now().year, datetime.datetime.now().year + 3):
                context['years'].append(year)
        if self.request.GET.get('prod'):
            context['prod'] = self.request.GET.get('prod')
        else:
            context['prod'] = 'Boite'
        # pylint: disable=no-member
        qs = ObjectifCapaciteProduction.objects.all().order_by('-date')
        context['dates'] = list(qs.values_list('date', flat=True).distinct())
        # if len(context['dates']) > 1:
        #     rmv_date = context['dates'].pop(0)
        if not self.request.GET.get('date'):
            context['first_dt'] = [context['dates'][0].month, context['dates'][0].year]
        else:
            context['first_dt'] = [int(self.request.GET.get('date').split('-')[0]), int(self.request.GET.get('date').split('-')[1])]
        # print(context['first_dt'])
        context['qs'] = self.get_queryset()
        return context

class AddObjectifCap(LoginRequiredMixin, View):
    def post(self, request):
        dic = dict(request.POST)
        del dic['csrfmiddlewaretoken']
        mode = None
        if dic['mode'][0] == 'add':
            mode = 'add'
            dic['date-obj'] = [dic['month-obj'][0] + '-' + dic['year-obj'][0]]
            del dic['mode']
            del dic['month-obj']
            del dic['year-obj']
        dic_values = dic.items()
        for key, value in dic_values:
            if key == 'date-obj':
                month = int(value[0].split('-')[0])
                year = int(value[0].split('-')[1])
                dic[key] = [month, year]
            else:
                val = list()
                for v in value:
                    try:
                        val.append(int(v))
                    except ValueError:
                        val.append(v)
                dic[key] = val
        # print(dic)
        # IF ADD MODE ; CHECK IF DATE MENTIONED ALREADY EXISTS
        if mode:
            qs_count = ObjectifCapaciteProduction.objects.filter(
                date__month = dic['date-obj'][0],
                date__year = dic['date-obj'][1],
                produit = dic['prod-obj'][0]
            ).count()
            if qs_count > 0:
                messages.error(request, "Des objectifs ont déjà été fixés pour le produit : " + dic['prod-obj'][0] + ", pour le mois " + str(calendar.month_name[dic['date-obj'][0]]).upper() + " " + str(dic['date-obj'][1]) + " .")
                return redirect(reverse('core:goals-summary', kwargs={
                    'mode': mode
                }))
        # DELETE THE DATE-CONCERNED & PRODUCT-CONCERNED ROWS
        ObjectifCapaciteProduction.objects.filter(date__month = dic['date-obj'][0],
                                                date__year = dic['date-obj'][1],
                                                produit = dic['prod-obj'][0]).delete()
        nb_obj = len(dic['obj'])
        dic_obj = dict()
        date = datetime.date(dic['date-obj'][1], dic['date-obj'][0], datetime.datetime.now().day)
        for obj in range(0, nb_obj):
            dic_obj['id'] = ObjectifCapaciteProduction.objects.latest('id').id + 1
            dic_obj['unite'] = dic['unit-obj'][obj]
            dic_obj['obj'] = dic['obj'][obj]
            dic_obj['capacite_jour'] = dic['capacite_jour'][obj]
            dic_obj['date'] = date
            dic_obj['volume'] = dic['volume-obj'][obj]
            dic_obj['category'] = dic['category-obj'][obj]
            dic_obj['produit'] = dic['prod-obj'][0]
            obj, created = ObjectifCapaciteProduction.objects.update_or_create(
            id = dic_obj['id'],
            defaults = dic_obj
        )
        messages.success(request, "L'opération s'est terminé avec succès !")
        if not mode:
            mode = 'edit'
        return redirect(reverse('core:goals-summary', kwargs={
                    'mode': mode
                }))

@login_required
def set_capacity(request):
    if request.is_ajax and request.method == "POST":
        # pylint: disable=no-member
        qs = ObjectifCapaciteProduction.objects.filter(
            unite = request.POST.get('unit'),
            category = request.POST.get('category'),
            volume = request.POST.get('volume'),
            produit = request.POST.get('prod'),
        )
        if qs.count() > 0:
            cap = qs.order_by('-id')[0].capacite_jour
        else:
            cap = 0
        return JsonResponse({'capacity': cap})
    return JsonResponse({'error': 'Something went wrong!'})

@login_required
def add_cap_prod_imp(request):
    context = {
        'title' : "capacité de production ( imprimerie )".upper(),
        'req' : "capacité de production ( imprimerie )".upper(),
    }
    return render(request, 'core/add-cap-prod-imp.html', context)

class addFlashJourn(LoginRequiredMixin, View):
    def post(self, request):
        if request.FILES['file_pg']:
            myfile = request.FILES['file_pg']
            fs = FileSystemStorage()
            filename = fs.save(myfile.name, myfile)
            uploaded_file_path = fs.path(filename)
            new_act_journ = uploaded_file_path
            try:
                tab_name = 'Production_Capacite_Imp'
                cursor.execute('SELECT MAX("date") FROM public."' + tab_name + '"')
                max_dt_cap = cursor.fetchone()[0]
                tab_name = 'Flash_Impression'
                cursor.execute('SELECT MAX("date") FROM public."' + tab_name + '"')
                max_dt_flash = cursor.fetchone()[0]

                # GET TABLE INTO DATAFRAME TO EXTRACT CURRENT DISTINCT DATES
                qs = Production_Capacite_Imp.objects.all()
                df = read_frame(qs)
                dst_dates = list(Production_Capacite_Imp.objects.values_list('date', flat=True).distinct().order_by('-date'))
                # print(dst_dates)

                xl = pd.ExcelFile(new_act_journ, engine='openpyxl') # pylint: disable=abstract-class-instantiated
                bg_frames = []
                good_file = False
                for sheetname in xl.sheet_names:
                    if 'flash' in sheetname.lower() or 'journ' in sheetname.lower():
                        good_file = True
                        bg_df = pd.read_excel(new_act_journ, sheet_name=sheetname, header=1)
                        ix = bg_df.index[bg_df['Unnamed: 0'].str.lower().str.contains(r'\d{2}/\d{2}/\d{4}', na = False)].tolist()[0]
                        dte = bg_df['Unnamed: 0'][ix]
                        # check the data type
                        if isinstance(dte, datetime.datetime):
                            date = dte.date()
                        else:
                            match = re.search(r'\d{2}/\d{2}/\d{4}', dte)
                            date = datetime.datetime.strptime(match.group(), '%d/%m/%Y').date()
                        # print(date, max_dt_flash)
                        if date in dst_dates:
                            messages.error(request, "Erreur ! le flash d'impression du " + str(date) + " existe déjà.")
                            return redirect('core:add-cap-prod-imp')
                        else:
                            dfs = bg_df.index[bg_df['Unnamed: 0'].str.lower().str.contains('vern|tand|offs', na = False)].tolist()
                            for idx, val in enumerate(dfs):
                                df = pd.DataFrame()
                                try:
                                    df = bg_df.loc[val: dfs[idx+1]]
                                except IndexError:
                                    df = bg_df.loc[val:]
                                df = df.reset_index(drop=True)
                                line = df.iloc[0]['Unnamed: 0']
                                if 'vern' in line.lower():
                                    line = 'VERNISSEUSE'
                                else:
                                    line = 'TANDEM'
                                # **************************************** FLASH IMPRESSION ***********************************************************
                                end_flash_df = df.index[df['Unnamed: 3'].str.lower().str.contains('tot', na = False)].tolist()[0]
                                flash_df = df.loc[0:end_flash_df, :]
                                flash_df = flash_df.copy()
                                flash_df.dropna(axis=1, how='all', inplace = True)
                                to_rmv = df.index[df['Unnamed: 0'].str.lower().str.contains('shi', na = False)].tolist()[0]
                                flash_df = flash_df.iloc[to_rmv + 3:-1]
                                flash_df['Unnamed: 0'].fillna(method='ffill', inplace = True)
                                flash_df['Unnamed: 1'].fillna(method='ffill', inplace = True)
                                flash_df['Unnamed: 13'].fillna(method='ffill', inplace = True)
                                flash_df['Unnamed: 0'] = flash_df['Unnamed: 0'].str.strip().str[-1].astype(int)
                                flash_df.rename(columns = {
                                    flash_df.columns[0]: 'hours',
                                    flash_df.columns[1]: 'shift',
                                    flash_df.columns[2]: 'format_fer',
                                    flash_df.columns[3]: 'des',
                                    flash_df.columns[4]: 'nb_psg',
                                    flash_df.columns[5]: 'sf_brut',
                                    flash_df.columns[6]: 'sf_rebut',
                                    flash_df.columns[7]: 'sf_conf',
                                    flash_df.columns[8]: 'sf_taux_reb',
                                    flash_df.columns[9]: 'brut',
                                    flash_df.columns[10]: 'rebut',
                                    flash_df.columns[11]: 'conf',
                                    flash_df.columns[12]: 'taux_reb',
                                    flash_df.columns[13]: 'conduct',
                                }, inplace = True)
                                flash_df = flash_df.reset_index(drop=True)
                                flash_df = flash_df.replace(['-'],0)
                                flash_df.fillna(0, inplace = True)
                                flash_df = flash_df.loc[(flash_df['sf_brut'] != 0) | (flash_df['brut'] != 0)]
                                flash_df['sf_brut'] = flash_df['sf_rebut'] + flash_df['sf_conf']
                                try:
                                    flash_df['sf_taux_reb'] = flash_df['sf_rebut'] / flash_df['sf_brut']
                                except ZeroDivisionError():
                                    flash_df['sf_taux_reb'] = np.nan
                                flash_df['brut'] = flash_df['rebut'] + flash_df['conf']
                                try:
                                    flash_df['taux_reb'] = flash_df['rebut'] / flash_df['brut']
                                except ZeroDivisionError():
                                    flash_df['taux_reb'] = np.nan
                                flash_df['date'] = date
                                flash_df['ligne'] = line
                                # print(flash_df[['sf_brut', 'sf_conf', 'sf_rebut', 'sf_taux_reb','brut', 'conf', 'rebut', 'taux_reb']])
                                # **************************************** FLASH IMPRESSION ***********************************************************
                             
                                # **************************************** CAPACITE PROD ***********************************************************
                                start_df2 = df.index[df['Unnamed: 0'].str.lower().str.contains('arr', na = False)].tolist()[0]
                                try:
                                    df_capacite = df.loc[start_df2:dfs[idx+1], :]
                                except:
                                    df_capacite = df.loc[start_df2:, :]
                                df_capacite = df_capacite.reset_index(drop=True)
                                df_capacite.dropna(axis=1, how='all', inplace = True)
                                df_arrets = df_capacite.iloc[:, :3]
                                df_cap_prod = df_capacite.iloc[:, 3:]
                                
                                # DF ARRETS

                                begin_df = (df_arrets['Unnamed: 0'].str.lower().str.contains('prog', na = False)).idxmax()
                                end_df = df_arrets['Unnamed: 2'].where(df_arrets['Unnamed: 2'].str.lower().str.contains('tot', na = False)).last_valid_index()
                                df_arrets = df_arrets.loc[begin_df:end_df-1]
                                df_arrets = df_arrets.loc[:, 'Unnamed: 2':]
                                df_arrets.rename(columns = {
                                    df_arrets.columns[0]: 'label_arret',
                                    df_arrets.columns[1]: 'temps arrets (mn)',
                                }, inplace = True)
                                df_arrets = df_arrets[df_arrets['label_arret'].notna()]
                                # df_arrets['line'] = line
                                # df_arrets['date'] = date

                                df_arrets.loc[df_arrets['label_arret'].str.lower().str.contains('parat'), 'label_arret'] = 'prep_line'
                                df_arrets.loc[df_arrets['label_arret'].str.lower().str.contains('paus'), 'label_arret'] = 'pause_eat'
                                df_arrets.loc[df_arrets['label_arret'].str.lower().str.contains('forma'), 'label_arret'] = 'chg_form'
                                df_arrets.loc[df_arrets['label_arret'].str.lower().str.contains('lavag'), 'label_arret'] = 'lvg'
                                df_arrets.loc[df_arrets['label_arret'].str.lower().str.contains('prog'), 'label_arret'] = 'manque_prog'
                                df_arrets.loc[df_arrets['label_arret'].str.lower().str.contains('pan'), 'label_arret'] = 'panne'
                                df_arrets.loc[df_arrets['label_arret'].str.lower().str.contains('reg|rég'), 'label_arret'] = 'reglages'
                                df_arrets.loc[df_arrets['label_arret'].str.lower().str.contains('autr'), 'label_arret'] = 'autres'
                                df_arrets.loc[df_arrets['label_arret'].str.lower().str.contains('abs'), 'label_arret'] = 'abs'

                                new_ones = list(set(df_arrets['label_arret'].unique()) - set(full_labels))
                                if len(new_ones):
                                    for new_arret in new_ones:
                                        new = True
                                        # print(df_arrets)
                                        # print(df_arrets.loc[df_arrets['label_arret'] == new_arret, 'temps arrets (mn)'].iloc[0])
                                        if df_arrets.loc[df_arrets['label_arret'] == new_arret, 'temps arrets (mn)'].iloc[0] == np.nan:
                                            df_arrets.drop(df_arrets.loc[df_arrets['label_arret'] == new_arret], inplace = True)
                                            new = False
                                        if new:
                                            if 'autres' in df_arrets['label_arret'].unique():
                                                if df_arrets.loc[df_arrets['label_arret'] == 'autres', 'temps arrets (mn)'].iloc[0] == np.nan:
                                                    df_arrets.loc[df_arrets['label_arret'] == 'autres', 'temps arrets (mn)'] = 0
                                                df_arrets.loc[df_arrets['label_arret'] == 'autres', 'temps arrets (mn)'] += df_arrets.loc[df_arrets['label_arret'] == new_arret, 'temps arrets (mn)']
                                                df_arrets.drop(df_arrets.loc[df_arrets['label_arret'] == new_arret], inplace = True)
                                            else:
                                                df_arrets.loc[df_arrets['label_arret'] == new_arret, 'label_arret'] = 'autres'
                                            df_arrets.loc[len(df_arrets.index)] = ['descr', new_arret]
                                        
                                # print(df_arrets)

                                diff = list(set(full_labels) - set(df_arrets['label_arret'].unique().tolist()))
                                if len(diff) > 0:
                                    for label in diff:
                                        df_arrets.loc[len(df_arrets.index)+1] = [label, 0]

                                df_arrets.fillna(0, inplace = True)
                                df_arrets = df_arrets.T
                                df_arrets.columns = df_arrets.iloc[0]
                                df_arrets = df_arrets.iloc[1:]
                                # print(df_arrets)

                                # DF CAP PROD
                            
                                df_cap_prod.rename(columns = {
                                    df_cap_prod.columns[0]: 'Unnamed: 0',
                                    df_cap_prod.columns[1]: 'Unnamed: 1',
                                }, inplace = True)

                                cph_brut = df_cap_prod.index[df_cap_prod['Unnamed: 0'].str.lower().str.contains('=', na = False)].tolist()[0]
                                match = re.search(r'([0-9]+)\s*f', df_cap_prod.at[cph_brut, 'Unnamed: 0'])
                                cph = int(match.group(1))
                                if 'vern' in line.lower():
                                    cph = 5000
                                else:
                                    cph = 4000
                                df_cap_prod = df_cap_prod.iloc[1:]
                                df_cap_prod = df_cap_prod.dropna(axis=0, how='all')
                                df_cap_prod.rename(columns = {
                                    df_cap_prod.columns[0]: 'key',
                                    df_cap_prod.columns[-1]: 'val',
                                }, inplace = True)
                                df_cap_prod = df_cap_prod.loc[:, ~df_cap_prod.columns.str.contains('^Unnamed')]
                                df_cap_prod = df_cap_prod[df_cap_prod['val'].notna()]
                                df_cap_prod.loc[df_cap_prod['key'].str.lower().str.contains('mn'), 'key'] = 'arrets'
                                df_cap_prod.loc[df_cap_prod['key'].str.lower().str.contains('bru'), 'key'] = 'prod_brute'
                                df_cap_prod.loc[df_cap_prod['key'].str.lower().str.contains('shif'), 'key'] = 'shift'
                                df_cap_prod.loc[df_cap_prod['key'].str.lower().str.contains('util'), 'key'] = 'taux_util'
                                df_cap_prod.loc[df_cap_prod['key'].str.lower().str.contains('cap'), 'key'] = 'capacite_prod'
                                df_cap_prod.loc[df_cap_prod['key'].str.lower().str.contains('feu.*av'), 'key'] = 'nb_feuill_pre_arret'
                                df_cap_prod.loc[df_cap_prod['key'].str.lower().str.contains('feu.*ap'), 'key'] = 'nb_feuill_post_arret'
                                df_cap_prod = df_cap_prod.T
                                df_cap_prod.columns = df_cap_prod.iloc[0]
                                df_cap_prod = df_cap_prod.iloc[1:]
                                s = df_cap_prod.columns.to_series()
                                s.iloc[-1] = 'taux_prod'
                                df_cap_prod.columns = s
                                # calcul des taux et de la capacite
                                # print(( (df_cap_prod['shift'] * flash_df.loc.at[0, 'hours'] * 60) - df_cap_prod['arrets'] ) / (df_cap_prod['shift'] * flash_df.loc.at[0, 'hours'] * 60))
                                df_cap_prod['cph'] = cph
                                # print(df_arrets)
                                # print(df_arrets.iloc[0]['prep_line'])
                                # print('hhhhhhhhhhhhhhhhhhhhh')
                                df_cap_prod['arrets'] = df_arrets.iloc[0]['prep_line'] + df_arrets.iloc[0]['pause_eat'] + df_arrets.iloc[0]['chg_form'] + df_arrets.iloc[0]['lvg'] + df_arrets.iloc[0]['manque_prog'] + df_arrets.iloc[0]['panne'] + df_arrets.iloc[0]['reglages'] + df_arrets.iloc[0]['autres'] + df_arrets.iloc[0]['abs']
                                # print(df_cap_prod)
                                flash_df = flash_df.reset_index(drop=True)
                                # print(flash_df)
                                # print(( (df_cap_prod['shift'] * flash_df.at[0, 'hours'] * 60) - df_cap_prod['arrets'] ) / (df_cap_prod['shift'] * flash_df.at[0, 'hours'] * 60))
                                try:
                                    df_cap_prod['taux_util'] = ( (df_cap_prod['shift'] * flash_df.at[0, 'hours'] * 60) - df_cap_prod['arrets'] ) / (df_cap_prod['shift'] * flash_df.at[0, 'hours'] * 60)
                                except:
                                    df_cap_prod['taux_util'] = np.nan
                                # print((df_cap_prod['cph'] * df_cap_prod['shift'] * flash_df.at[0, 'hours'] * df_cap_prod['taux_util']).astype(float).round())
                                try:
                                    df_cap_prod['capacite_prod'] = (df_cap_prod['cph'] * df_cap_prod['shift'] * flash_df.at[0, 'hours'] * df_cap_prod['taux_util']).astype(float).round()
                                except:
                                    df_cap_prod['capacite_prod'] = np.nan
                                try:
                                    df_cap_prod['taux_prod'] = df_cap_prod['prod_brute'] / df_cap_prod['capacite_prod']
                                except:
                                    df_cap_prod['taux_prod'] = np.nan
                                try:
                                    df_cap_prod['nb_feuill_pre_arret'] = df_cap_prod['capacite_prod'] / ( ( (df_cap_prod['shift'] * flash_df.at[0, 'hours'] * 60) - df_cap_prod['arrets'] ) / 60 )
                                except:
                                    df_cap_prod['nb_feuill_pre_arret'] = np.nan
                                try:
                                    df_cap_prod['nb_feuill_post_arret'] = df_cap_prod['capacite_prod'] / ( df_cap_prod['shift'] * flash_df.at[0, 'hours'] )
                                except:
                                    df_cap_prod['nb_feuill_post_arret'] = np.nan

                                # COMBINE DF_ARRET AND DF_CAP_PROD
                                df_arrets.reset_index(drop=True, inplace=True)
                                df_cap_prod.reset_index(drop=True, inplace=True)
                                df_capacite = pd.concat([df_cap_prod, df_arrets], axis=1)
                                df_capacite['date'] = date
                                df_capacite['ligne'] = line

                                # **************************************** CAPACITE PROD ***********************************************************

                                # print(flash_df)
                                # print(df_capacite)

                                tab_name = 'Production_Capacite_Imp'

                                cursor.execute('SELECT MAX("id") FROM public."' + tab_name + '"')
                                max_id = cursor.fetchone()[0]
                                if not max_id:
                                    max_id = 0
                                df_capacite.insert(0, 'id', range(int(max_id) + 1, 1 + int(max_id) + len(df_capacite)))
                                df_capacite.to_sql(tab_name, engine, if_exists='append', index=False)

                                tab_name = 'Flash_Impression'

                                cursor.execute('SELECT MAX("id") FROM public."' + tab_name + '"')
                                max_id = cursor.fetchone()[0]
                                if not max_id:
                                    max_id = 0
                                flash_df.insert(0, 'id', range(int(max_id) + 1, 1 + int(max_id) + len(flash_df)))
                                flash_df.to_sql(tab_name, engine, if_exists='append', index=False)
                if not good_file:
                    messages.error(request, "Fichier non conforme ! Veuillez relire la note importante en jaune.")
                    return redirect('core:add-cap-prod-imp')
            except (KeyError, pd.errors.ParserError):
                messages.error(request, "Erreur ! Noms de feuilles Excel erronés, ou bien la structure du fichier ( d'un tableau ) a été modifiée.")
                print(str(KeyError))
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                # print(exc_type, fname, exc_tb.tb_lineno)
                # messages.error(request, "Erreur ! ")
                print(exc_type, fname, exc_tb.tb_lineno, traceback.format_exc())
                return redirect('core:add-cap-prod-imp')
            except UnboundLocalError:
                messages.error(request, "Erreur ! Les données des dates concernées ont déjà été chargées.")
                return redirect('core:add-cap-prod-imp')
            except ValueError as v:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                # print(exc_type, fname, exc_tb.tb_lineno)
                # messages.error(request, "Erreur ! ")
                print(exc_type, fname, exc_tb.tb_lineno, traceback.format_exc())
                messages.error(request, str(v))
                return redirect('core:add-cap-prod-imp')
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                # print(exc_type, fname, exc_tb.tb_lineno)
                messages.error(request, "Erreur ! Probablement un nouvel arrêt non-enregistré.")
                print(exc_type, fname, exc_tb.tb_lineno, traceback.format_exc())
                return redirect('core:add-cap-prod-imp')
            # f = open(uploaded_file_path)
            # f.close()
            # os.remove(uploaded_file_path)
            # fs.delete(uploaded_file_path)
        messages.success(request, "Opération terminé avec succès !")
        return redirect('core:add-cap-prod-imp')
    
class FlashImpressionSummary(LoginRequiredMixin, ListView):
    model = Production_Capacite_Imp
    template_name = 'core/cap_impression_summary.html'
    paginate_by = 30
    
    def get_queryset(self):
        # pylint: disable=no-member
        qs = Production_Capacite_Imp.objects.all().order_by('-date')
        if self.request.GET.get('date'):
            date = datetime.datetime.strptime(self.request.GET.get('date'), '%Y-%m-%d').date()
            # pylint: disable=no-member
            qs = qs.filter(date=date)
        if self.request.GET.get('lines') and self.request.GET.get('lines') != 'all':
            qs = qs.filter(ligne = self.request.GET.get('lines').strip())
        return qs.order_by('-date', '-ligne')

    def get_context_data(self, *args,**kwargs):
        context = super(FlashImpressionSummary, self).get_context_data(*args, **kwargs)
        context['max_dt_flash'] = Production_Capacite_Imp.objects.latest('date').date
        context['req'] = 'flash journalier d\'impression'.upper()
        context['count'] = self.get_queryset().count()
        context['mode'] = 'impr'
        if self.request.GET.get('lines'):
            context['ligne'] = self.request.GET.get('lines')
        if self.request.GET.get('date'):
            context['date'] = datetime.datetime.strptime(self.request.GET.get('date'), '%Y-%m-%d').date()
        context['lines'] = list(Production_Capacite_Imp.objects.values_list('ligne', flat = True).distinct())
        return context

class FlashImpressionDetails(LoginRequiredMixin, DetailView):
    model = Production_Capacite_Imp
    template_name = 'core/flash-impr-details.html'

    def get_context_data(self, *args,**kwargs):
        context = super(FlashImpressionDetails, self).get_context_data(*args, **kwargs)
        # pylint: disable=no-member
        obj = Production_Capacite_Imp.objects.get(id = self.get_object().pk)
        context['id'] = self.get_object().pk
        context['qs'] = Production_Capacite_Imp.objects.filter(date = obj.date).order_by('-ligne')
        date = datetime.datetime.strptime(str(obj.date), '%Y-%m-%d').strftime('%d/%m/%Y')
        context['date'] = date
        context['req'] = 'imprimerie - '.upper() + str(date)
        context['title'] = 'imprimerie - '.upper() + str(date)
        context['shifts'] = list(Flash_Impression.objects.values_list('shift', flat=True).distinct())
        context['formats'] = list(Flash_Impression.objects.values_list('format_fer', flat=True).distinct())
        return context

class EditFlashImp(LoginRequiredMixin, View):
    def post(self, request):
        dic = dict(request.POST)
        del dic['csrfmiddlewaretoken']
        # print(dic)
        nb_real_tandem = int(dic['TANDEM-nbreal'][0])
        nb_real_vern = int(dic['VERNISSEUSE-nbreal'][0])
        # print(nb_real_tandem, nb_real_vern)
        dic_values = dic.items()
        for key, value in dic_values:
            val = list()
            for v in value:
                try:
                    val.append(int(v))
                except ValueError:
                    try:
                        val.append(float(v))
                    except ValueError:
                        try:
                            val.append(datetime.datetime.strptime(v, '%d/%m/%Y').date())
                        except:
                            val.append(v.strip())
            dic[key] = val
        # print(dic)

        mode = dic['mode'][0]
        # building flash impression dic
        date = dic['date'][0]
        begin = 0
        end = nb_real_vern
        print(dic)
        if mode == 'add':
            nb_line = len(dic['lvg'])
        else:
            nb_line = len(dic['id'])
        sum_prod_brute = dict()
        for i in range(0, nb_line):
            sum_prod_brute['prod_brute_' + dic['ligne'][i]] = 0
            flash_imp_dic = dict()
            flash_imp_dic['ligne'] = dic['ligne'][i]
            flash_imp_dic['date'] = date
            for j in range(begin, end):
                flash_imp_dic['hours'] = dic['hours'][j]
                if mode == 'edit':
                    flash_imp_dic['id'] = dic['id_flash'][j]
                else:
                    tab_name = 'Flash_Impression'
                    cursor.execute('SELECT MAX("id") FROM public."' + tab_name + '"')
                    max_id = cursor.fetchone()[0]
                    flash_imp_dic['id'] = max_id + 1
                flash_imp_dic['shift'] = dic['real_shift'][j]
                flash_imp_dic['format_fer'] = dic['format_fer'][j]
                flash_imp_dic['des'] = dic['des'][j]
                flash_imp_dic['nb_psg'] = dic['nb_psg'][j]
                flash_imp_dic['sf_rebut'] = dic['sf_rebut'][j]
                flash_imp_dic['sf_conf'] = dic['sf_conf'][j]
                flash_imp_dic['conduct'] = dic['conduct'][j]
                flash_imp_dic['sf_brut'] = flash_imp_dic['sf_conf'] + flash_imp_dic['sf_rebut']
                try:
                    flash_imp_dic['sf_taux_reb'] = flash_imp_dic['sf_rebut'] / flash_imp_dic['sf_brut']
                except ZeroDivisionError:
                    flash_imp_dic['sf_taux_reb'] = 0
                flash_imp_dic['rebut'] = dic['rebut'][j]
                flash_imp_dic['conf'] = dic['conf'][j]
                flash_imp_dic['brut'] = flash_imp_dic['conf'] + flash_imp_dic['rebut']
                try:
                    flash_imp_dic['taux_reb'] = flash_imp_dic['rebut'] / flash_imp_dic['brut']
                except ZeroDivisionError:
                    flash_imp_dic['taux_reb'] = 0
                sum_prod_brute['prod_brute_' + dic['ligne'][i]] = sum_prod_brute['prod_brute_' + dic['ligne'][i]] + flash_imp_dic['sf_brut'] + flash_imp_dic['brut']
                print(flash_imp_dic)
                print('\n')
                try:
                    obj, created = Flash_Impression.objects.update_or_create(
                        id = flash_imp_dic['id'],
                        defaults = flash_imp_dic
                    )   
                except:
                    if mode == 'add':
                        return redirect('core:add-flash-imp-manual')
                    messages.error(request, 'Une erreur s\'est produite! Réssayez plus tard.')
                    return HttpResponseRedirect(reverse('core:flash-impr-details', kwargs={
                        'pk' : dic['main_id'][0]
                    }))
            begin = nb_real_vern
            end = nb_real_vern + nb_real_tandem
        
        # building capacite prod dic
        if mode == 'add':
            nb_line = len(dic['lvg'])
        else:
            nb_line = len(dic['id'])
        for i in range(0, nb_line):
            cap_imp_dic = dict()
            if mode == 'edit':
                cap_imp_dic['id'] = dic['id_flash'][j]
            else:
                tab_name = 'Production_Capacite_Imp'
                cursor.execute('SELECT MAX("id") FROM public."' + tab_name + '"')
                max_id = cursor.fetchone()[0]
                cap_imp_dic['id'] = max_id + 1
            cap_imp_dic['date'] = date
            cap_imp_dic['shift'] = dic['shift'][i]
            cap_imp_dic['prod_brute'] = sum_prod_brute['prod_brute_' + dic['ligne'][i]]
            cap_imp_dic['cph'] = dic['cph'][i]
            cap_imp_dic['ligne'] = dic['ligne'][i]
            cap_imp_dic['prep_line'] = dic['prep_line'][i]
            cap_imp_dic['pause_eat'] = dic['pause_eat'][i]
            cap_imp_dic['chg_form'] = dic['chg_form'][i]
            cap_imp_dic['lvg'] = dic['lvg'][i]
            cap_imp_dic['manque_prog'] = dic['manque_prog'][i]
            cap_imp_dic['panne'] = dic['panne'][i]
            cap_imp_dic['reglages'] = dic['reglages'][i]
            cap_imp_dic['autres'] = dic['autres'][i]
            cap_imp_dic['abs'] = dic['abs'][i]
            cap_imp_dic['arrets'] = cap_imp_dic['prep_line'] + cap_imp_dic['pause_eat'] + cap_imp_dic['chg_form'] + cap_imp_dic['lvg'] + cap_imp_dic['manque_prog'] + cap_imp_dic['panne'] + cap_imp_dic['reglages'] + cap_imp_dic['autres'] + cap_imp_dic['abs']
            # calcul des taux et de la capacite
            # print(round(cap_imp_dic['cph'] * cap_imp_dic['shift'] * flash_imp_dic['hours'] * cap_imp_dic['taux_util']))
            try:
                cap_imp_dic['taux_util'] = ( (cap_imp_dic['shift'] * flash_imp_dic['hours'] * 60) - cap_imp_dic['arrets'] ) / (cap_imp_dic['shift'] * flash_imp_dic['hours'] * 60)
            except:
                cap_imp_dic['taux_util'] = np.nan
            try:
                cap_imp_dic['capacite_prod'] = round(cap_imp_dic['cph'] * cap_imp_dic['shift'] * flash_imp_dic['hours'] * cap_imp_dic['taux_util'])
            except:
                cap_imp_dic['capacite_prod'] = np.nan
            try:
                cap_imp_dic['taux_prod'] = cap_imp_dic['prod_brute'] / cap_imp_dic['capacite_prod']
            except:
                cap_imp_dic['taux_prod'] = np.nan
            print(cap_imp_dic)
            print('\n')
            try:
                obj, created = Production_Capacite_Imp.objects.update_or_create(
                    id = cap_imp_dic['id'],
                    defaults = cap_imp_dic
                )
            except:
                if mode == 'add':
                    return redirect('core:add-flash-imp-manual')
                messages.error(request, 'Une erreur s\'est produite! Réssayez plus tard.')
                return HttpResponseRedirect(reverse('core:flash-impr-details', kwargs={
                    'pk' : dic['main_id'][0]
                }))
        messages.success(request, 'Modification effectuée avec succès!')
        if mode == 'add':
            return redirect('core:flash-impr-summary')
        return HttpResponseRedirect(reverse('core:flash-impr-details', kwargs={
            'pk' : dic['main_id'][0]
        }))

@login_required
def add_cap_prod_imp_man(request):
    shifts = list(Flash_Impression.objects.order_by('shift').values_list('shift', flat=True).distinct())
    shifts = list(map(lambda s: s.strip(), shifts))
    shifts = list(set(shifts))
    l = [1, 'shift', 3.5]
    print(l)
    context = {
        'title' : "Ajout - flash journalier d'impression".upper(),
        'req' : "Ajout - flash journalier d'impression".upper(),
        'lines': list(Flash_Impression.objects.values_list('ligne', flat=True).distinct().order_by('-ligne')),
        'shifts': shifts,
    }
    return render(request, 'core/add-flash-imp-manual.html', context)

