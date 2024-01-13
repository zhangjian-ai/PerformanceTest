from locust import task, events, FastHttpUser

from libs.framework.crunner import CRunner


@events.init_command_line_parser.add_listener
def _(parser):
    """
    注册自定义命令行参数。用法同python的argparse
    """

    parser.add_argument("--clean", type=int, default=0, help="测试进程结束时，是否清理业务数据。0:False, 1:True")


class DemoRunner(CRunner):
    """
    自定义runner
    """

    def __init__(self, environment):
        super().__init__(environment)

    def call(self, user: FastHttpUser):
        user.client.request(method="post", url=user.host,
                            json={"name": "admin", "password": "admin123"})

    def build_sample(self):
        pass

    def set_up(self):
        pass

    def conclude(self):
        super(DemoRunner, self).conclude()

    def aggregate(self):
        super(DemoRunner, self).aggregate()

    def tear_down(self):
        self.send_mail()
