# scraper/models.py
from django.db import models

class ScraperAPI(models.Model):
    name = models.CharField(max_length=100, verbose_name="接口名称")
    url = models.URLField(max_length=500, verbose_name="接口地址", help_text="例如: https://itunes.apple.com/search")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    priority = models.IntegerField(default=0, verbose_name="优先级", help_text="数字越小优先级越高")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['priority', '-id']
        verbose_name = "刮削接口配置"
        verbose_name_plural = "刮削接口配置"

    def __str__(self):
        return f"{self.name} ({'启用' if self.is_active else '停用'})"