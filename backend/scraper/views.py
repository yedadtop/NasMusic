# scraper/views.py
import threading
import json
from django.db import models
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from library.models import Track
from .models import ScraperAPI
from .serializers import ScraperAPISerializer
from .utils import fetch_and_embed_cover, fetch_and_embed_lyrics

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

        has_cover = bool(track.cover_thumbnail and str(track.cover_thumbnail).strip())

        success, message = fetch_and_embed_cover(track)

        track.refresh_from_db()
        has_cover_after = bool(track.cover_thumbnail and str(track.cover_thumbnail).strip())

        response_data = {
            "track_id": track.id,
            "track_title": track.title,
            "success": success,
            "message": message,
            "had_cover_before": has_cover,
            "has_cover_after": has_cover_after
        }

        if success:
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)

    def get(self, request, track_id):
        track = get_object_or_404(Track, id=track_id)
        has_cover = bool(track.cover_thumbnail and str(track.cover_thumbnail).strip())

        return Response({
            "track_id": track.id,
            "track_title": track.title,
            "has_cover": has_cover,
            "cover_url": track.cover_thumbnail.url if has_cover else None
        }, status=status.HTTP_200_OK)


class BatchScrapeCoverView(APIView):
    """
    批量刮削封面，支持全量和增量模式
    mode: 'full'(全量) 或 'incremental'(增量，只刮削缺少封面的歌曲)
    """

    def post(self, request):
        task_id = request.data.get('task_id')
        mode = request.data.get('mode', 'incremental')

        if not task_id:
            return Response({"message": "缺少 task_id 参数"}, status=status.HTTP_400_BAD_REQUEST)

        if mode not in ['full', 'incremental']:
            return Response({"message": "mode 参数必须是 'full' 或 'incremental'"}, status=status.HTTP_400_BAD_REQUEST)

        def run_batch_scrape():
            from scanner.models import ScanTask
            import os

            task = ScanTask.objects.filter(id=task_id).first()
            if not task:
                print(f"[批量刮削] 任务 {task_id} 不存在")
                return

            print(f"[批量刮削] =========================================")
            print(f"[批量刮削] 开始批量刮削任务，模式: {'全量' if mode == 'full' else '增量'}")
            print(f"[批量刮削] =========================================")

            if mode == 'incremental':
                tracks = Track.objects.filter(
                    models.Q(cover_thumbnail__isnull=True) | models.Q(cover_thumbnail__exact='')
                )
                print(f"[批量刮削] 增量模式：只刮削缺少封面的歌曲")
            else:
                tracks = Track.objects.all()
                print(f"[批量刮削] 全量模式：刮削所有歌曲")

            tracks_to_scrape = []
            tracks_file_not_exist = []
            tracks_already_has_cover = []

            for track in tracks:
                has_cover = bool(track.cover_thumbnail and str(track.cover_thumbnail).strip())
                if has_cover:
                    tracks_already_has_cover.append(track)
                    print(f"[批量刮削] 已有封面，跳过: {track.title} - {track.file_path}")
                    continue

                if not os.path.exists(track.file_path):
                    tracks_file_not_exist.append(track.file_path)
                    print(f"[批量刮削] 文件不存在，跳过: {track.file_path}")
                    continue
                tracks_to_scrape.append(track)
                print(f"[批量刮削] 待刮削: {track.title} - {track.file_path}")

            print(f"[批量刮削] 检查完成: 待刮削 {len(tracks_to_scrape)} 首, 已有封面跳过 {len(tracks_already_has_cover)} 首, 文件不存在 {len(tracks_file_not_exist)} 首")

            total = len(tracks_to_scrape)
            task.total_files = len(tracks_to_scrape)
            task.processed_files = 0
            task.status = 'running'
            task.save()

            success_list = []
            failed_list = []

            for track in tracks_to_scrape:
                task.current_file = track.file_path
                task.save()

                print(f"[批量刮削] 开始刮削: {track.title} - {track.file_path}")
                success, message = fetch_and_embed_cover(track)
                if success:
                    success_list.append({
                        "track_id": track.id,
                        "title": track.title,
                        "message": message
                    })
                    print(f"[批量刮削] ✅ 成功: {track.title} - {message}")
                else:
                    failed_list.append({
                        "track_id": track.id,
                        "title": track.title,
                        "message": message
                    })
                    print(f"[批量刮削] ❌ 失败: {track.title} - {message}")

                task.processed_files = len(success_list) + len(failed_list)
                task.save()

            task.status = 'completed'
            task.current_file = ''
            task.result_summary = json.dumps({
                "mode": mode,
                "total": len(tracks_to_scrape),
                "success_count": len(success_list),
                "failed_count": len(failed_list),
                "skipped_cover": len(tracks_already_has_cover),
                "skipped_file_not_exist": len(tracks_file_not_exist),
                "success_list": success_list,
                "failed_list": failed_list
            }, ensure_ascii=False)
            task.save()

            print(f"[批量刮削] 任务完成: 成功 {len(success_list)} 首, 失败 {len(failed_list)} 首")
            print(f"[批量刮削] 跳过: 已有封面 {len(tracks_already_has_cover)} 首, 文件不存在 {len(tracks_file_not_exist)} 首")

        threading.Thread(target=run_batch_scrape, daemon=True).start()

        return Response({
            "message": f"批量刮削任务已在后台启动 (模式: {'全量' if mode == 'full' else '增量'})",
            "task_id": task_id,
            "mode": mode
        }, status=status.HTTP_202_ACCEPTED)


