import time
import logging

from typing import Optional, Tuple
from locust import LoadTestShape


class MultiStageStrategy(LoadTestShape):
    """
    多阶段测试策略
    组织多轮次 并发数、测试时长 的测试
    如果使用测试策略进行测试，则需要你在 init 钩子为 strategies、environment 赋值。
        strategies: 一个列表，每一项作为一个策略。例如: [{"duration": 100, "users": 10, "spawn_rate": 10}, {}, {}]
            duration: 当前策略的测试周期
            users: 并发数
            spawn_rate: 执行策略时，每秒钟启动多少用户

        environment: 测试环境对象
    同时需要你在locust所有前置工作完成后，主动告知策略开始执行。即设置 environment.shape_class.start = True
    """
    # 负载策略
    strategies = None

    # 测试环境
    environment = None

    def __init__(self):
        logging.info(f"🚚 The test will begin")
        super(MultiStageStrategy, self).__init__()

        # 需要在locust文件通知策略正式开始执行，否则将将一直等待
        self.start = False

        # 为了保证测试时间的精准性，首次调用时，重置一下测试时间。
        # 例如：初始化用户这样的时间不参与统计
        self.stage_init = False

        # 策略数量
        self.strategy_num = 0

        # 默认从第0组策略开始执行
        self.point = 0

        # 测试启动/结束总时间
        # 为方便使用，这里保存13位毫秒级整数时间戳
        self.begin = round(time.time() * 1000)
        self.finish = None

    def tick(self) -> Optional[Tuple[int, float]]:
        # 等待locust文件通知
        if not self.start:
            return 0, 1

        # 由于实例化策略在locust初始化之前，所以计算策略个数在这一步进行
        if not self.strategy_num:
            self.strategy_num = len(self.strategies)

        # 若无策略，直接结束
        if self.point >= self.strategy_num:
            logging.error("❌ 无可执行策略，测试终止")
            self.finish = round(time.time() * 1000)
            return None

        # 用户数达到后才开始统计当前策略的数据
        if self.get_current_user_count() == self.strategies[self.point]["users"] and not self.stage_init:
            # 设置标识为已完成阶段初始化
            self.stage_init = True
            # 重置策略时间和统计信息
            self.reset_time()
            self.environment.stats.reset_all()

            if self.strategies[self.point]["users"]:
                logging.info(f"🚀 {self.get_current_user_count()} users are testing")
            else:
                logging.info(f"☕️ take a rest")

        # 根据测试时间来判断当前策略是否执行完成
        if self.get_run_time() >= self.strategies[self.point]["duration"] and self.stage_init:
            # 统计当前策略的执行结果
            if self.strategies[self.point]["users"]:
                self.environment.c_runner.aggregate()

            if self.point < self.strategy_num - 1:
                # 切换策略并重置计时
                self.point += 1
                self.reset_time()
                self.stage_init = False
            else:
                self.finish = round(time.time() * 1000)
                logging.info("🎉 end of test")
                return None

        return self.strategies[self.point]["users"], self.strategies[self.point]["spawn_rate"]


class SimpleStrategy(LoadTestShape):
    """
    简单策略
    控制单个虚拟用户的起停
    同时需要你在locust所有前置工作完成后，主动告知策略开始执行。即设置 environment.shape_class.start = True
    """

    def __init__(self):
        logging.info(f"🚚 The test will begin")
        super(SimpleStrategy, self).__init__()

        # 需要在locust文件通知策略正式开始执行，否则将将一直等待
        self.start = False

        # 结束标识
        self.end = False

        # 测试启动/结束总时间
        # 为方便使用，这里保存13位毫秒级整数时间戳
        self.begin = round(time.time() * 1000)
        self.finish = None

    def tick(self) -> Optional[Tuple[int, float]]:
        # 等待locust文件通知
        if not self.start:
            return 0, 1

        if self.start and not self.end:
            return 1, 1

        # 结束测试
        self.finish = round(time.time() * 1000)
        return None


class StrategySupport:
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

    @classmethod
    def parse_strategy(cls, options) -> list:
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
                strategies.append(cls.strategy_stage(duration, start, spawn_rate))

                # 每个并发阶段结束，都默认给一个休息时间，通常是测试时间的1/3，但最大不超过90s
                strategies.append(cls.strategy_stage(min(duration // 3, 90), 0, spawn_rate))

                if start - step <= end:
                    spawn_rate = max(end, 1)
                    strategies.append(cls.strategy_stage(duration, end, spawn_rate))
                    strategies.append(cls.strategy_stage(min(duration // 3, 90), 0, spawn_rate))
                    break

                # 迭代
                start -= step
        elif start < end:
            while True:
                # 默认所有用户创建和注销都在3s完成
                spawn_rate = max(start, 1)
                strategies.append(cls.strategy_stage(duration, start, spawn_rate))
                strategies.append(cls.strategy_stage(min(duration // 3, 90), 0, spawn_rate))

                if start + step >= end:
                    spawn_rate = max(end, 1)
                    strategies.append(cls.strategy_stage(duration, end, spawn_rate))
                    strategies.append(cls.strategy_stage(min(duration // 3, 90), 0, spawn_rate))
                    break

                # 迭代
                start += step
        else:
            spawn_rate = max(end, 1)
            strategies.append(cls.strategy_stage(duration, end, spawn_rate))
            strategies.append(cls.strategy_stage(min(duration // 3, 90), 0, spawn_rate))

        # 调整策略开始的停留时间不超过30，通常取为压测时长的1/3
        strategies.insert(0, cls.strategy_stage(min(duration // 3, 30), 0, 1))

        logging.info(f"📚 strategies information: {strategies}")
        return strategies
