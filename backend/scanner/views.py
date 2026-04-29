# scanner/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import ScanTask
from .tasks import run_scan_async


class ScanLibraryView(APIView):
    """
    触发本地音乐目录扫描 (异步)
    """

    def post(self, request):
        # ==========================================
        # 🚨 核心拦截逻辑：防止同时启动多个扫描线程
        # ==========================================
        active_task = ScanTask.objects.filter(status__in=['pending', 'running']).first()
        if active_task:
            return Response({
                "message": "当前已有扫描任务正在进行中，请勿重复点击！",
                "task_id": active_task.id
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            # 返回 429 Too Many Requests，告诉前端不要再发了

        # 如果没有正在运行的任务，再继续正常启动
        directory_path = request.data.get('path', r"C:\1D\Mass\my_music")

        # 1. 在数据库中创建一条扫描任务记录
        task = ScanTask.objects.create(target_path=directory_path)

        # 2. 将任务丢给后台线程去跑
        run_scan_async(directory_path, task.id)

        # 3. 立刻返回给前端
        return Response({
            "message": "扫描任务已在后台启动",
            "task_id": task.id
        }, status=status.HTTP_202_ACCEPTED)


class ScanStatusView(APIView):
    """
    查询扫描任务状态进度
    """

    def get(self, request):
        # 允许前端通过 ?task_id=1 查询指定任务，如果不传，默认查询最新的一条记录
        task_id = request.query_params.get('task_id')
        if task_id:
            task = ScanTask.objects.filter(id=task_id).first()
        else:
            task = ScanTask.objects.order_by('-created_at').first()

        if not task:
            return Response({"message": "暂无扫描任务记录"}, status=status.HTTP_404_NOT_FOUND)

        # 计算百分比进度
        progress = 0
        if task.total_files > 0:
            progress = int((task.processed_files / task.total_files) * 100)

        return Response({
            "task_id": task.id,
            "status": task.status,  # 'running', 'completed', 'error'
            "progress": progress,  # 例如: 45 (代表 45%)
            "total_files": task.total_files,
            "processed_files": task.processed_files,
            "current_file": task.current_file,
            "added_count": task.added_count,
            "updated_count": task.updated_count,
            "error_message": task.error_message
        }, status=status.HTTP_200_OK)