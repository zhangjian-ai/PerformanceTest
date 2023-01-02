import os
import sys
import random
from pathlib import Path

from locust import task, events, FastHttpUser

BASE_DIR = Path(__file__).resolve().parent.parent.parent.__str__()
sys.path.insert(0, BASE_DIR)

# 当前locust使用的c_runner类
from libs.runners import DemoRunner
from libs.strategy import TestStrategy

# 每个locust文件必须注册下面两个类
from test.scripts import register

register(DemoRunner, TestStrategy)


@events.init_command_line_parser.add_listener
def _(parser):
    """
    注册命令行参数。用法同python的argparse
    :param parser:
    :return:
    """

    parser.add_argument("--recipients", nargs="+", default=[], help="* 测试报告收件人，离线/在线操作都会发送邮件")
    parser.add_argument("--clean", type=int, default=0, help="测试进程结束时，是否清理业务数据。0:False, 1:True")
    parser.add_argument("--NAMESPACE", help="部署环境的命名空间")
    parser.add_argument("--edition", help="环境版本号")
    parser.add_argument("--kube_config", help="k8s 环境配置文件以获取部署信息")
    parser.add_argument("--tester", help="测试人员")


class QueryUser(FastHttpUser):
    """
    测试用户
    """

    def __init__(self, environment):
        super().__init__(environment)

        self.c_runner = environment.c_runner
        self.client = self.c_runner.Client(environment)

    @task
    def task(self):
        # 从样本中随机获取数据进行测试
        data = random.choice(self.c_runner.samples)

        self.client.request(data)
