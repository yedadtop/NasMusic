# scraper/views.py
import threading
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from library.models import Track
from .models import ScraperAPI
from .serializers import ScraperAPISerializer
from .utils import fetch_and_embed_cover


class ScraperAPIViewSet(viewsets.ModelViewSet):
    """
    刮削接口的增删改查视图
    """
    queryset = ScraperAPI.objects.all()
    serializer_class = ScraperAPISerializer


class TrackScrapeView(APIView):
    """
    手动触发单首歌曲的封面高清刮削
    """

    def post(self, request, track_id):
        track = get_object_or_404(Track, id=track_id)

        success, message = fetch_and_embed_cover(track)

        if success:
            return Response({"message": message}, status=status.HTTP_200_OK)
        else:
            return Response({"error": message}, status=status.HTTP_404_NOT_FOUND)


class BatchScrapeCoverView(APIView):
    """
    批量刮削并嵌入所有缺少封面的歌曲封面
    """

    def post(self, request):
        task_id = request.data.get('task_id')
        if not task_id:
            return Response({"message": "缺少 task_id 参数"}, status=status.HTTP_400_BAD_REQUEST)

        def run_batch_scrape():
            from scanner.models import ScanTask
            import os

            task = ScanTask.objects.filter(id=task_id).first()
            if not task:
                print(f"[批量刮削] 任务 {task_id} 不存在")
                return

            tracks = Track.objects.all()
            tracks_to_scrape = []
            tracks_file_not_exist = []

            print(f"[批量刮削] 测试模式：跳过封面检查，直接刮削所有歌曲，共 {tracks.count()} 首")

            for track in tracks:
                if not os.path.exists(track.file_path):
                    tracks_file_not_exist.append(track.file_path)
                    print(f"[批量刮削] 文件不存在，跳过: {track.file_path}")
                    continue
                tracks_to_scrape.append(track)
                print(f"[批量刮削] 待刮削: {track.title} - {track.file_path}")

            print(f"[批量刮削] 检查完成: 待刮削 {len(tracks_to_scrape)} 首, 文件不存在 {len(tracks_file_not_exist)} 首")

            total = len(tracks_to_scrape)
            task.total_files = total
            task.processed_files = 0
            task.status = 'running'
            task.save()

            success_count = 0
            failed_count = 0

            for track in tracks_to_scrape:
                task.current_file = track.file_path
                task.save()

                print(f"[批量刮削] 开始刮削: {track.title} - {track.file_path}")
                success, message = fetch_and_embed_cover(track)
                if success:
                    success_count += 1
                    print(f"[批量刮削] ✅ 成功: {track.title} - {message}")
                else:
                    failed_count += 1
                    print(f"[批量刮削] ❌ 失败: {track.title} - {message}")

                task.processed_files = success_count + failed_count
                task.save()

            task.status = 'completed'
            task.current_file = ''
            task.save()

            print(f"[批量刮削] 任务完成: 成功 {success_count} 首, 失败 {failed_count} 首")

        threading.Thread(target=run_batch_scrape, daemon=True).start()

        return Response({
            "message": "批量刮削任务已在后台启动",
            "task_id": task_id
        }, status=status.HTTP_202_ACCEPTED)