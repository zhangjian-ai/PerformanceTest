from locust import events

from honeypot.core.users import TestUser
from honeypot.core.crunner import CRunner

import time


@events.init_command_line_parser.add_listener
def _(parser):
    """
    注册自定义命令行参数。用法同python的argparse
    """

    pass


class DemoRunner(CRunner):
    """
    自定义runner

    分布式
    python honeypot -f demo.py --master --expect-workers 1 --strategy 1_1_1_5
    python honeypot -f demo.py --worker

    单进程
    python honeypot -f demo.py --strategy 1_1_1_5
    """
    host = "http://www.baidu.com"

    def __init__(self, environment):
        super().__init__(environment)

    def call(self, user: TestUser):
        with user.client.request(method="get", url=user.host,
                                 json={"name": "admin", "password": "admin123"},
                                 catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(None)
            time.sleep(1)
