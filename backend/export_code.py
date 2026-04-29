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


def get_available_apps():
    available = []
    for app in APPS:
        app_dir = os.path.join(BASE_DIR, app)
        if os.path.isdir(app_dir):
            available.append(app)
    return available


def select_apps():
    available = get_available_apps()
    print("\n📋 可用的 APP 列表:")
    print("-" * 40)
    for i, app in enumerate(available, 1):
        print(f"  {i}. {app}")
    print("-" * 40)
    print("\n选择要导出的 APP:")
    print("  - 输入 'all': 导出所有 APP")
    print("  - 输入数字编号 (如 1,3): 导出指定的 APP")
    print("  - 输入 app 名称 (如 library,scanner): 导出指定的 APP")

    while True:
        choice = input("\n请输入选择: ").strip()
        if not choice:
            print("❌ 输入不能为空，请重新输入")
            continue

        if choice.lower() == 'all':
            return available

        selected = []
        parts = [p.strip() for p in choice.split(',')]

        for part in parts:
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(available):
                    selected.append(available[idx])
                else:
                    print(f"❌ 无效的编号: {part}，请重新输入")
                    break
            elif part in available:
                selected.append(part)
            else:
                print(f"❌ 无效的 APP 名称: {part}，请重新输入")
                break
        else:
            if selected:
                return selected

    return available


def export_code(selected_apps=None):
    if selected_apps is None:
        selected_apps = get_available_apps()

    content = []
    print("=" * 60)
    print("Django 代码导出工具")
    print("=" * 60)

    for app in selected_apps:
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
    print(f"📊 共处理 {len(selected_apps)} 个 APP: {', '.join(selected_apps)}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    selected = select_apps()
    export_code(selected)
