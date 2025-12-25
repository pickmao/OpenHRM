from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView
from django.contrib.auth import login
from django.utils import timezone
from .models import DataScope
from .serializers import (
    LoginSerializer,
    UserProfileSerializer,
    RefreshTokenSerializer,
    LogoutSerializer,
    ChangePasswordSerializer
)
from audit.models import AuditLog, AuditAction


def get_client_ip(request):
    """获取客户端IP"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    """
    登录接口
    POST /api/auth/login/
    """
    serializer = LoginSerializer(data=request.data, context={'request': request})

    if serializer.is_valid():
        user = serializer.validated_data['user']

        # 获取或创建数据范围
        data_scope, created = DataScope.objects.get_or_create(
            user=user,
            defaults={
                'scope_type': 'SELF' if not user.is_superuser else 'ALL'
            }
        )

        # 生成JWT tokens
        refresh = RefreshToken.for_user(user)

        # 更新登录信息
        user.last_login = timezone.now()
        user.last_login_ip = get_client_ip(request)
        user.save(update_fields=['last_login', 'last_login_ip'])

        # 记录登录成功日志
        AuditLog.objects.create(
            actor=user,
            action=AuditAction.LOGIN,
            target_type='User',
            target_id=user.id,
            ip_address=user.last_login_ip,
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            context={
                'username': user.username,
                'success': True
            }
        )

        # 获取用户信息
        profile_serializer = UserProfileSerializer(user, context={'request': request})

        response_data = {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'expires_in': 900,  # 15分钟
            'user': profile_serializer.data,
            'permissions': profile_serializer.data.get('permissions', [])
        }

        return Response(response_data, status=status.HTTP_200_OK)

    # 记录登录失败日志
    AuditLog.objects.create(
        actor=None,
        action=AuditAction.OTHER,
        target_type='User',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        context={
            'username': request.data.get('username', ''),
            'success': False,
            'errors': serializer.errors
        }
    )

    return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)


class CustomTokenRefreshView(TokenRefreshView):
    """自定义刷新Token视图"""
    serializer_class = RefreshTokenSerializer


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    """
    登出接口
    POST /api/auth/logout/
    """
    serializer = LogoutSerializer(data=request.data)

    if serializer.is_valid():
        try:
            refresh_token = serializer.validated_data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()

            # 记录登出日志
            AuditLog.objects.create(
                actor=request.user,
                action=AuditAction.LOGOUT,
                target_type='User',
                target_id=request.user.id,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )

            return Response({'message': '登出成功'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': '登出失败'}, status=status.HTTP_400_BAD_REQUEST)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(RetrieveAPIView):
    """
    获取当前用户信息
    GET /api/auth/me/
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password_view(request):
    """
    修改密码
    POST /api/auth/change-password/
    """
    serializer = ChangePasswordSerializer(
        data=request.data,
        context={'request': request}
    )

    if serializer.is_valid():
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        # 记录修改密码日志
        AuditLog.objects.create(
            actor=user,
            action=AuditAction.OTHER,
            target_type='User',
            target_id=user.id,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            context={
                'action': 'change_password',
                'success': True
            }
        )

        return Response({'message': '密码修改成功'}, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
