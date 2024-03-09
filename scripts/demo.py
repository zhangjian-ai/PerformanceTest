from locust import events, FastHttpUser

from nightingale.core.crunner import CRunner


@events.init_command_line_parser.add_listener
def _(parser):
    """
    注册自定义命令行参数。用法同python的argparse
    """

    pass


class DemoRunner(CRunner):
    """
    自定义runner
    """

    def __init__(self, environment):
        super().__init__(environment)

    def call(self, user: FastHttpUser):
        user.client.request(method="post", url=user.host,
                            json={"name": "admin", "password": "admin123"})
