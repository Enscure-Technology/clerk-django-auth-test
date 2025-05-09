from django.contrib import admin
from .models import BreakGlassUser

@admin.register(BreakGlassUser)
class BreakGlassUserAdmin(admin.ModelAdmin):
    list_display = ("email", "organization_id", "is_active")
    list_filter = ("organization_id", "is_active")
    search_fields = ("email",)