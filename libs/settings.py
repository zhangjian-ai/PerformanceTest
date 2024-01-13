import os
from pathlib import Path

# 项目路径
from libs.framework.utils import path_builder

BASE_DIR = Path(__file__).resolve().parent.parent.__str__()

# 脚本路径
LOCUST_DIR = path_builder(os.path.join(BASE_DIR, "scripts"))

# 日志路径
LOG_DIR = path_builder(os.path.join(BASE_DIR, "logs"))

# 配置文件路径
CONFIG_DIR = path_builder(os.path.join(BASE_DIR, "config"))
