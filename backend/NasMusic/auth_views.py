# NasMusic/auth_views.py
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response


class TokenVerifyView(APIView):
    """校验访问令牌（POST，本身受全局权限类拦截：令牌有效返回 200，无效返回 403）"""

    def post(self, request):
        configured = bool(getattr(settings, 'NASMUSIC_API_TOKEN', ''))
        return Response({
            'success': True,
            'token_configured': configured,
            'message': '令牌有效' if configured else '后端未启用令牌校验（NASMUSIC_API_TOKEN 为空）',
        })
