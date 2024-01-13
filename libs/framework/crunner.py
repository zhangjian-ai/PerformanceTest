import time
import logging

from abc import ABCMeta, abstractmethod

from locust import User
from locust.runners import MasterRunner, LocalRunner
from locust.stats import calculate_response_time_percentile as cp

from libs.framework.mail import Mail
from libs.framework.utils import logger
from libs.framework.schedule import ScheduleJob
from libs.framework.monitor import LocalMonitor, KubernetesMonitor


class CRunner(metaclass=ABCMeta):
    """
    自定义Runner抽象类
    """

    @abstractmethod
    def __init__(self, environment, monitor=True):
        self.monitor = monitor
        self.environment = environment

        # 前后置操作通常只需要在主节点执行
        if isinstance(environment.runner, (MasterRunner, LocalRunner)):
            # 固定框架参数
            self.edition = getattr(environment.parsed_options, "edition", "-")
            self.tester = getattr(environment.parsed_options, "tester", "-")

            self.NAMESPACE = getattr(environment.parsed_options, "namespace", None)
            self.kube_config = getattr(environment.parsed_options, "kube_config", None)

            # 测试样本
            self.samples = []

            # 各阶段的统计数据
            self.aggregates = []

            # 需要渲染到报告的表格，列表用于保存多个表格对象
            self.tables = []

            # 邮件图表，保存图表对象的元组。(名字, ID, 邮件图片对象)
            self.charts = []

            # 邮件附件，content对象或者文件路径
            self.annexes = []

            # 默认收集 rps、response_time 过程指标
            if self.monitor:
                self.lm = LocalMonitor(environment)
                ScheduleJob.add_job(self.lm.record_metrics, interval=2)

            # k8s监控
            self.k8s = KubernetesMonitor(self.NAMESPACE, self.kube_config)

    @abstractmethod
    def set_up(self):
        """
        子类的所有前置操作应该在这里组织并执行
        * 框架自动调用 *
        """
        pass

    @abstractmethod
    def tear_down(self):
        """
        子类的所有后置操作应该在这里组织并执行
        * 框架自动调用 *
        """
        pass

    @abstractmethod
    def call(self, user: User):
        """
        实现请求调用及自定义结果
        * 在User类的task中调用 *
        """

    def build_sample(self):
        """
        实现该方法，以构建请求样本。推荐放入 samples 中
        * 框架自动调用 *
        """
        pass

    def aggregate(self):
        """
        实现该方法，以收集各个阶段的聚合结果
        * 框架自动调用 *
        """
        self.aggregates.append(self.default_aggr())

    def conclude(self):
        """
        实现该方法，以归纳测试数据，构建好表格、图片等报告邮件需要的信息
        * 框架自动调用 *
        """
        self.tables.append(self.describe_table())
        self.tables.append(self.aggregate_table())

        self.collect_monitor()

    # ====================== 下面是可选的一些通用的方法 ======================

    def default_aggr(self) -> dict:
        """
        默认聚合指标，收集通用的聚合指标
        可以不使用而全部自定义，也可以通过入参追加定制化的聚合指标
        total: environment.stats.total
        """
        total = self.environment.stats.total

        return {
            "开始时间": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(total.start_time)),
            "并发数量": self.environment.runner.user_count,
            "测试时长": str(round(total.last_request_timestamp - total.start_time)) + "s",
            "平均响应": str(round(total.avg_response_time, 1)) + "ms",
            "最小响应": str(round(total.min_response_time, 1)) + "ms",
            "最大响应": str(round(total.max_response_time, 1)) + "ms",
            "50%ile": str(cp(total.response_times, total.num_requests, 0.5)) + "ms",
            "90%ile": str(cp(total.response_times, total.num_requests, 0.9)) + "ms",
            "95%ile": str(cp(total.response_times, total.num_requests, 0.95)) + "ms",
            "99%ile": str(cp(total.response_times, total.num_requests, 0.99)) + "ms",
            "100%ile": str(cp(total.response_times, total.num_requests, 1)) + "ms",
            "请求总数": total.num_requests,
            "QPS": round(total.total_rps, 2),
            "fails": total.num_failures,
            "fail%": round(total.fail_ratio * 100, 2),
            "FPS": round(total.total_fail_per_sec, 2),
            "PPS": round(total.total_rps - total.total_fail_per_sec, 2)
        }

    def describe_table(self, data: dict = None) -> dict:
        """
        测试的一些描述信息
        已添加常用的字段，可通过参数传入想要补充的字段信息
        """
        # 运行模式
        run_mode = "Local"
        if self.environment.parsed_options.master:
            run_mode = "Distributed"

        # 测试节点数量
        workers = self.environment.parsed_options.expect_workers

        # 时间信息
        start = self.environment.shape_class.begin / 1000
        end = self.environment.shape_class.finish / 1000

        start = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start))
        end = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end))

        heads = ["运行模式", "节点数量", "测试开始", "测试结束"]
        line = [run_mode, workers, start, end]

        # 添加自定义描述信息
        if isinstance(data, dict):
            for key, val in data.items():
                heads.append(key)
                line.append(val)
        elif data:
            logging.error(f"描述信息期望是 DICT 类型，不是 {type(data)}")

        data = {"title": "测试描述信息", "heads": heads, "lines": [line]}

        return data

    def aggregate_table(self):
        """
        将多阶段的聚合数据规范成聚合报告表格
        """
        data = {"title": "聚合报告", "heads": self.aggregates[0].keys(), "lines": []}
        for res in self.aggregates:
            data["lines"].append(res.values())

        return data

    def collect_monitor(self):
        """
        收集环境信息，监控图表
        """
        # 实时数据采集
        if ScheduleJob.running:
            # 本地监控
            if self.monitor:
                self.charts.append(self.lm.rps_chart)
                self.charts.append(self.lm.response_time_chart)

            # 静态资源
            if self.k8s.status:
                self.tables.append(self.k8s.namespace_resource)
                self.tables.append(self.k8s.service_resource)
                self.tables.append(self.k8s.pod_resource)

                # 统计图表
                self.charts.extend(self.k8s.service_usage_charts)

    def send_mail(self, title: str = "性能测试报告", **kwargs):
        """
        发送邮件
        :param title: 报告标题
        """
        mail = Mail(self.environment.parsed_options)

        # 生成邮件并发送
        date = time.strftime('%Y-%m-%d %H:%M', time.localtime(self.environment.shape_class.begin / 1000))
        text = mail.text_instance(title=title, tables=self.tables, charts=[x[0:2] for x in self.charts],
                                  tester=self.tester, date=date, **kwargs)
        email = mail.mail_instance(content=text, subject=title,
                                   charts=self.charts, annex_files=self.annexes)
        mail.send_mail(email)
