from django import template
import calendar
import os
import locale

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
    return calendar.month_name[month_number].upper()

@register.filter
def negative(num):
    if isinstance(num, int) or isinstance(num, float):
        return num < 0

@register.filter
def get_username(user):
    return user.first_name.upper()[0] + user.first_name.lower()[1:] + ' ' + user.last_name.upper()