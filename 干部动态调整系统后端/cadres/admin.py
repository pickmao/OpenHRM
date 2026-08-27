from django.contrib import admin
from .models import PersonnelRoster, Cadre, CadreResume


@admin.register(PersonnelRoster)
class PersonnelRosterAdmin(admin.ModelAdmin):
    """花名册管理"""
    list_display = [
        'serial_number', 'name', 'department', 'gender', 'age',
        'political_status', 'position', 'police_rank', 'phone'
    ]
    list_filter = ['department', 'gender', 'political_status', 'police_rank']
    search_fields = ['name', 'department', 'police_number', 'id_card']
    ordering = ['serial_number', 'department', 'name']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('基本信息', {
            'fields': ('serial_number', 'name', 'department', 'gender', 'age', 'birth_date',
                       'ethnicity', 'native_place', 'household_registration')
        }),
        ('工作信息', {
            'fields': ('working_years', 'join_work_date', 'join_prison_date', 'continuous_service_date',
                       'has_2years_grassroots')
        }),
        ('政治信息', {
            'fields': ('political_status', 'join_party_date')
        }),
        ('职务信息', {
            'fields': ('position', 'promotion_category', 'position_category', 'current_position_years',
                       'current_position_date', 'position_level', 'position_rank')
        }),
        ('领导职务信息', {
            'fields': ('same_level_leadership_years', 'same_level_leadership_date',
                       'same_level_rank_years', 'same_level_rank_date')
        }),
        ('职级信息', {
            'fields': ('current_rank_years', 'current_rank_date', 'calculation_start_date')
        }),
        ('警员职级信息', {
            'fields': ('police_rank', 'police_rank_start_date', 'first_set_rank', 'first_set_rank_date',
                       'first_promote_rank', 'first_promote_rank_date', 'work_charge')
        }),
        ('教育信息', {
            'fields': ('fulltime_education', 'fulltime_school', 'fulltime_major', 'fulltime_degree',
                       'fulltime_start_date', 'fulltime_graduate_date',
                       'inservice_education', 'inservice_school', 'inservice_form',
                       'inservice_major', 'inservice_degree', 'inservice_start_date', 'inservice_graduate_date',
                       'highest_education', 'highest_school', 'education_level', 'highest_major',
                       'highest_degree', 'major_category')
        }),
        ('警衔警号', {
            'fields': ('police_title', 'police_number')
        }),
        ('专业资格', {
            'fields': ('profession_name', 'profession_level', 'technical_title',
                       'counseling_cert_level', 'english_level', 'cert_level')
        }),
        ('部门工作信息', {
            'fields': ('dept_work_years', 'dept_work_date', 'unit_work_years', 'enter_unit_date',
                       'enter_unit_form', 'identity_source', 'military_experience')
        }),
        ('联系信息', {
            'fields': ('id_card', 'id_card_inconsistent', 'phone')
        }),
        ('备注', {
            'fields': ('remark', 'quarterly_remark')
        }),
        ('系统信息', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Cadre)
class CadreAdmin(admin.ModelAdmin):
    """干部主档管理"""
    list_display = ['cadre_code', 'name', 'gender', 'age', 'education_level', 'current_position', 'status']
    list_filter = ['status', 'gender', 'education_level']
    search_fields = ['name', 'cadre_code']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CadreResume)
class CadreResumeAdmin(admin.ModelAdmin):
    """干部履历管理"""
    list_display = ['cadre', 'org_unit', 'position_title', 'start_date', 'end_date']
    list_filter = ['start_date', 'end_date']
    search_fields = ['cadre__name', 'position_title']
    readonly_fields = ['created_at']
