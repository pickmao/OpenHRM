from rest_framework import serializers
from .models import PersonnelRoster, Cadre, CadreResume


class PersonnelRosterSerializer(serializers.ModelSerializer):
    """花名册序列化器"""
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = PersonnelRoster
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def validate_id_card(self, value):
        """验证身份证号格式"""
        if value and len(value) != 18:
            raise serializers.ValidationError("身份证号必须为18位")
        return value

    def validate_police_number(self, value):
        """验证警号格式"""
        if value and not value.isdigit():
            raise serializers.ValidationError("警号必须为数字")
        return value


class PersonnelRosterListSerializer(serializers.ModelSerializer):
    """花名册列表序列化器（简化版）"""
    gender_display = serializers.CharField(source='get_gender_display', read_only=True)
    political_status_display = serializers.CharField(source='get_political_status_display', read_only=True)
    police_rank_display = serializers.CharField(source='get_police_rank_display', read_only=True)
    police_title_display = serializers.CharField(source='get_police_title_display', read_only=True)

    class Meta:
        model = PersonnelRoster
        fields = [
            'id', 'serial_number', 'name', 'department', 'gender', 'gender_display',
            'age', 'political_status', 'political_status_display',
            'position', 'police_rank', 'police_rank_display',
            'police_title', 'police_title_display',
            'police_number', 'phone', 'education_level', 'highest_education'
        ]


class CadreSerializer(serializers.ModelSerializer):
    """干部主档序列化器"""
    age = serializers.IntegerField(read_only=True)
    gender_display = serializers.CharField(source='get_gender_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Cadre
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class CadreResumeSerializer(serializers.ModelSerializer):
    """干部履历序列化器"""
    cadre_name = serializers.CharField(source='cadre.name', read_only=True)
    org_unit_name = serializers.CharField(source='org_unit.name', read_only=True)

    class Meta:
        model = CadreResume
        fields = '__all__'
        read_only_fields = ['id', 'created_at']
