from django.contrib import admin
from .models import ForexPair, Portfolio, MacroData

admin.site.register(ForexPair)
admin.site.register(Portfolio)
admin.site.register(MacroData)