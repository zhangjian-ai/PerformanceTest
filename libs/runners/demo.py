from gevent import monkey

monkey.patch_all()

from libs.crunner import CRunner


class DemoRunner(CRunner):
    """
    自定义runner
    """

    class Client:
        """
        将client放入crunner，在
        """

        def __init__(self, environment):
            pass

        def request(self, data):
            pass

    def __init__(self, environment):
        super().__init__(environment)
        # 获取命令行参数
        options = environment.parsed_options

        self.host = options.host
        self.port = options.port
        self.clean = options.clean

    def build_sample(self):
        pass

    def set_up(self):
        pass

    def conclude(self):
        pass

    def tear_down(self):
        pass
