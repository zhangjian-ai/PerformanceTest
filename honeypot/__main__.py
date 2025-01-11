import os
import sys

from gevent import monkey
monkey.patch_all()

sys.path.insert(0, os.getcwd())

from honeypot.libs.utils import parse_args
from honeypot.core.entrypoint import Executor

# 命令行参数
cmd = parse_args(sys.argv[1:])

if not cmd.get("f"):
    raise RuntimeError("locust 脚本文件缺失")

Executor().run()
