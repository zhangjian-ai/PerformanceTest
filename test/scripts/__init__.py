import os
import logging
import traceback

from locust import events, stats
from locust.runners import MasterRunner, LocalRunner

from libs.schedule import ScheduleJob
from libs.strategy import StrategySupport


def register(c_runner=None, strategy_cls=None):
    """
    配置locust
    指定 CRunner 类 和 LoadTestShape 类
    :param c_runner: CRunner 子类
    :param strategy_cls: LoadTestShape 子类
    :return:
    """
    # c_runner类必传
    if not c_runner:
        raise RuntimeError("必须为当前locust指定CRunner类")

    # 策略类必传
    if not strategy_cls:
        raise RuntimeError("必须为当前locust指定Strategy类")

    # 配置瞬时指标的统计窗口，默认是最近的10s
    stats.CURRENT_RESPONSE_TIME_PERCENTILE_WINDOW = 2

    # 默认命令行
    @events.init_command_line_parser.add_listener
    def _(parser):
        """
        注册框架默认的命令行参数
        """
        parser.add_argument("--edition")
        parser.add_argument("--tester")
        parser.add_argument("--recipients", nargs="+", default=[])
        parser.add_argument("--NAMESPACE")
        parser.add_argument("--kube_config")

    @events.init.add_listener
    def _(environment, **kwargs):
        # 只在主节点为策略类绑定信息
        if isinstance(environment.runner, (MasterRunner, LocalRunner)):
            strategy_cls.strategies = StrategySupport.parse_strategy(environment.parsed_options)
            strategy_cls.environment = environment

    @events.test_start.add_listener
    def _(environment, **kwargs):
        """
        session 级别的setup
        注意：此时的 environment 并没有创建完成
        :param environment:
        :param kwargs:
        :return:
        """
        try:
            # 自定义runner放到environment中统一叫c_runner
            # 因为在策略中需要触发结果收集，因此需要统一命名
            environment.c_runner = c_runner(environment)

            if isinstance(environment.runner, (MasterRunner, LocalRunner)):
                # 主节点初始化环境
                environment.c_runner.set_up()

            if not isinstance(environment.runner, MasterRunner):
                # 准备测试样本
                environment.c_runner.build_sample()

            if isinstance(environment.runner, (MasterRunner, LocalRunner)):
                # 通知策略开始执行
                environment.shape_class.start = True

                # 调度任务开始执行
                ScheduleJob.run()

        except Exception as e:
            logging.error(f"❌ [test_start]测试异常终止({e})\n\n{traceback.format_exc()}")

            # 终止所有测试进程
            os.system("kill -9 $(ps -ef | grep 'locust' | awk '{print $2}')")

    @events.test_stop.add_listener
    def _(environment, **kwargs):
        """
        session 级别的teardown
        :param environment:
        :param kwargs:
        :return:
        """
        # 后处理
        if isinstance(environment.runner, (MasterRunner, LocalRunner)):
            try:
                # 规整测试数据
                environment.c_runner.conclude()

                # 执行后置
                environment.c_runner.tear_down()

            except Exception as e:
                logging.error(f"❌ [test_stop]测试异常终止({e})\n\n{traceback.format_exc()}")
                # 终止所有测试进程
                os.system("kill -9 $(ps -ef | grep 'locust' | awk '{print $2}')")
            else:
                logging.info("✅ 测试完成")
