import csv
import json
import yaml
import platform
from typing import Generator


def load_csv(path, delimiter=None) -> Generator:
    """
    加载csv文件，返回一个迭代器，每一次迭代返回一个行数据（用列表记录）
    :param path: csv文件的绝对路径
    :param delimiter: 列表分隔符
    :return:
    """
    if not path.endswith(".csv"):
        raise TypeError("file type is not 'csv'.")

    # 修改csv的限制行数
    csv.field_size_limit(1024 * 1024)

    if not delimiter:
        # 根据操作系统来赋值delimiter
        if platform.system() == "Darwin":
            # Mac 默认是";"
            delimiter = ";"
        else:
            # 其他系统默认使用","
            delimiter = ","

    with open(path, "r", newline='', encoding='utf8') as f:
        buff = csv.reader(f, delimiter=delimiter)
        for line in buff:
            yield line


def load_json(path):
    """
    加载json文件
    :param path:
    :return:
    """
    if not path.endswith(".json"):
        raise TypeError("file type is not 'json'.")

    with open(path, "r", encoding="utf8") as f:
        data = json.load(f)

    return data


def dump_json(path, content, intent=None):
    """
    持久化json文件
    :param path:
    :param content:
    :param intent:
    :return:
    """
    if not path.endswith(".json"):
        raise TypeError("file type is not 'json'.")

    with open(path, "w", encoding="utf8") as f:
        json.dump(content, f, ensure_ascii=False, indent=intent)


def load_yaml(path):
    """
    加载yaml文件
    :param path:
    :return:
    """
    if not path.endswith(".yaml"):
        raise TypeError("file type is not 'yaml'.")

    with open(path, "r", encoding="utf8") as f:
        data = yaml.safe_load(f)

    return data


def dump_yaml(path, content, intent=2):
    """
    持久化yaml文件
    :param path:
    :param content:
    :param intent:
    :return:
    """
    if not path.endswith(".yaml"):
        raise TypeError("file type is not 'yaml'.")

    with open(path, "w", encoding="utf8") as f:
        yaml.safe_dump(content, f, allow_unicode=True, sort_keys=False, indent=intent)
