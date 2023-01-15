import os
import sys
import random
from pathlib import Path

from locust import task, events, FastHttpUser

BASE_DIR = Path(__file__).resolve().parent.parent.parent.__str__()
sys.path.insert(0, BASE_DIR)

# 当前locust使用的c_runner类
from libs.runners import DemoRunner
from libs.strategy import SimpleStrategy

# 每个locust文件必须注册下面两个类
from test.scripts import register

register(DemoRunner, SimpleStrategy)


@events.init_command_line_parser.add_listener
def _(parser):
    """
    注册自定义命令行参数。用法同python的argparse
    """

    parser.add_argument("--host")
    parser.add_argument("--port")
    parser.add_argument("--clean", type=int, default=0, help="测试进程结束时，是否清理业务数据。0:False, 1:True")


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
