# models.py

from django.db import models

class BreakGlassUser(models.Model):
    organization_id = models.CharField(max_length=255)  # Clerk org_id
    email = models.EmailField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.email} @ {self.organization_id}"