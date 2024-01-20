import os
import sys
import time

sys.path.insert(0, os.getcwd())

from libs.settings import LOG_DIR
from libs.framework.utils import parse_args

# 命令行参数
cmd = parse_args(sys.argv[1:])

if not cmd.get("f"):
    raise RuntimeError("locust 脚本文件缺失")

file = cmd.get("f")

# 日志文件
log_file = os.path.join(LOG_DIR, f"{os.path.splitext(file)[0]}_{time.strftime('%Y-%m-%d_%H:%M')}.log")

# 后台运行测试
os.system(f"nohup python3 {os.getcwd()}/nightingale/executor.py {' '.join(sys.argv[1:])}"
          f" --logfile {log_file} >/dev/null 2>&1 &")

# 打印日志内容
time.sleep(3)
f = os.popen(f"tail -f {log_file}")
try:
    while True:
        # 增量读取日志文件内容，0 表示读取时的偏移量；2 表示从哪里读取，0代表从头开始，1代表当前位置，2代表文件最末尾位置。
        # f.seek(0, 2)
        line = f.readline()

        if line.strip():
            sys.stdout.write(line)

        if "finished" in line:
            break

except KeyboardInterrupt:
    pass

