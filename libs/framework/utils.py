import os
import json
import time
import inspect
import logging.config
import logging.handlers

from functools import wraps
from google.protobuf import json_format
from requests.exceptions import RequestException


def path_builder(full_path):
    """
    检查路径
    路径不存在时自动创建
    :param full_path:
    :return:
    """

    if not os.path.isabs(full_path):
        logging.warning(f"参数不是绝对路径，不做处理  {full_path}")

    if not os.path.exists(full_path):
        logging.warning(f"路径不存在({full_path})，自动创建...")

        os.makedirs(full_path)

    return full_path


def parse_args(line: list) -> dict:
    """
    根据cmd列表生成字典
    :param line:
    :return:
    """
    target = {}
    point = 0

    if len(line) == 0:
        return target

    if not line[point].startswith("-"):
        raise RuntimeError("命令行参数有误")

    while point < len(line):
        if line[point].startswith("-"):
            target[line[point].lstrip("-")] = None
            if point + 1 >= len(line):
                break

        cursor = point + 1

        # 连续出现两个参数名时，那么当前key值就是None，继续向后走
        if line[cursor].startswith("-"):
            point = cursor
            continue

        # 若key出现有效值，则进行连续查找
        # 有多个值时，以列表形式为key赋值
        while True:
            if cursor + 1 >= len(line) or line[cursor + 1].startswith("-"):
                break

            cursor += 1

        if cursor - point == 1:
            target[line[point].lstrip("-")] = line[cursor]
        elif cursor - point > 1:
            target[line[point].lstrip("-")] = line[point + 1: cursor + 1]

        point = cursor + 1

    return target


def set_logging(loglevel, logfile=None):
    loglevel = loglevel.upper()

    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": f"[%(asctime)s] %(filename)-12s [%(lineno)-3d] | %(levelname)s | %(name)s: %(message)s",
                "datefmt": '%Y-%m-%d %H:%M:%S'
            },
            "plain": {
                "format": "%(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            },
            "console_plain": {
                "class": "logging.StreamHandler",
                "formatter": "plain",
            },
        },
        "loggers": {
            "locust": {
                "handlers": ["console"],
                "level": loglevel,
                "propagate": False,
            },
            "locust.stats_logger": {
                "handlers": ["console_plain"],
                "level": "INFO",
                "propagate": False,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": loglevel,
        },
    }
    if logfile:
        # if a file has been specified add a file logging handler and set
        # the locust and root loggers to use it
        LOGGING_CONFIG["handlers"]["file"] = {
            "class": "logging.FileHandler",
            "filename": logfile,
            "formatter": "default",
            "mode": "w"
        }
        LOGGING_CONFIG["root"]["handlers"] = ["file"]
        LOGGING_CONFIG["loggers"]["locust"]["handlers"] = ["file"]
        LOGGING_CONFIG["loggers"]["locust.stats_logger"]["handlers"] = ["file"]

    logging.config.dictConfig(LOGGING_CONFIG)


logger = logging.getLogger("locust.runners")


def func_logger(show_input=True):
    """
    装饰器
    为指定函数添加装饰器，实现函数调用前后的日志打印
    """

    def inner(func):
        def wrapper(*args, **kwargs):
            inp = ', '.join(str(val) for val in args[1:]) + ', '.join(key + ':' + str(kwargs[key]) for key in kwargs)
            if show_input:
                logging.info(f"{func.__name__} 请求入参: {inp}")
            # 调用接口并解析PB
            try:
                res = func(*args, **kwargs)
                if res:
                    res = json.loads(json_format.MessageToJson(res,
                                                               including_default_value_fields=True,
                                                               preserving_proto_field_name=True))
            except Exception as e:
                if not show_input:
                    logging.info(f"{func.__name__} 请求入参: {inp}")
                logging.error(str(e))
                raise e

            if res.get("code", -1) != 0:
                if not show_input:
                    logging.info(f"{func.__name__} 请求入参: {inp}")
                logging.error(f"接口返回值: {res}")

            return res

        return wrapper

    return inner


def rpc_logger(show_input=True):
    """
    类装饰器
    :param show_input:
    :return:
    """

    def inner(cls):
        func_list = inspect.getmembers(cls, inspect.isfunction)

        # 过滤掉close的函数，并为满足条件的函数添加装饰器
        for name, func in filter(lambda x: not (x[0].startswith("close") or x[0].startswith("_")), func_list):
            setattr(cls, name, func_logger(show_input=show_input)(func))

        return cls

    return inner


def retry(count: int = 10, interval: int = 2, throw: bool = True):
    """
    装饰器 失败重试
    默认重试10次，间隔2秒
    :param count:
    :param interval:
    :param throw:
    :return:
    """

    def outer(func):
        @wraps(func)
        def inner(*args, **kwargs):
            c = count
            i = interval
            while c > 0:
                try:
                    response = func(*args, **kwargs)
                except (RequestException, RuntimeError) as e:
                    c -= 1
                    if c == 0:
                        logging.error(str(e))
                        if throw:
                            raise e
                        break
                    time.sleep(i)
                    continue

                return response

        return inner

    return outer
