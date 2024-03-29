import os
import sys
import time

sys.path.insert(0, os.getcwd())

from nightingale import LOG_DIR
from nightingale.utils.utils import parse_args
from nightingale.core.entrypoint import Executor

# 命令行参数
cmd = parse_args(sys.argv[1:])

if not cmd.get("f"):
    raise RuntimeError("locust 脚本文件缺失")

if cmd.__contains__("h"):
    Executor().run()

file: str = cmd.get("f")

# 日志文件
log_file = os.path.join(LOG_DIR, f"nightingale_{os.path.splitext(file)[0]}.log")

# 后台运行测试
r = os.popen(f"nohup python3 {os.getcwd()}/nightingale/core/entrypoint.py {' '.join(sys.argv[1:])}"
             f" --logfile {log_file} >/dev/null 2>&1 &")
sys.stdout.write(r.read())

# 打印日志内容
time.sleep(3)
f = os.popen(f"tail -f -n 100 {log_file}")
try:
    while True:
        # 增量读取日志文件内容，0 表示读取时的偏移量；2 表示从哪里读取，0代表从头开始，1代表当前位置，2代表文件最末尾位置。
        line = f.readline()

        if line.strip():
            sys.stdout.write(line)
        else:
            time.sleep(2)

        if "finished" in line:
            break

except KeyboardInterrupt:
    os.system("kill -9 $(ps -ef | grep 'nightingale' | awk '{print $2}')")