class TrackScrapeLyricsView(APIView):
    """
    手动触发单首歌曲的歌词刮削
    """

    def post(self, request, track_id):
        track = get_object_or_404(Track, id=track_id)

        has_lyrics_before = bool(track.lyrics and track.lyrics.strip())

        success, message = fetch_and_embed_lyrics(track)

        track.refresh_from_db()
        has_lyrics_after = bool(track.lyrics and track.lyrics.strip())

        response_data = {
            "track_id": track.id,
            "track_title": track.title,
            "success": success,
            "message": message,
            "had_lyrics_before": has_lyrics_before,
            "has_lyrics_after": has_lyrics_after,
            "lyrics_length": len(track.lyrics) if track.lyrics else 0
        }

        if success:
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)

    def get(self, request, track_id):
        track = get_object_or_404(Track, id=track_id)
        has_lyrics = bool(track.lyrics and track.lyrics.strip())

        return Response({
            "track_id": track.id,
            "track_title": track.title,
            "has_lyrics": has_lyrics,
            "lyrics_length": len(track.lyrics) if track.lyrics else 0
        }, status=status.HTTP_200_OK)


class BatchScrapeLyricsView(APIView):
    """
    批量刮削歌词，支持全量和增量模式
    mode: 'full'(全量) 或 'incremental'(增量，只刮削缺少歌词的歌曲)
    """

    def post(self, request):
        task_id = request.data.get('task_id')
        mode = request.data.get('mode', 'incremental')

        if not task_id:
            return Response({"message": "缺少 task_id 参数"}, status=status.HTTP_400_BAD_REQUEST)

        if mode not in ['full', 'incremental']:
            return Response({"message": "mode 参数必须是 'full' 或 'incremental'"}, status=status.HTTP_400_BAD_REQUEST)

        def run_batch_scrape():
            from scanner.models import ScanTask
            import os

            task = ScanTask.objects.filter(id=task_id).first()
            if not task: return

            print(f"[批量歌词刮削] =========================================")
            print(f"[批量歌词刮削] 开始批量歌词刮削任务，模式: {'全量' if mode == 'full' else '增量'}")
            print(f"[批量歌词刮削] =========================================")

            if mode == 'incremental':
                tracks = Track.objects.filter(
                    models.Q(lyrics__isnull=True) | models.Q(lyrics__exact='')
                )
                print(f"[批量歌词刮削] 增量模式：只刮削缺少歌词的歌曲")
            else:
                tracks = Track.objects.all()
                print(f"[批量歌词刮削] 全量模式：刮削所有歌曲")

            tracks_to_scrape = []
            tracks_file_not_exist = []
            tracks_already_has_lyrics = []

            for track in tracks:
                has_lyrics = bool(track.lyrics and track.lyrics.strip())
                if has_lyrics:
                    tracks_already_has_lyrics.append(track)
                    print(f"[批量歌词刮削] 已有歌词，跳过: {track.title} (长度: {len(track.lyrics)} 字符)")
                    continue

                if not os.path.exists(track.file_path):
                    tracks_file_not_exist.append(track.file_path)
                    continue
                tracks_to_scrape.append(track)

            print(f"[批量歌词刮削] 检查完成: 待刮削 {len(tracks_to_scrape)} 首, 已有歌词跳过 {len(tracks_already_has_lyrics)} 首, 文件不存在 {len(tracks_file_not_exist)} 首")

            task.total_files = len(tracks_to_scrape)
            task.processed_files = 0
            task.status = 'running'
            task.save()

            success_list = []
            failed_list = []

            for track in tracks_to_scrape:
                task.current_file = track.file_path
                task.save()

                success, message = fetch_and_embed_lyrics(track)
                if success:
                    success_list.append({
                        "track_id": track.id,
                        "title": track.title,
                        "message": message
                    })
                    print(f"[批量歌词刮削] ✅ 成功: {track.title} - {message}")
                else:
                    failed_list.append({
                        "track_id": track.id,
                        "title": track.title,
                        "message": message
                    })
                    print(f"[批量歌词刮削] ❌ 失败: {track.title} - {message}")

                task.processed_files = len(success_list) + len(failed_list)
                task.save()

            task.status = 'completed'
            task.current_file = ''
            task.result_summary = json.dumps({
                "mode": mode,
                "total": len(tracks_to_scrape),
                "success_count": len(success_list),
                "failed_count": len(failed_list),
                "skipped_lyrics": len(tracks_already_has_lyrics),
                "skipped_file_not_exist": len(tracks_file_not_exist),
                "success_list": success_list,
                "failed_list": failed_list
            }, ensure_ascii=False)
            task.save()

            print(f"[批量歌词刮削] 完成: 成功 {len(success_list)} 首, 失败 {len(failed_list)} 首")
            print(f"[批量歌词刮削] 跳过: 已有歌词 {len(tracks_already_has_lyrics)} 首, 文件不存在 {len(tracks_file_not_exist)} 首")

        threading.Thread(target=run_batch_scrape, daemon=True).start()

        return Response({
            "message": f"批量歌词刮削任务已在后台启动 (模式: {'全量' if mode == 'full' else '增量'})",
            "task_id": task_id,
            "mode": mode
        }, status=status.HTTP_202_ACCEPTED)