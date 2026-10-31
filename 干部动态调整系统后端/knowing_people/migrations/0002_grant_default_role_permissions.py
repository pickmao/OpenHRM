from django.db import migrations


ROLE_PERMISSIONS = {
    'SUPER_ADMIN': [
        'knowing_people:campaign:manage',
        'knowing_people:task:view',
        'knowing_people:task:submit',
        'knowing_people:result:view',
    ],
    'POLITICAL_OFFICE_ADMIN': [
        'knowing_people:campaign:manage',
        'knowing_people:task:view',
        'knowing_people:task:submit',
        'knowing_people:result:view',
    ],
    'DEPT_MANAGER': [
        'knowing_people:task:view',
        'knowing_people:task:submit',
    ],
    'CADRE_SELF': [
        'knowing_people:task:view',
        'knowing_people:task:submit',
    ],
    'ANALYST': [
        'knowing_people:result:view',
    ],
}


def grant_permissions(apps, schema_editor):
    Role = apps.get_model('accounts', 'Role')
    for code, extra in ROLE_PERMISSIONS.items():
        role = Role.objects.filter(code=code).first()
        if not role:
            continue
        permissions = list(role.permissions or [])
        changed = False
        for item in extra:
            if item not in permissions:
                permissions.append(item)
                changed = True
        if changed:
            role.permissions = permissions
            role.save(update_fields=['permissions'])


def noop(apps, schema_editor):
    return None


class Migration(migrations.Migration):

    dependencies = [
        ('knowing_people', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(grant_permissions, noop),
    ]
