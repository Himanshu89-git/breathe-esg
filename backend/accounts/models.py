from django.contrib.auth.models import AbstractUser
from django.db import models


class Tenant(models.Model):
    """Represents a client company (multi-tenancy root)."""
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class User(AbstractUser):
    ROLE_ANALYST = 'analyst'
    ROLE_ADMIN = 'admin'
    ROLE_AUDITOR = 'auditor'
    ROLE_CHOICES = [
        (ROLE_ANALYST, 'Analyst'),
        (ROLE_ADMIN, 'Admin'),
        (ROLE_AUDITOR, 'Auditor'),
    ]

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, null=True, blank=True,
        related_name='users'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_ANALYST)

    def __str__(self):
        return f"{self.username} ({self.tenant})"
