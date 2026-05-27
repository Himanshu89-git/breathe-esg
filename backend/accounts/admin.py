from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Tenant

admin.site.register(Tenant)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'tenant', 'role']
    list_filter = ['role', 'tenant']
    fieldsets = UserAdmin.fieldsets + (
        ('Breathe ESG', {'fields': ('tenant', 'role')}),
    )
