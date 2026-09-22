from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import PersonnelRoster
from .org_alignment import sync_memberships_from_roster


@receiver(post_save, sender=PersonnelRoster)
def sync_membership_when_roster_department_changes(sender, instance, created, update_fields, **kwargs):
    if update_fields and 'department' not in update_fields:
        return
    sync_memberships_from_roster(instance)
