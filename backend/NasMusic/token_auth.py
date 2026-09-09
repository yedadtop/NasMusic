# NasMusic/token_auth.py
# 静态令牌鉴权：写操作（POST/PUT/PATCH/DELETE）需要携带有效令牌，只读接口放行
# 注意：本模块会被 settings.DEFAULT_PERMISSION_CLASSES 引用，禁止在顶层导入
# rest_framework.views（会触发循环导入）；视图请放到 auth_views.py
import hmac
from django.conf import settings
from rest_framework.permissions import BasePermission, SAFE_METHODS


def extract_token(request):
    """从 Authorization 请求头（Bearer/Token）或 ?token= 查询参数中提取令牌"""
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if auth.startswith('Bearer ') or auth.startswith('Token '):
        return auth.split(' ', 1)[1].strip()
    return request.GET.get('token', '')


def token_matches(request):
    """校验请求携带的令牌是否与配置一致（恒定时间比较，防时序攻击）"""
    expected = getattr(settings, 'NASMUSIC_API_TOKEN', '')
    if not expected:
        # 后端未配置令牌时不启用校验
        return True
    provided = extract_token(request)
    if not provided:
        return False
    return hmac.compare_digest(provided.encode('utf-8'), expected.encode('utf-8'))


class TokenRequiredForUnsafe(BasePermission):
    """写操作鉴权：GET/HEAD/OPTIONS 放行，其余方法需携带有效令牌"""
    message = '访问令牌缺失或无效，请前往「设置」填写访问令牌'

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return token_matches(request)
