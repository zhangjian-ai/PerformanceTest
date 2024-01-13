import os
import logging
import traceback

from locust import events, stats
from locust.runners import MasterRunner, LocalRunner, logger

from libs.framework.schedule import ScheduleJob
from libs.framework.strategy import DefaultStrategy

# 配置瞬时指标的统计窗口，默认是最近的10s
stats.CURRENT_RESPONSE_TIME_PERCENTILE_WINDOW = 2


# 默认命令行
@events.init_command_line_parser.add_listener
def _(parser):
    """
    注册框架默认的命令行参数
    """

    parser.add_argument("--strategy")
    parser.add_argument("--strategy_mode", type=int, default=0, help="策略模式。0 并发间配置间隔；1 并发间没有间隔；2 去掉所有缓冲时间")
    parser.add_argument("--tester")
    parser.add_argument("--namespace")
    parser.add_argument("--kube_config")

    # 邮件相关配置
    parser.add_argument("--smtp_server", default='smtp.exmail.qq.com')
    parser.add_argument("--ssl_port", default='465')
    parser.add_argument("--sender_name", default='Performance-Test')
    parser.add_argument("--from_addr", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--recipients", nargs="+", default=[])


@events.init.add_listener
def _(environment, **kwargs):
    # 校验shape类型
    if not isinstance(environment.shape_class, DefaultStrategy):
        raise RuntimeError("shape_class 不是 DefaultStrategy 的实例")

    # 只在主节点为策略类绑定信息
    if isinstance(environment.runner, (MasterRunner, LocalRunner)):
        environment.shape_class.enable(environment, kwargs["c_runner"])


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
        if isinstance(environment.runner, (MasterRunner, LocalRunner)):
            # 主节点初始化环境
            environment.shape_class.c_runner.set_up()

        if not isinstance(environment.runner, MasterRunner):
            # 准备测试样本
            environment.shape_class.c_runner.build_sample()

        if isinstance(environment.runner, (MasterRunner, LocalRunner)):
            # 通知策略开始执行
            environment.shape_class.start = True

            # 调度任务开始执行
            ScheduleJob.run()

    except Exception as e:
        logger.error(f"❌ [test_start]测试异常终止({e})\n\n{traceback.format_exc()}")

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
            environment.shape_class.c_runner.conclude()

            # 执行后置
            environment.shape_class.c_runner.tear_down()

        except Exception as e:
            logger.error(f"❌ [test_stop]测试异常终止({e})\n\n{traceback.format_exc()}")
            # 终止所有测试进程
            os.system("kill -9 $(ps -ef | grep 'locust' | awk '{print $2}')")
        else:
            logger.info("✅  test is finished")
