from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.users.models import User
from apps.doctors.models import Doctor

class Command(BaseCommand):
    help = 'Setup user groups and permissions'

    def handle(self, *args, **options):
        # Create groups
        admin_group, created = Group.objects.get_or_create(name='Administrators')
        hospital_admin_group, created = Group.objects.get_or_create(name='Hospital Administrators')
        doctor_group, created = Group.objects.get_or_create(name='Doctors')
        patient_group, created = Group.objects.get_or_create(name='Patients')

        # Get content types
        user_ct = ContentType.objects.get_for_model(User)
        doctor_ct = ContentType.objects.get_for_model(Doctor)

        # Admin permissions (full access)
        admin_permissions = Permission.objects.filter(
            content_type__in=[user_ct, doctor_ct]
        )
        admin_group.permissions.set(admin_permissions)

        # Hospital admin permissions (limited)
        hospital_admin_permissions = Permission.objects.filter(
            content_type=doctor_ct,
            codename__in=['view_doctor', 'change_doctor']
        )
        hospital_admin_group.permissions.set(hospital_admin_permissions)

        # Doctor permissions (own profile)
        doctor_permissions = Permission.objects.filter(
            content_type=doctor_ct,
            codename__in=['view_doctor', 'change_doctor']
        )
        doctor_group.permissions.set(doctor_permissions)

        self.stdout.write(
            self.style.SUCCESS('Successfully created groups and permissions')
        )