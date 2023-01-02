import inspect
import json
import logging
import time
from functools import wraps

from google.protobuf import json_format
from requests.exceptions import RequestException


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
    失败重试
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
