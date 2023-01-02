from gevent import monkey

monkey.patch_all()

from locust.runners import MasterRunner, LocalRunner

from libs.crunner import CRunner
from libs.monitor import KubernetesMonitor


class DemoRunner(CRunner):
    """
    query 接口 自定义runner
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
        self.options = environment.parsed_options
        self.recipients = self.options.recipients
        self.NAMESPACE = self.options.NAMESPACE
        self.edition = self.options.edition
        self.kube_config = self.options.kube_config
        self.tester = self.options.tester

        if isinstance(environment.runner, (MasterRunner, LocalRunner)):
            # k8s 数据指标采集
            self.k8s = KubernetesMonitor(self.NAMESPACE, self.kube_config)

    def build_sample(self):
        pass

    def set_up(self):
        pass

    def aggregate(self):
        pass

    def arrange(self):
        pass

    def tear_down(self):
        pass
