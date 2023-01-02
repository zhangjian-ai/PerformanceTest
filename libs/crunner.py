import time
import logging

from abc import ABCMeta, abstractmethod
from locust.runners import MasterRunner, LocalRunner
from locust.stats import calculate_response_time_percentile as cp

from libs.mail import text_instance, mail_instance, send_mail
from libs.monitor import LocalMonitor
from libs.tool_cls import ScheduleJob


class CRunner(metaclass=ABCMeta):
    """
    自定义Runner抽象类
    """

    @abstractmethod
    def __init__(self, environment, monitor=True):
        self.environment = environment

        if not isinstance(environment.runner, MasterRunner):
            # 请求样本集
            self.samples = []

        if isinstance(environment.runner, (MasterRunner, LocalRunner)):
            # 测试人员
            self.tester = None

            # 如果发布了知识则对其赋值。10 位的时间戳
            self.publish_start = None
            self.publish_end = None

            # 测试数据统计信息
            self.stat = None

            # 聚合结果集
            self.aggregations = []

            # 普通统计表格
            self.tables = []

            # 邮件图表
            self.charts = []

            # 邮件附件
            self.annexes = []

            # 默认收集 rps、response_time 过程指标
            if monitor:
                self.local_monitor = LocalMonitor(environment)
                ScheduleJob.add_job(self.local_monitor.record_metrics, interval=2)

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

    def build_sample(self):
        """
        实现该方法，以构建请求样本
        建议放入 samples 列表中
        * 框架自动调用 *
        """
        pass

    def aggregate(self):
        """
        实现该方法，以收集各个阶段的聚合结果
        建议放入 aggregations 列表中
        * 框架自动调用 *
        """
        pass

    def arrange(self):
        """
        实现该方法，以整理各类型数据
        子类整理的数据请一定放入指定列表，
        基类已经实现常用的表格和图表，子类如需使用，完成调用即可
        注意: 该方法将被 send_mail 自动调用，将从指定的列表取值
        """
        pass

    def default_aggregate(self):
        """
        默认聚合指标
        可以不使用而全部自定义
        :return:
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

    def description_table(self, data: dict = None):
        """
        描述信息表格
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
        publish_start = self.environment.c_runner.publish_start
        publish_end = self.environment.c_runner.publish_end

        start = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start))
        end = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end))

        publish_start = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(publish_start)) if publish_start else "-"
        publish_end = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(publish_end)) if publish_end else "-"

        heads = ["运行模式", "节点数量", "测试开始", "测试结束", "发布开始", "发布结束"]
        line = [run_mode, workers, start, end, publish_start, publish_end]

        # 添加自定义描述信息
        if isinstance(data, dict):
            for key, val in data.items():
                heads.append(key)
                line.append(val)
        elif data:
            logging.error(f"描述信息期望是 DICT 类型，不是 {type(data)}")

        data = {"title": "测试描述信息", "heads": heads, "lines": [line]}

        self.tables.append(data)

    def knowledge_table(self):
        """
        测试数据表格
        """
        if isinstance(self.stat, dict):
            table = {
                "title": "测试数据",
                "heads": self.stat.keys(),
                "lines": [self.stat.values()]
            }

            self.tables.append(table)

    def aggregate_table(self):
        """
        聚合报告表格
        """
        # 聚合报告
        if self.aggregations:
            data = {"title": "聚合报告", "heads": self.aggregations[0].keys(), "lines": []}
            for res in self.aggregations:
                data["lines"].append(res.values())

            self.tables.append(data)

    def local_charts(self):
        """
        本地监控图表
        """
        # 收集默认图表
        if ScheduleJob.GRANT:
            self.charts.append(self.local_monitor.rps_chart)
            self.charts.append(self.local_monitor.response_time_chart)

    def send_mail(self, title: str = "性能测试报告", recipients: list = None, **kwargs):
        """
        发送邮件
        :param title: 报告标题
        :param recipients: 收件人
        """
        # 发邮件之前，需要整理数据
        self.arrange()

        # 生成邮件并发送
        date = time.strftime('%Y-%m-%d %H:%M', time.localtime(self.environment.shape_class.begin / 1000))
        text = text_instance(title=title, tables=self.tables, charts=[x[0:2] for x in self.charts],
                             tester=self.tester, date=date, **kwargs)
        email = mail_instance(content=text, recipients=recipients, subject=title,
                              charts=self.charts, annex_files=self.annexes)
        send_mail(email)
