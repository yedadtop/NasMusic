"""
Django 代码导出脚本
将所有 app 的 model, utils, views 文件内容导出到单个 txt 文件
"""
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = SCRIPT_DIR
OUTPUT_FILE = os.path.join(BASE_DIR, "exported_code.txt")

APPS = ['library', 'scanner', 'stream', 'scraper']
FILES = ['models.py', 'views.py', 'serializers.py', 'admin.py', 'utils.py']


def export_code():
    content = []
    print("=" * 60)
    print("Django 代码导出工具")
    print("=" * 60)

    for app in APPS:
        app_dir = os.path.join(BASE_DIR, app)
        if not os.path.isdir(app_dir):
            print(f"⏭️  跳过 {app}/ (目录不存在)")
            continue

        print(f"\n📂 发现 APP: {app}")
        print("-" * 40)

        for filename in FILES:
            filepath = os.path.join(app_dir, filename)
            if not os.path.isfile(filepath):
                continue

            print(f"  📄 导出 {app}/{filename}")

            with open(filepath, 'r', encoding='utf-8') as f:
                content.append("")
                content.append("-" * 60)
                content.append(f"{app} {filename}:")
                content.append("-" * 60)
                content.append(f.read())
                content.append("")

        print(f"  ✅ {app} 完成")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(content))

    print(f"\n{'=' * 60}")
    print(f"✅ 代码已导出到: {OUTPUT_FILE}")
    print(f"📊 共处理 {len([a for a in APPS if os.path.isdir(os.path.join(BASE_DIR, a))])} 个 APP")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    export_code()
