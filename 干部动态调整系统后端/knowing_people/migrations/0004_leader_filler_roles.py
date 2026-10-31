from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('knowing_people', '0003_task_branch_identity')]
    operations = [migrations.AlterField(
        model_name='inspectiontask', name='filler_role',
        field=models.CharField('填报身份', max_length=30, default='MANUAL', choices=[
            ('MIDDLE_LEADER', '中层领导（含团队负责人）'),
            ('BRANCH_LEADERSHIP', '党支部班子'),
            ('BRANCH_SECRETARY', '党支部书记'),
            ('BRANCH_DEPUTY_SECRETARY', '党支部副书记'),
            ('BRANCH_COMMITTEE', '党支部支委'),
            ('BRANCH_STAFF', '本支部民警职工'),
            ('POLITICAL_LEADER', '政工领导'),
            ('POLITICAL_DIRECTOR', '政治处主任'),
            ('POLITICAL_EXECUTIVE_DEPUTY', '政治处常务副主任'),
            ('POLITICAL_DEPUTY', '政治处副主任'),
            ('PRISON_LEADER', '其他监狱领导'),
            ('PRINCIPAL_LEADER', '主要评价监狱领导'),
            ('INSPECTION_TALKER', '谈话研判人员'),
            ('MANUAL', '管理员指定'),
        ]),
    )]
