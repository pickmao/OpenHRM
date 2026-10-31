from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('knowing_people', '0002_grant_default_role_permissions')]
    operations = [
        migrations.RemoveConstraint(model_name='inspectiontask', name='unique_knowing_people_task_per_form'),
        migrations.AddConstraint(
            model_name='inspectiontask',
            constraint=models.UniqueConstraint(fields=['campaign', 'form_type', 'assignee', 'branch'],
                condition=models.Q(branch__isnull=False), name='unique_kp_task_per_branch'),
        ),
        migrations.AddConstraint(
            model_name='inspectiontask',
            constraint=models.UniqueConstraint(fields=['campaign', 'form_type', 'assignee'],
                condition=models.Q(branch__isnull=True), name='unique_kp_task_without_branch'),
        ),
    ]
