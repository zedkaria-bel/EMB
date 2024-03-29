# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.


import datetime

from django.apps import apps
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.shortcuts import reverse
# pylint: disable=import-error
from django_model_changes import ChangesMixin, post_change
from embapp.middleware import get_current_user

op_choices = (
    (1, 'AJOUT'),
    (2, 'MODIFICATION'),
    (3, 'SUPPRESSION')
)

# Class for Audit
class AuditLog(models.Model):
    id = models.AutoField(db_column='ID', primary_key=True)
    tab = models.TextField(null=True, blank=True)
    line_id = models.TextField(null=True, blank=True)
    op = models.TextField(blank=True, null=True, choices=op_choices)
    dt = models.DateTimeField(blank=True, null=True)
    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE)
    details = models.JSONField()

    class Meta:
        db_table = 'AuditLog'
    
    def get_line_url(self):
        # pylint: disable=no-member
        model = apps.get_model('core', self.tab)
        obj = model.objects.get(
            id = int(self.line_id)
        )
        return obj.get_absolute_url()
    
    def get_absolute_url(self):
        return reverse('core:audit-details', kwargs = {
            'pk' : self.pk
        })

class MetaWorkforce(models.Model):
    id = models.AutoField(primary_key=True)
    unit = models.TextField(blank=True, null=True)
    product = models.TextField(blank=True, null=True)
    dim = models.TextField(blank=True, null=True)
    num_instal = models.TextField(blank=True, null=True)
    code = models.TextField(blank=True, null=True)
    cob = models.TextField(blank=True, null=True)
    pds_brut_1000 = models.FloatField(blank=True, null=True)
    pds_net_1000 = models.FloatField(blank=True, null=True)
    nb_instal = models.IntegerField(blank=True, null=True)
    phase_fab = models.IntegerField(blank=True, null=True)
    date = models.DateField()

    class Meta:
        db_table = 'Workforce_Meta'

class ConsomWorkforce(models.Model):
    id = models.AutoField(primary_key=True)
    code = models.TextField(blank=True, null=True)
    des = models.TextField(blank=True, null=True)
    nb_post = models.IntegerField(blank=True, null=True)
    nb_agent = models.FloatField(blank=True, null=True)
    real_cad_hor = models.IntegerField(blank=True, null=True)
    time_consum_thsd = models.FloatField(blank=True, null=True)
    mode = models.TextField(blank=True, null=True)
    id_meta = models.ForeignKey(MetaWorkforce, on_delete=models.CASCADE, db_column='id_meta')

    class Meta:
        db_table = 'Workforce_Consom'

