from django import template
from django.utils.feedgenerator import rfc3339_date

register = template.Library()

register.filter('rfc3339', rfc3339_date)