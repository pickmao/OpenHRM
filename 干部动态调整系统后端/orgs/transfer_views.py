from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import ScopeType
from accounts.permissions import HasPermissionCode
from audit.models import AuditAction, AuditLog

from .models import Membership, OrgUnit


class MembershipTransferView(APIView):
    """将页面中已选中的人员从一个部门调入另一个部门。"""

    permission_classes = [IsAuthenticated, HasPermissionCode]
    permission_code = 'orgs:membership:transfer'

    def _allowed_unit_ids(self, user):
        if user.is_superuser:
            return None
        scope = getattr(user, 'data_scope', None)
        if not scope:
            return set()
        if scope.scope_type == ScopeType.ALL:
            return None
        if scope.scope_type == ScopeType.ORG_UNIT:
            return set(scope.org_units.values_list('id', flat=True))
        return set()

    def post(self, request):
        user_ids = request.data.get('members', [])
        source_id = request.data.get('from_dept')
        target_id = request.data.get('to_dept')
        reason = (request.data.get('reason') or '').strip()
        effective_date = parse_date(request.data.get('effective_date', '')) or timezone.localdate()
        if not user_ids or not isinstance(user_ids, list):
            return Response({'error': '请选择需要调配的人员'}, status=status.HTTP_400_BAD_REQUEST)
        if not source_id or not target_id:
            return Response({'error': '请选择调出部门和调入部门'}, status=status.HTTP_400_BAD_REQUEST)
        if not reason:
            return Response({'error': '请填写调配原因'}, status=status.HTTP_400_BAD_REQUEST)
        source = get_object_or_404(OrgUnit, id=source_id, is_active=True)
        target = get_object_or_404(OrgUnit, id=target_id, is_active=True)
        if source == target:
            return Response({'error': '调出部门和调入部门不能相同'}, status=status.HTTP_400_BAD_REQUEST)
        allowed_ids = self._allowed_unit_ids(request.user)
        if allowed_ids is not None and (source.id not in allowed_ids or target.id not in allowed_ids):
            raise PermissionDenied('没有调配这两个部门人员的权限')

        result = []
        for user_id in user_ids:
            try:
                with transaction.atomic():
                    membership = Membership.objects.select_related('user').filter(
                        user_id=user_id, unit=source, effective_to__isnull=True
                    ).first()
                    if not membership:
                        raise ValueError('该人员不在调出部门的有效成员中')
                    if Membership.objects.filter(user_id=user_id, unit=target, effective_to__isnull=True).exists():
                        raise ValueError('该人员已在调入部门')
                    Membership.objects.filter(user_id=user_id, is_primary=True, effective_to__isnull=True).update(
                        effective_to=effective_date
                    )
                    new_membership = Membership.objects.create(
                        user_id=user_id,
                        unit=target,
                        is_primary=True,
                        position=request.data.get('new_position') or membership.position,
                        is_manager=bool(request.data.get('is_manager', False)),
                        effective_from=effective_date,
                        created_by=request.user,
                    )
                    AuditLog.objects.create(
                        actor=request.user,
                        action=AuditAction.UPDATE_ORG,
                        target_type='Membership',
                        target_id=new_membership.id,
                        context={'from_dept': str(source.id), 'to_dept': str(target.id), 'reason': reason},
                    )
                    result.append({'user_id': str(user_id), 'success': True})
            except Exception as exc:
                result.append({'user_id': str(user_id), 'success': False, 'error': str(exc)})
        success = sum(item['success'] for item in result)
        return Response({'success': success, 'failed': len(result) - success, 'results': result})
