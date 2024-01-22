import os
import traceback

from locust import events, stats
from locust.runners import MasterRunner, LocalRunner

from libs.framework.utils import logger
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
    # 策略配置
    parser.add_argument("--strategy", help="测试策略 开始并发数_结束并发数_步进数_持续时间(s)")
    parser.add_argument("--strategy_mode", type=int, default=0, help="策略模式。0 并发间配置间隔；1 并发间没有间隔；2 去掉所有缓冲时间")

    # 测试人员
    parser.add_argument("--tester", default="夜莺", help="测试人员名字")

    # k8s 配置
    parser.add_argument("--kube_ns", help="kubernetes namespace 名称")
    parser.add_argument("--kube_config", help="kubernetes kube_config 文件名称，需要手动挂在到config路径下")

    # 邮件相关配置
    parser.add_argument("--smtp_server", default='smtp.exmail.qq.com', help="邮箱服务地址")
    parser.add_argument("--ssl_port", default='465', help="邮箱服务端口")
    parser.add_argument("--sender_name", default='Performance-Test', help="发件人名称")
    parser.add_argument("--from_addr", default=None, help="发件人邮箱")
    parser.add_argument("--password", default=None, help="发件人邮箱密码")
    parser.add_argument("--recipients", nargs="+", default=[], help="收件人邮箱 多个用空格隔开")


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
        # 校验shape类型
        if not isinstance(environment.shape_class, DefaultStrategy):
            raise RuntimeError("shape_class 不是 DefaultStrategy 的实例")

        # 只在主节点为策略类绑定信息
        if isinstance(environment.runner, (MasterRunner, LocalRunner)):
            environment.shape_class.enable(environment)

        # 主节点初始化环境
        if isinstance(environment.runner, (MasterRunner, LocalRunner)):
            environment.shape_class.c_runner.set_up()

        if isinstance(environment.runner, (MasterRunner, LocalRunner)):
            # 通知策略开始执行
            environment.shape_class.start = True

            # 调度任务开始执行
            ScheduleJob.run()

    except Exception as e:
        logger.info(f"[ test_start ]测试异常终止({e}){traceback.format_exc()}")

        logger.info("Test is finished with error")

        os.system("kill -9 $(ps -ef | grep 'executor.py' | awk '{print $2}')")


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
            # 执行后置
            environment.shape_class.c_runner.tear_down()

        except Exception as e:
            logger.error(f"[ test_stop ]测试异常终止({e})\n\n{traceback.format_exc()}")

            logger.error("Test is finished with error")
        else:
            logger.info("Test is finished")
        finally:
            os.system("kill -9 $(ps -ef | grep 'executor.py' | awk '{print $2}')")
