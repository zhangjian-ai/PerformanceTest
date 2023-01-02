import os
import logging
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def valid_path(path):
    """
    检查路径
    如果是绝对路径则直接返回
    如果是相对路径则为其拼接项目路径后返回
    :param path:
    :return:
    """
    starts = ["/", "C:", "D:", "E:", "F:", "G:"]
    if any([path.startswith(start) for start in starts]):
        return path

    path = os.path.join(BASE_DIR, path)

    if not os.path.exists(path):
        logging.warning(f"目标路径不存在({path})，如非本意，请检查挂载目录。")

        # 如果路径不存在，就判断当前指向的是不是文件
        basename = os.path.basename(path)

        # 如果不是文件则直接创建目录即可
        if r"." not in basename:
            os.makedirs(path)
        # 如果是文件，那么就先创建路径，再创建文件
        else:
            dirname = os.path.dirname(path)

            if not os.path.exists(dirname):
                os.makedirs(dirname)

            # 创建文件时，如果是 yaml 和 json 文件，默认写入一个空字典
            with open(path, "w") as f:
                if basename.endswith(".yaml") or basename.endswith(".yml") or basename.endswith(".json"):
                    f.write("{}")

    return path


# k8s配置文件目录
K8S_DIR = valid_path("config/k8s")

# 场景文件目录
SCENE_DIR = valid_path("config/scenes")

# 数据目录
DATA_DIR = valid_path("data")

# locust文件目录
LOCUST_DIR = valid_path("test/scripts")

# log文件目录
LOG_DIR = valid_path("logs")



