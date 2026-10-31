from django.db import migrations


ROLE_PERMISSIONS = {
    'SUPER_ADMIN': [
        'cadre_recommendations:campaign:manage',
        'cadre_recommendations:task:view',
        'cadre_recommendations:task:submit',
        'cadre_recommendations:result:view',
    ],
    'POLITICAL_OFFICE_ADMIN': [
        'cadre_recommendations:campaign:manage',
        'cadre_recommendations:task:view',
        'cadre_recommendations:task:submit',
        'cadre_recommendations:result:view',
    ],
    'DEPT_MANAGER': [
        'cadre_recommendations:task:view',
        'cadre_recommendations:task:submit',
    ],
    'CADRE_SELF': [
        'cadre_recommendations:task:view',
        'cadre_recommendations:task:submit',
    ],
    'ANALYST': [
        'cadre_recommendations:result:view',
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
        ('cadre_recommendations', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(grant_permissions, noop),
    ]