class AbstractProduction(models.Model):
    id = models.IntegerField(db_column='ID', primary_key=True)  # Field name made lowercase.
    unite = models.TextField(db_column='Unité', blank=True, null=True)  # Field name made lowercase.
    obj = models.BigIntegerField(db_column='Objectif', blank=True, null=True)  # Field name made lowercase.
    capacite_jour = models.BigIntegerField(db_column='Capacité jour', blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    volume = models.TextField(db_column='Volume', blank=True, null=True)  # Field name made lowercase.
    category = models.TextField(blank=True, null=True)
    produit = models.TextField(blank=True, null=True)

    class Meta:
        abstract = True

class Production(ChangesMixin, AbstractProduction):
    ligne = models.TextField(db_column='Ligne', blank=True, null=True)  # Field name made lowercase.
    des = models.TextField(db_column='Désignation', blank=True, null=True)  # Field name made lowercase.
    client = models.TextField(db_column='Client', blank=True, null=True)  # Field name made lowercase.
    brute_jour = models.BigIntegerField(db_column='Brute_jour', blank=True, null=True)  # Field name made lowercase.
    conforme_jour = models.BigIntegerField(db_column='Conforme_jour', blank=True, null=True)  # Field name made lowercase.
    rebut_jour = models.BigIntegerField(db_column='Rebut_jour', blank=True, null=True)  # Field name made lowercase.
    taux_jour = models.BigIntegerField(db_column='Taux_jour', blank=True, null=True)  # Field name made lowercase.
    brute_mois = models.BigIntegerField(db_column='Brute_mois', blank=True, null=True)  # Field name made lowercase.
    conforme_mois = models.BigIntegerField(db_column='Conforme_mois', blank=True, null=True)  # Field name made lowercase.
    rebut_mois = models.BigIntegerField(db_column='Rebut_mois', blank=True, null=True)  # Field name made lowercase.
    taux_real = models.FloatField(db_column='Taux_real', blank=True, null=True)  # Field name made lowercase.
    taux_rebut = models.FloatField(db_column='Taux_rebut', blank=True, null=True)  # Field name made lowercase.
    pu_cout_revient = models.FloatField(db_column='PU_cout_revient', blank=True, null=True)  # Field name made lowercase.
    montant_journee_coutrev = models.FloatField(db_column='montant_journee_coutRev', blank=True, null=True)  # Field name made lowercase.
    montantcumul_coutrev = models.FloatField(db_column='MontantCumul_coutRev', blank=True, null=True)  # Field name made lowercase.
    pu_prix_vente = models.FloatField(db_column='PU_prix_vente', blank=True, null=True)  # Field name made lowercase.
    montant_journee_prix_vente = models.FloatField(blank=True, null=True)
    montantcumul_prix_vente = models.FloatField(db_column='MontantCumul_prix_vente', blank=True, null=True)  # Field name made lowercase.

    class Meta(AbstractProduction.Meta):
        db_table = 'Production'
    
    def get_absolute_url(self):
        return reverse('core:prod-details', kwargs = {
            'pk' : self.pk
        })
    
    def get_user(self, request):
        return request.user

class ObjectifCapaciteProduction(ChangesMixin, AbstractProduction):
    class Meta(AbstractProduction.Meta):
        db_table = 'OBJ_CAP_PRODUCTION'

class Tcr(ChangesMixin, models.Model):
    id = models.AutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    unite = models.TextField(db_column='Unité', blank=True, null=True)  # Field name made lowercase.
    ca = models.FloatField(db_column="Chiffre d'affaires", blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    cessions_et_produits = models.BigIntegerField(db_column='Cessions et produits', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    var_stock_fini_encours = models.FloatField(db_column='Variation stocks produits finis et en cours', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    prod_immob = models.FloatField(db_column='Production immobilisée', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    subv_expl = models.BigIntegerField(db_column="Subventions d'exploitation", blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    prod_exerc = models.FloatField(db_column="PRODUCTION DE L'EXERCICE (I)", blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    achats_consom = models.FloatField(db_column='Achats consommes', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.    services_extérieurs_et_autres_consommation = models.FloatField(db_column='Services extérieurs et Autres consommation', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    serv_ext_other_consom = models.FloatField(db_column='Services extérieurs et Autres consommation', blank=True, null=True)
    consom_inter_unit = models.BigIntegerField(db_column='Consommation inter-unités', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    consom_exerc = models.FloatField(db_column="CONSOMMATIONS DE L'EXERCICE (II)", blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    v_ajoute = models.FloatField(db_column='VALEUR AJOUTEE (I - II)', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    charge_pers = models.FloatField(db_column='Charges de personnel', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    impot_tax_vers_ass = models.BigIntegerField(db_column='Impôts, taxes et versements assimiles', blank=True, null=True)  # Field name made lowercase. 
    exced_brut_exploit = models.FloatField(db_column="\xa0EXCEDENT BRUT D'EXPLOITATION", blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it started with '_'.
    other_prod_op = models.FloatField(db_column='Autres produits opérationnels', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    other_charge_op = models.FloatField(db_column='Autres charges opérationnelles', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    prod_inter_unit = models.BigIntegerField(db_column='Produits inter unités', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    charge_inter_unit = models.BigIntegerField(db_column='Charges inter unités', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    dot_amort_prov_pert_val = models.FloatField(db_column='Dotation aux amortissements, provisions et pertes de valeur ', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    repr_pert_val_prov = models.BigIntegerField(db_column='Reprise sur pertes de valeur et provisions', blank=True, null=True)  # Field name made 
    res_op = models.FloatField(db_column=' RESULTAT OPERATIONNEL', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it started with '_'.
    prod_fin = models.FloatField(db_column='Produits financiers', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    charge_financ = models.FloatField(db_column='Charges financières', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    res_financ = models.FloatField(db_column='RESULTAT FINANCIER', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    res_ord_pre_impot = models.FloatField(db_column='RESULTAT ORDINAIRE AVANT IMPOTS (V + VI)', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    impot_exig_res_ord = models.BigIntegerField(db_column='Impôts exigibles sur résultats ordinaires', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    impot_diff_res_ord = models.BigIntegerField(db_column='Impôts différés (Variations) sur résultats ordinaires', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    tot_prod_act_ord = models.FloatField(db_column='Total des produits des activités ordinaires', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    tot_charge_act_ord = models.FloatField(db_column='Total des charges des activités ordinaires', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    res_net_act_ord = models.FloatField(db_column='RESULTAT NET DES ACTIVITES ORDINAIRES ', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    elem_extraord_prod = models.BigIntegerField(db_column='Eléments extraordinaires produits', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    elem_extraord_charge = models.BigIntegerField(db_column='Eléments extraordinaires charges', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    res_extraord = models.BigIntegerField(db_column='RESULTAT EXTRAORDINAIRE ', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    res_net_exerc = models.FloatField(db_column="RESULTAT NET DE L'EXERCICE", blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    date = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'TCR'

class Trs(ChangesMixin, models.Model):
    id = models.IntegerField(db_column='ID', primary_key=True)  # Field name made lowercase.
    unite = models.TextField(db_column='Unité', blank=True, null=True)  # Field name made lowercase.
    ligne = models.TextField(db_column='Ligne', blank=True, null=True)  # Field name made lowercase.
    ecarts_cadences = models.BigIntegerField(db_column='Ecarts_Cadences', blank=True, null=True)  # Field name made lowercase.
    arret_plan = models.BigIntegerField(db_column='Arret_Plan', blank=True, null=True)  # Field name made lowercase.
    arret_non_plan = models.BigIntegerField(db_column='Arret_non_Plan', blank=True, null=True)  # Field name made lowercase.
    capacite_theo = models.BigIntegerField(db_column='Capacite_Theo', blank=True, null=True)  # Field name made lowercase.
    qte_prod = models.BigIntegerField(db_column='Qte_Prod', blank=True, null=True)  # Field name made lowercase.
    qte_conf = models.BigIntegerField(db_column='Qte_Conf', blank=True, null=True)  # Field name made lowercase.
    qte_rebut = models.BigIntegerField(db_column='Qte_Rebut', blank=True, null=True)  # Field name made lowercase.
    temps_ouv = models.BigIntegerField(db_column='Temps_Ouv', blank=True, null=True)  # Field name made lowercase.
    temps_fct = models.BigIntegerField(db_column='Temps_Fct', blank=True, null=True)  # Field name made lowercase.
    temps_req = models.BigIntegerField(db_column='Temps_Req', blank=True, null=True)  # Field name made lowercase.
    taux_dispo = models.FloatField(db_column='Taux_Dispo', blank=True, null=True)  # Field name made lowercase.
    temps_net = models.BigIntegerField(db_column='Temps_Net', blank=True, null=True)  # Field name made lowercase.
    taux_perf = models.FloatField(db_column='Taux_Perf', blank=True, null=True)  # Field name made lowercase.
    temps_util = models.FloatField(db_column='Temps_Util', blank=True, null=True)  # Field name made lowercase.
    taux_qualit = models.FloatField(db_column='Taux_Qualit', blank=True, null=True)  # Field name made lowercase.
    trs = models.FloatField(db_column='TRS', blank=True, null=True)  # Field name made lowercase.
    date = models.DateField(blank=True, null=True)

    class Meta:
        db_table = 'TRS'

    def get_absolute_url(self):
        return reverse('core:trs-details', kwargs = {
            'pk' : self.pk
        })

class Vente(ChangesMixin, models.Model):
    id = models.IntegerField(db_column='ID', primary_key=True)  # Field name made lowercase.
    unite = models.TextField(db_column='Unité', blank=True, null=True)  # Field name made lowercase.
    des = models.TextField(db_column='Désignation', blank=True, null=True)  # Field name made lowercase.
    client = models.TextField(db_column='Client', blank=True, null=True)  # Field name made lowercase.
    qte_journ = models.BigIntegerField(db_column='Qte_Journ', blank=True, null=True)  # Field name made lowercase.
    qte_cumul = models.BigIntegerField(db_column='Qte_Cumul', blank=True, null=True)  # Field name made lowercase.
    pu = models.TextField(db_column='PU', blank=True, null=True)  # Field name made lowercase.
    montant_journee = models.FloatField(db_column='Montant_journee', blank=True, null=True)  # Field name made lowercase.
    montant_cumul = models.FloatField(db_column='Montant_cumul', blank=True, null=True)  # Field name made lowercase.
    date = models.DateField(blank=True, null=True)
    category = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'Vente'

    def get_absolute_url(self):
        return reverse('core:sale-details', kwargs = {
            'pk' : self.pk
        })

    def get_user(self, request):
        return request.user

class Profile(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete = models.CASCADE)
    poste = models.TextField(null=True, blank = True)

    class Meta:
        db_table = 'Profile'

class Flash_Impression(ChangesMixin, models.Model):
    id = models.AutoField(primary_key=True)
    hours = models.IntegerField(null = True, blank = True)
    shift = models.TextField(null = True, blank = True)
    format_fer = models.TextField(null = True, blank = True)
    des = models.TextField(null = True, blank = True)
    nb_psg = models.IntegerField(null = True, blank = True)
    sf_brut = models.IntegerField(null = True, blank = True)
    sf_rebut = models.IntegerField(null = True, blank = True)
    sf_conf = models.IntegerField(null = True, blank = True)
    sf_taux_reb = models.FloatField(null = True, blank = True)
    brut = models.IntegerField(null = True, blank = True)
    rebut = models.IntegerField(null = True, blank = True)
    conf = models.IntegerField(null = True, blank = True)
    taux_reb = models.FloatField(null = True, blank = True)
    conduct = models.TextField(null = True, blank = True)
    ligne = models.TextField(null = True, blank = True)
    date = models.DateField(null = True, blank = True)

    class Meta:
        db_table = 'Flash_Impression'

class Production_Capacite_Imp(ChangesMixin, models.Model):
    id = models.AutoField(primary_key=True)
    date = models.DateField(blank=True, null=True)
    arrets = models.IntegerField(blank=True, null=True)
    prod_brute = models.IntegerField(null=True, blank=True)
    shift = models.IntegerField(null=True, blank=True)
    taux_util = models.FloatField(null=True, blank=True)
    capacite_prod = models.IntegerField(blank=True, null=True)
    taux_prod = models.FloatField(null=True, blank=True)
    ligne = models.TextField(null=True, blank=True)
    cph = models.IntegerField(blank=True, null=True)
    prep_line = models.IntegerField(blank=True, null=True)
    pause_eat = models.IntegerField(blank=True, null=True)
    chg_form = models.IntegerField(blank=True, null=True)
    lvg = models.IntegerField(blank=True, null=True)
    manque_prog = models.IntegerField(blank=True, null=True)
    descr = models.TextField(blank=True, null=True, max_length=300)
    panne = models.IntegerField(blank=True, null=True)
    reglages = models.IntegerField(blank=True, null=True)
    autres = models.IntegerField(blank=True, null=True)
    abs = models.IntegerField(blank=True, null=True)
    nb_feuill_pre_arret = models.IntegerField(blank=True, null=True, default=None)
    nb_feuill_post_arret = models.IntegerField(blank=True, null=True, default=None)

    class Meta:
        db_table = 'Production_Capacite_Imp'
    
    def get_absolute_url(self):
        return reverse('core:flash-impr-details', kwargs = {
            'pk' : self.pk
        })

class Impr_Arrets_Teams(models.Model):
    id = models.AutoField(primary_key=True)
    date = models.DateField(blank=True, null=True)
    line = models.TextField(blank=True, null=True)
    team = models.IntegerField(null=True, blank=True)
    prep_line = models.IntegerField(blank=True, null=True)
    pause_eat = models.IntegerField(blank=True, null=True)
    chg_form = models.IntegerField(blank=True, null=True)
    lvg = models.IntegerField(blank=True, null=True)
    manque_prog = models.IntegerField(blank=True, null=True)
    descr = models.TextField(blank=True, null=True, max_length=300)
    panne = models.IntegerField(blank=True, null=True)
    reglages = models.IntegerField(blank=True, null=True)
    autres = models.IntegerField(blank=True, null=True)
    abs = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'Impr_Arrets_Teams'


@receiver(post_save, sender=User)
def update_user_profile(sender, instance, created, **kwargs):
    if created:
        # pylint: disable=E1101
        Profile.objects.create(user=instance)
        instance.profile.save()

def do_something_if_changed(sender, instance, **kwargs):
    tab = sender._meta.db_table
    max_id = sender.objects.latest('id').id
    try:
        obj = sender.objects.get(pk=instance.pk)
        op = 'add'
    except:
        op = 'del'
    if op == 'add':
        line_id = str(instance.pk)
        dt = datetime.datetime.now()
        user = get_current_user()
        if tab == 'TCR':
            max_id = instance.pk
        if max_id == instance.pk:
            op = op_choices[0][1]
            details = obj.previous_state()
            details['date'] = str(details['date'])
        else:
            op = op_choices[1][1]
            details = instance.old_changes()
        # pylint: disable=no-member
        obj = AuditLog.objects.create(
            tab = tab,
            line_id = line_id,
            op = op,
            dt = dt,
            user = user,
            details = details
        )

post_change.connect(do_something_if_changed, Production)
post_change.connect(do_something_if_changed, Vente)
post_change.connect(do_something_if_changed, Trs)
post_change.connect(do_something_if_changed, Tcr)
