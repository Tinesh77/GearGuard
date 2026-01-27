from django.contrib import admin
from .models import Equipment, MaintenanceTeam, MaintenanceRequest
# Register your models here.
admin.site.register(Equipment)
admin.site.register(MaintenanceTeam)
admin.site.register(MaintenanceRequest)

