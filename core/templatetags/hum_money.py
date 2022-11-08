from datetime import date
from django import template
import calendar
import os
import locale
from ..models import Flash_Impression, Tcr, User

locale.setlocale(locale.LC_ALL, 'fr_FR')

register = template.Library()

@register.filter
def space_digits(amount):
    return str(amount).replace(',', " ")

@register.filter(name='times') 
def times(number):
    return range(1, number)

@register.filter
def month_name(month_number):
    if isinstance(month_number, str):
        month_number = int(month_number)
    return calendar.month_name[month_number].upper()

@register.filter
def negative(num):
    if isinstance(num, int) or isinstance(num, float):
        return num < 0

@register.filter
def get_raw_username(username):
    usr = User.objects.get(username=username)
    return usr.first_name.upper()[0] + usr.first_name.lower()[1:] + ' ' + usr.last_name.upper()

@register.filter
def get_username(usr):
    # pylint: disable=no-member
    # print(usr)
    user = User.objects.get(username=usr)
    return user.first_name.upper()[0] + user.first_name.lower()[1:] + ' ' + user.last_name.upper()

@register.filter
def get_tcr(audit):
    return Tcr.objects.get(id = int(audit.line_id))

@register.filter
def get_tcr_info(obj):
    return obj.date.date().strftime('%B').upper() + ' ' + obj.date.date().strftime('%Y')

@register.filter
def to_int(str):
    try:
        return int(str)
    except ValueError:
        pass

@register.filter
def filter_unit(qs, unit):
    return qs.filter(unite = unit)

@register.simple_tag
def filter_cat(qs, unit, cat):
    return qs.filter(unite = unit, category = cat)

@register.filter
def count(qs):
    return len(qs)

@register.filter
def get_unit_qs(qs, unit):
    return qs.get(unite = unit)

@register.filter
def get_field(row, field):
    return getattr(row, field)

@register.filter
def get_flash_qs(cap_prod):
    return Flash_Impression.objects.filter(
        date = cap_prod.date,
        ligne = cap_prod.ligne
    )

@register.filter
def get_flash_obj(cap_prod, field):
    return Flash_Impression.objects.get(
        date = cap_prod.date,
        ligne = cap_prod.ligne
    )[field]

@register.filter
def get_percent(nb):
    try:
        return round(nb * 100, 2)
    except:
        return 0

@register.filter
def get_flash_count(obj):
    return obj.count()

@register.filter
def len_str(str):
    return len(str)

@register.filter
def get_str_st_part(str):
    return str[:31]