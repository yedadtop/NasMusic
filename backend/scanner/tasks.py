# scanner/tasks.py
import threading
from .utils import scan_local_directory

def run_scan_async(directory_path, task_id):
    """
    启动一个后台守护线程来执行扫描任务，不阻塞主线程
    """
    thread = threading.Thread(target=scan_local_directory, args=(directory_path, task_id))
    thread.daemon = True  # 设置为守护线程
    thread.start()