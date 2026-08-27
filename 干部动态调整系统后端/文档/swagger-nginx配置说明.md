# Swagger 通过 Nginx 代理配置说明

## 问题分析

Swagger UI 需要加载静态资源（CSS、JS），通过 nginx 代理时可能会遇到：
1. 静态资源 404
2. CORS 跨域问题
3. 路径不匹配

## 解决方案

### 方案一：更新 Nginx 配置（推荐）

在你的 nginx.conf 中添加以下配置：

```nginx
server {
    listen 80;
    server_name _;

    client_max_body_size 50m;

    # ===== 前端（Vue Vite dev server）=====
    location / {
        proxy_pass http://host.docker.internal:5173;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600;
        proxy_send_timeout 3600;
    }

    # ===== 后端（Django API）=====
    location /api/ {
        proxy_pass http://host.docker.internal:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_send_timeout 300;
    }

    # ===== Django Admin =====
    location /admin/ {
        proxy_pass http://host.docker.internal:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # ===== Swagger UI (静态资源支持) =====
    location /swagger/ {
        proxy_pass http://host.docker.internal:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /redoc/ {
        proxy_pass http://host.docker.internal:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # ===== 静态文件 =====
    location /static/ {
        proxy_pass http://host.docker.internal:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /media/ {
        proxy_pass http://host.docker.internal:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 方案二：直接访问 Django（调试用）

如果只是为了调试 Swagger，可以暂时绕过 nginx，直接访问：

```
http://localhost:8000/swagger/
```

或者在 Windows 浏览器访问：

```
http://localhost:8000/swagger/
```

## 已完成的代码修改

### 1. settings.py - 静态文件配置
```python
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = []
```

### 2. urls.py - 开发模式静态文件服务
```python
from django.conf import settings
from django.conf.urls.static import static

# ... urlpatterns ...

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
```

## 测试步骤

1. **重启 Django 服务**
   ```bash
   cd "/mnt/d/code/干部管理系统开发/干部动态调整系统后端"
   python manage.py runserver
   ```

2. **重启 Nginx 容器**
   ```bash
   docker restart <nginx容器名>
   ```

3. **访问测试**
   - 直接访问: `http://localhost:8000/swagger/`
   - 通过 Nginx: `http://3844m0m948.vicp.fun/swagger/`

## 常见错误及解决

### 错误 1: 静态文件 404
```
GET http://3844m0m948.vicp.fun/static/swagger-ui-bundle.js net::ERR_ABORTED 404
```

**解决**:
- 检查 nginx 配置中是否有 `/static/` 的 location
- 确认 Django 的 DEBUG=True
- 运行 `python manage.py collectstatic`

### 错误 2: CORS 错误
```
Access to script at 'xxx' from origin 'xxx' has been blocked by CORS policy
```

**解决**: Django settings.py 已配置 `CORS_ALLOW_ALL_ORIGINS = True`

### 错误 3: API 加载失败
```
Failed to load API definition
```

**解决**:
- 检查 `/swagger.json` 是否可访问
- 确认所有 API ViewSet 已正确注册
