from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView
from django.contrib.auth import login
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import DataScope
from .serializers import (
    LoginSerializer,
    UserProfileSerializer,
    RefreshTokenSerializer,
    LogoutSerializer,
    ChangePasswordSerializer
)
from audit.models import AuditLog, AuditAction

# 登录接口的请求和响应schema
login_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['username', 'password'],
    properties={
        'username': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='用户名',
            example='admin'
        ),
        'password': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='密码',
            example='admin123456'
        ),
    }
)

login_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'access': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='访问令牌（Access Token），有效期15分钟'
        ),
        'refresh': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='刷新令牌（Refresh Token），有效期7天'
        ),
        'expires_in': openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description='访问令牌过期时间（秒）'
        ),
        'user': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            description='用户信息',
            properties={
                'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='用户ID'),
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='用户名'),
                'real_name': openapi.Schema(type=openapi.TYPE_STRING, description='真实姓名'),
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='邮箱'),
                'phone': openapi.Schema(type=openapi.TYPE_STRING, description='手机号'),
                'role': openapi.Schema(type=openapi.TYPE_STRING, description='角色'),
            }
        ),
        'permissions': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_STRING),
            description='用户权限列表'
        )
    }
)

refresh_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['refresh'],
    properties={
        'refresh': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='刷新令牌'
        ),
    }
)

logout_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['refresh'],
    properties={
        'refresh': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='刷新令牌（需要加入黑名单）'
        ),
    }
)

change_password_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['old_password', 'new_password'],
    properties={
        'old_password': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='旧密码',
            minLength=6
        ),
        'new_password': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='新密码',
            minLength=6
        ),
    }
)


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
@swagger_auto_schema(
    operation_summary='用户登录',
    operation_description='使用用户名和密码登录系统，成功后返回JWT Token和用户信息',
    request_body=login_schema,
    responses={
        200: openapi.Response(
            description='登录成功',
            schema=login_response_schema
        ),
        401: openapi.Response(
            description='登录失败，用户名或密码错误',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING, description='错误信息')
                }
            )
        ),
    },
    tags=['认证接口']
)
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

    @swagger_auto_schema(
        operation_summary='刷新访问令牌',
        operation_description='使用刷新令牌获取新的访问令牌',
        request_body=refresh_schema,
        responses={
            200: openapi.Response(
                description='刷新成功',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'access': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description='新的访问令牌'
                        ),
                        'refresh': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description='新的刷新令牌（如果启用了轮换）'
                        ),
                    }
                )
            ),
            401: openapi.Response(
                description='刷新令牌无效或已过期'
            ),
        },
        tags=['认证接口']
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@swagger_auto_schema(
    operation_summary='用户登出',
    operation_description='将刷新令牌加入黑名单，使用户退出登录',
    request_body=logout_schema,
    responses={
        200: openapi.Response(
            description='登出成功',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='登出成功')
                }
            )
        ),
        400: openapi.Response(
            description='请求参数错误或令牌无效'
        ),
        401: openapi.Response(
            description='未授权，需要先登录'
        ),
    },
    tags=['认证接口']
)
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

    @swagger_auto_schema(
        operation_summary='获取当前用户信息',
        operation_description='获取当前登录用户的详细信息，包括角色、权限等',
        responses={
            200: openapi.Response(
                description='获取成功',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='用户ID'),
                        'username': openapi.Schema(type=openapi.TYPE_STRING, description='用户名'),
                        'real_name': openapi.Schema(type=openapi.TYPE_STRING, description='真实姓名'),
                        'email': openapi.Schema(type=openapi.TYPE_STRING, description='邮箱'),
                        'phone': openapi.Schema(type=openapi.TYPE_STRING, description='手机号'),
                        'role': openapi.Schema(type=openapi.TYPE_STRING, description='角色'),
                        'is_superuser': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='是否超级管理员'),
                        'last_login': openapi.Schema(type=openapi.TYPE_STRING, description='最后登录时间'),
                        'last_login_ip': openapi.Schema(type=openapi.TYPE_STRING, description='最后登录IP'),
                        'permissions': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_STRING),
                            description='权限列表'
                        ),
                    }
                )
            ),
            401: openapi.Response(
                description='未授权，需要先登录'
            ),
        },
        tags=['认证接口']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_object(self):
        return self.request.user


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@swagger_auto_schema(
    operation_summary='修改密码',
    operation_description='修改当前登录用户的密码',
    request_body=change_password_schema,
    responses={
        200: openapi.Response(
            description='密码修改成功',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='密码修改成功')
                }
            )
        ),
        400: openapi.Response(
            description='请求参数错误（如旧密码不正确、新密码不符合要求等）'
        ),
        401: openapi.Response(
            description='未授权，需要先登录'
        ),
    },
    tags=['认证接口']
)
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
