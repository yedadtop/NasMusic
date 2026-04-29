# scanner/models.py
from django.db import models


class ScanTask(models.Model):
    STATUS_CHOICES = (
        ('pending', '等待中'),
        ('running', '正在扫描'),
        ('completed', '扫描完成'),
        ('error', '扫描出错'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    target_path = models.CharField(max_length=1024, verbose_name="目标路径")

    total_files = models.IntegerField(default=0, verbose_name="总文件数")
    processed_files = models.IntegerField(default=0, verbose_name="已处理数")

    added_count = models.IntegerField(default=0, verbose_name="新增数量")
    updated_count = models.IntegerField(default=0, verbose_name="更新数量")

    current_file = models.CharField(max_length=1024, blank=True, null=True, verbose_name="当前正在处理的文件")
    error_message = models.TextField(blank=True, null=True, verbose_name="错误信息")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"扫描任务 #{self.id} - {self.status}"