# scanner/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import ScanTask, SystemConfig
from .tasks import run_scan_async


def get_music_path():
    config = SystemConfig.objects.filter(key='music_path').first()
    if config and config.value:
        return config.value
    return None


class ScanLibraryView(APIView):
    """
    触发本地音乐目录扫描 (异步)
    """

    def post(self, request):
        active_task = ScanTask.objects.filter(status__in=['pending', 'running']).first()
        if active_task:
            return Response({
                "message": "当前已有扫描任务正在进行中，请勿重复点击！",
                "task_id": active_task.id
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        music_path = get_music_path()
        if not music_path:
            return Response({
                "message": "请先在系统配置中设置音乐文件路径"
            }, status=status.HTTP_400_BAD_REQUEST)

        task = ScanTask.objects.create(target_path=music_path)
        run_scan_async(music_path, task.id)

        return Response({
            "message": "扫描任务已在后台启动",
            "task_id": task.id
        }, status=status.HTTP_202_ACCEPTED)


class ScanStatusView(APIView):
    """
    查询扫描任务状态进度
    """

    def get(self, request):
        task_id = request.query_params.get('task_id')
        if task_id:
            task = ScanTask.objects.filter(id=task_id).first()
        else:
            task = ScanTask.objects.order_by('-created_at').first()

        if not task:
            return Response({"message": "暂无扫描任务记录"}, status=status.HTTP_404_NOT_FOUND)

        progress = 0
        if task.total_files > 0:
            progress = int((task.processed_files / task.total_files) * 100)

        return Response({
            "task_id": task.id,
            "status": task.status,
            "progress": progress,
            "total_files": task.total_files,
            "processed_files": task.processed_files,
            "current_file": task.current_file,
            "added_count": task.added_count,
            "updated_count": task.updated_count,
            "deleted_count": getattr(task, 'deleted_count', 0),
            "error_message": task.error_message
        }, status=status.HTTP_200_OK)


class SystemConfigView(APIView):
    """
    获取或更新系统配置
    """

    def get(self, request):
        configs = SystemConfig.objects.all()
        result = {}
        for config in configs:
            result[config.key] = {
                "value": config.value,
                "description": config.description,
                "updated_at": config.updated_at
            }
        return Response(result, status=status.HTTP_200_OK)

    def put(self, request):
        key = request.data.get('key')
        value = request.data.get('value')
        description = request.data.get('description', '')

        if not key or value is None:
            return Response({"message": "key 和 value 不能为空"}, status=status.HTTP_400_BAD_REQUEST)

        config, created = SystemConfig.objects.update_or_create(
            key=key,
            defaults={'value': value, 'description': description}
        )

        return Response({
            "message": "配置更新成功" if not created else "配置创建成功",
            "key": config.key,
            "value": config.value,
            "description": config.description
        }, status=status.HTTP_200_OK)