import time

from typing import Optional, Tuple
from locust import LoadTestShape

from libs.framework.utils import logger


class DefaultStrategy(LoadTestShape):
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

    def __init__(self):
        logger.info(f"🚚 du du du ~")
        super(DefaultStrategy, self).__init__()

        # 需要在locust文件通知策略正式开始执行，否则将将一直等待
        self.start = False

        # 策略数量
        self.strategies = None
        self.strategy_num = 0

        # 当前测试的 environment对象 和 c_runner 实例
        self.env = None
        self.c_runner = None

        # 默认从第0组策略开始执行
        self.point = 0

        # 测试启动/结束总时间
        # 为方便使用，这里保存13位毫秒级整数时间戳
        self.begin = round(time.time() * 1000)
        self.finish = None

    def enable(self, environment, c_runner):
        """
        配置各种信息
        """
        self.strategies = StrategySupport.parse_strategy(environment.parsed_options)
        self.strategy_num = len(self.strategies)

        self.env = environment
        self.c_runner = c_runner

        # 启动出发策略执行
        self.reset_time()
        self.env.stats.reset_all()
        self.start = True

    def tick(self) -> Optional[Tuple[int, float]]:
        # 等待locust文件通知
        if not self.start:
            return 0, 1

        # 若无策略，直接结束
        if self.point >= self.strategy_num:
            logger.error("❌ 无可执行策略，测试终止")
            self.finish = round(time.time() * 1000)
            return None

        # 根据测试时间来判断当前策略是否执行完成
        if self.get_run_time() >= self.strategies[self.point]["duration"]:
            # 只要当前阶段由用户在测试就统计一次
            if self.strategies[self.point]["users"] != 0:
                logger.info("Aggregating current concurrency test results...")
                self.c_runner.aggregate()

            if self.point < self.strategy_num - 1:
                self.point += 1
                self.reset_time()
                self.env.stats.reset_all()
            else:
                self.finish = round(time.time() * 1000)
                logger.info("🎉 end of testing")
                return None

            if self.strategies[self.point]["users"]:
                logger.info(f"🚀 {self.strategies[self.point]['users']} users are testing")
            else:
                logger.info(f"☕️ take a rest")

        return self.strategies[self.point]["users"], self.strategies[self.point]["spawn_rate"]


class StrategySupport:
    """
    策略辅助类
    """

    @staticmethod
    def strategy_build(duration, users, spawn_rate):
        """
        标准策略对象
        """
        return {
            "duration": duration,
            "users": users,
            "spawn_rate": spawn_rate
        }

    @classmethod
    def parse_strategy(cls, options) -> list:
        """
        根据入参，返回一个有效的strategy列表
        规则: 起始并发数_结束并发数_步进_每个并发执行时间
        :param options:
        :return:
        """
        strategy = getattr(options, "strategy", 0)
        mode = getattr(options, "strategy_mode")
        strategies = []

        if not strategy:
            logger.error("Argument strategy is required !!!")
            raise RuntimeError("Argument strategy is required !!!")

        args = [int(_) for _ in strategy.split("_")]

        # 校验策略是否正确
        if len(args) != 4:
            logger.error("Argument strategy is illegal !!!")
            raise RuntimeError("Argument strategy is illegal !!!")

        start, end, step, duration = args

        # 起始并发数大于结束并发数
        if start > end:
            while True:
                spawn_rate = max(start // 10, 1)
                strategies.append(cls.strategy_build(duration, start, spawn_rate))

                if start - step <= end:
                    spawn_rate = max(end // 10, 1)
                    strategies.append(cls.strategy_build(duration, end, spawn_rate))
                    break

                # 迭代
                start -= step
        elif start < end:
            while True:
                # 默认所有用户创建和注销都在3s完成
                spawn_rate = max(start // 10, 1)
                strategies.append(cls.strategy_build(duration, start, spawn_rate))

                if start + step >= end:
                    spawn_rate = max(end // 10, 1)
                    strategies.append(cls.strategy_build(duration, end, spawn_rate))
                    break

                # 迭代
                start += step
        else:
            spawn_rate = max(end // 10, 1)
            strategies.append(cls.strategy_build(duration, end, spawn_rate))

        if mode != 2:
            # 增加起止缓冲时间
            strategies.insert(0, cls.strategy_build(min(duration // 5, 30), 0, 1))
            strategies.append(cls.strategy_build(min(duration // 5, 30), 0, strategies[-1]["users"]))

        if mode == 0:
            temp = []
            for i in range(len(strategies)):
                temp.append(strategies[i])
                if i < len(strategies) - 1 and strategies[i]["users"] != 0 and strategies[i + 1]["users"] != 0:
                    temp.append(cls.strategy_build(min(duration // 6, 300), 0, strategies[i]["spawn_rate"]))
            strategies = temp

        logger.info(f"📚 strategies information: {strategies}")
        return strategies
