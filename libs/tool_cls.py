from gevent import monkey, time

monkey.patch_all()

import os
import random
import gevent
import logging
import schedule
import threading

from faker import Faker
from copy import deepcopy
from collections import defaultdict
from string import ascii_letters, digits, punctuation

from libs.cio import load_yaml


class Singleton(type):
    """
    单例元类
    """
    __lock = threading.Lock()
    __instances = defaultdict()

    def __call__(cls, *args, **kwargs):
        # 根据调用方、调用参数生成一个唯一的key
        key = cls.__name__ + str(args) + str(kwargs)

        # 加锁，判断当前key是否已有实例
        with Singleton.__lock:
            if key not in Singleton.__instances:
                Singleton.__instances[key] = super(Singleton, cls).__call__(*args, **kwargs)

        return Singleton.__instances[key]


class CFaker:
    """
    动态/随机数据类
    """

    faker = Faker(locale='zh_CN')

    @staticmethod
    def random_str(n: int = 10):
        """
        返回一个随机字符串，默认10位
        :param n:
        :return:
        """
        string = ascii_letters + digits

        return "".join(random.sample(string, n))

    @classmethod
    def random_text(cls):
        """
        随机文本
        :return:
        """
        return cls.faker.sentence().strip(".")


class ScheduleJob:
    """
    自定义任务调度
    """
    # 授权之后启动调度才会成功
    GRANT = False

    # 结束标识
    FINISH = False

    @classmethod
    def add_job(cls, job_func=None, interval=1, *args, **kwargs):
        # 创建任务
        schedule.every(interval).seconds.do(job_func, *args, **kwargs)

    @classmethod
    def run(cls):
        if not cls.GRANT:
            logging.error("调度任务未被授权")
            return

        def worker(schedule_job: ScheduleJob):
            # 持续调度
            while not schedule_job.FINISH:
                schedule.run_pending()
                time.sleep(1)

            # 结束调度
            schedule.clear()

        # 启动调度任务
        gevent.spawn(worker, cls)


class Strategy:
    """
    策略辅助类
    """

    @staticmethod
    def strategy_stage(duration, users, spawn_rate, interval=None):
        """
        标准策略对象
        :param duration:
        :param users:
        :param spawn_rate:
        :param interval:
        :return:
        """
        strategy = {
            "duration": duration,
            "users": users,
            "spawn_rate": spawn_rate
        }

        if interval:
            strategy["interval"] = interval

        return strategy

    @staticmethod
    def parse_strategy(options) -> list:
        """
        根据入参，返回一个有效的strategy列表
        :param options:
        :return:
        """
        strategy = getattr(options, "strategy", 0)
        strategies = []

        if not strategy:
            logging.info(f"📚 strategies information: {strategies}")
            return strategies

        args = [int(_) for _ in strategy.split("_")]

        # 校验策略是否正确
        if len(args) != 4:
            logging.info(f"⚠️ 策略非法，无法完成解析")
            logging.info(f"📚 strategies information: {strategies}")
            return strategies

        start, end, step, duration = args

        # 起始并发数大于结束并发数
        if start > end:
            while True:
                spawn_rate = max(start, 1)
                strategies.append(Strategy.strategy_stage(duration, start, spawn_rate))

                # 每个并发阶段结束，都默认给一个休息时间，通常是测试时间的1/3，但最大不超过90s
                strategies.append(Strategy.strategy_stage(min(duration // 3, 90), 0, spawn_rate))

                if start - step <= end:
                    spawn_rate = max(end, 1)
                    strategies.append(Strategy.strategy_stage(duration, end, spawn_rate))
                    strategies.append(Strategy.strategy_stage(min(duration // 3, 90), 0, spawn_rate))
                    break

                # 迭代
                start -= step
        elif start < end:
            while True:
                # 默认所有用户创建和注销都在3s完成
                spawn_rate = max(start, 1)
                strategies.append(Strategy.strategy_stage(duration, start, spawn_rate))
                strategies.append(Strategy.strategy_stage(min(duration // 3, 90), 0, spawn_rate))

                if start + step >= end:
                    spawn_rate = max(end, 1)
                    strategies.append(Strategy.strategy_stage(duration, end, spawn_rate))
                    strategies.append(Strategy.strategy_stage(min(duration // 3, 90), 0, spawn_rate))
                    break

                # 迭代
                start += step
        else:
            spawn_rate = max(end, 1)
            strategies.append(Strategy.strategy_stage(duration, end, spawn_rate))
            strategies.append(Strategy.strategy_stage(min(duration // 3, 90), 0, spawn_rate))

        # 调整策略开始的停留时间不超过30，通常取为压测时长的1/3
        strategies.insert(0, Strategy.strategy_stage(min(duration // 3, 30), 0, 1))

        logging.info(f"📚 strategies information: {strategies}")
        return strategies


class Interface:
    """
    接口类
    """
    __slots__ = ["apis"]

    def __init__(self, path: str):
        if not os.path.exists(path):
            raise RuntimeError(f"api 文件不存在({path})")

        if not path.endswith(".yaml") and not path.endswith(".yml"):
            raise RuntimeError(f"api 文件格式不正确({os.path.basename(path)})")

        self.apis = load_yaml(path)

    def __getattribute__(self, item):
        if item == "apis":
            return object.__getattribute__(self, item)

        if item not in self.apis:
            raise RuntimeError(f"{item}: 接口文档中没有这样的api")

        data = deepcopy(self.apis[item])

        return data

