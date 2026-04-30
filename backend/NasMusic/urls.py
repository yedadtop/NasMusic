from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from library.views import TrackViewSet, ArtistViewSet, AlbumViewSet

# 自动生成 RESTful 路由
router = DefaultRouter()
router.register(r'tracks', TrackViewSet)
router.register(r'artists', ArtistViewSet)
router.register(r'albums', AlbumViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    # 把我们的 API 挂载到 /api/ 路径下
    path('api/', include(router.urls)),
    # 挂载流媒体服务的路由
    path('stream/', include('stream.urls')),
    # --- 新增：挂载扫描器接口 ---
    path('api/scanner/', include('scanner.urls')),
    # --- 新增：挂载刮削器接口 ---
    path('api/scraper/', include('scraper.urls')),
]

# 新增这段逻辑：只有在开发模式下，才让 Django 代劳提供媒体文件
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)