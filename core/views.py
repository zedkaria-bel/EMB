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
from sqlalchemy import create_engine
import datetime
from django.utils import timezone
from django.db.models.fields import BLANK_CHOICE_DASH
from django.template.loader import render_to_string
import calendar
from dateutil.relativedelta import relativedelta
from django.views.decorators.csrf import csrf_protect
import pandas as pd
import numpy as np
import json
import re
from django.shortcuts import render
# pylint: disable=import-error
from django_pandas.io import read_frame
from .models import (
    Production,
    Vente,
    Trs,
    Tcr,
)

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