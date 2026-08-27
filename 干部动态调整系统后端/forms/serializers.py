from rest_framework import serializers

from .models import DispatchBatch, DispatchRule, FormSubmission, FormTask, FormTemplate


class FormTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormTemplate
        fields = [
            'id', 'code', 'name', 'version', 'description', 'schema_json', 'scoring_rule_json',
            'source_file', 'source_file_name', 'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']


class DispatchRuleSerializer(serializers.ModelSerializer):
    template_code = serializers.CharField(source='template.code', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)

    class Meta:
        model = DispatchRule
        fields = [
            'id', 'batch', 'template', 'template_code', 'template_name', 'receiver_type',
            'receiver_expr_json', 'target_type', 'target_expr_json', 'created_at', 'created_by',
        ]
        read_only_fields = ['id', 'created_at', 'created_by']


class DispatchBatchSerializer(serializers.ModelSerializer):
    rules = DispatchRuleSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.real_name', read_only=True)

    class Meta:
        model = DispatchBatch
        fields = [
            'id', 'cycle_id', 'stage_code', 'name', 'status', 'deadline_at', 'published_at', 'closed_at',
            'stats_total', 'stats_submitted', 'stats_overdue', 'created_at', 'updated_at', 'created_by',
            'created_by_name', 'rules',
        ]
        read_only_fields = [
            'id', 'status', 'published_at', 'closed_at', 'stats_total', 'stats_submitted',
            'stats_overdue', 'created_at', 'updated_at', 'created_by',
        ]


class FormTaskSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True)
    template_code = serializers.CharField(source='template.code', read_only=True)
    batch_name = serializers.CharField(source='batch.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_overdue = serializers.SerializerMethodField()
    latest_submission = serializers.SerializerMethodField()
    template_has_source_file = serializers.SerializerMethodField()

    class Meta:
        model = FormTask
        fields = [
            'id', 'batch', 'batch_name', 'template', 'template_code', 'template_name', 'template_version',
            'assignee_type', 'assignee_id', 'assignee_name_snapshot', 'assignee_role_snapshot',
            'status', 'status_display', 'deadline_at', 'submitted_at', 'is_overdue', 'context_json',
            'reassign_to', 'reassign_reason', 'created_at', 'updated_at', 'latest_submission',
            'template_has_source_file',
        ]
        read_only_fields = fields

    def get_is_overdue(self, obj):
        return obj.is_overdue()

    def get_latest_submission(self, obj):
        submission = obj.submissions.order_by('-version').first()
        if not submission:
            return None
        return {'id': str(submission.id), 'version': submission.version, 'is_final': submission.is_final}

    def get_template_has_source_file(self, obj):
        return bool(obj.template.source_file)


class FormSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormSubmission
        fields = [
            'id', 'task', 'version', 'is_final', 'payload_json', 'score_json', 'attachments_json',
            'submitted_by', 'submitted_at', 'return_reason', 'returned_by', 'returned_at', 'created_at',
        ]
        read_only_fields = ['id', 'version', 'submitted_by', 'submitted_at', 'returned_by', 'returned_at', 'created_at']


class DraftSaveSerializer(serializers.Serializer):
    payload_json = serializers.JSONField(required=False, default=dict)
    attachments_json = serializers.JSONField(required=False, default=list)


class TaskSubmitSerializer(DraftSaveSerializer):
    score_json = serializers.JSONField(required=False, allow_null=True)


class ReturnTaskSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000)
