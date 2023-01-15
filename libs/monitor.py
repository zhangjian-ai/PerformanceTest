import io
import os
import math
import time
import logging

from typing import Optional, Tuple, List
from requests import session
from email.mime.image import MIMEImage
from kubernetes import client, config

from libs.cfaker import Dynamic
from libs.cio import load_yaml
from libs.constants import K8S_DIR
from libs.schedule import ScheduleJob


def chart(x_axis: list, y_axis: Optional[Tuple[str, list] or List[Tuple[str, list]]],
          fig_size: Tuple[int, int] = (16, 7), title=None, x_axis_point: int = 64,
          x_label=None, y_label=None, grid=True, points=4320) -> bytes:
    """
    绘制折线图
    :param x_axis: x 轴的值，要求是秒级时间戳
    :param y_axis: y 轴的值，要求是多组数据，每一组对应一个折线
    :param fig_size: 画布的尺寸比例
    :param title: 图表标题
    :param x_axis_point: x 轴坐标的点数，即控制 x 轴坐标显示的密度
    :param x_label: x 轴标签
    :param y_label: y 轴标签
    :param grid: 是否画网格
    :param grid: 是否画网格
    :param points: 画布上最大的坐标点数
    :return:
    """
    import matplotlib.pyplot as plot
    from matplotlib import ticker

    # 设置日志打印登记
    plot.set_loglevel('WARNING')

    figure, axis = plot.subplots(figsize=fig_size, dpi=100)
    canvas = figure.canvas

    # 准备曲线颜色，准备12种颜色对比明显的
    colors = ["#00AA00", "#778899", "#CC6600", "#0088A8", "#990099", "#BBBB00"]

    if not x_axis or not y_axis:
        logging.warning("图表绘制异常，请检查参数 x_axis、y_axis")
        raise RuntimeError("图表绘制异常，请检查参数 x_axis、y_axis")
    else:
        line_count = len(y_axis)

        # 统计图按最大4320个坐标值来绘制。每5s采集一次、标准6小时
        x_temp = []
        step = len(x_axis) // points
        for i in range(0, len(x_axis), step + 1):
            t = x_axis[i]
            if step:
                t = sum(x_axis[i: i + step + 1]) // (step + 1)

            x_temp.append(time.strftime("%d %H:%M:%S", time.localtime(t)))

        for idx in range(line_count):
            # 如果x轴和y轴值个数不同就不绘制
            if len(x_axis) != len(y_axis[idx][1]):
                continue

            y_cur = y_axis[idx][1]
            if step:
                y_temp = []
                for i in range(0, len(x_axis), step + 1):
                    y_temp.append(round(sum(y_cur[i: i + step + 1]) // (step + 1), 2))
                y_cur = y_temp

            line_style = "dashed" if idx else "solid"
            plot.plot(x_temp, y_cur, linestyle=line_style, linewidth=1.2,
                      marker='', label=y_axis[idx][0], color=colors[idx % len(colors)])

    # 指定默认字体：解决plot不能显示中文问题
    # from pylab import mpl
    # mpl.rcParams['font.sans-serif'] = ['STZhongsong']
    # mpl.rcParams['axes.unicode_minus'] = False

    # 设置 x 轴显示密度
    tick_spacing = math.ceil(len(x_temp) / x_axis_point)
    axis.xaxis.set_major_locator(ticker.MultipleLocator(tick_spacing))

    # 设置 x 轴最左刻度和最右刻度
    # axis.set_xlim(left=x_axis[0], right=x_axis[-1])
    axis.set_xlim(auto=True)

    # 设置 x 坐标轴刻度的旋转方向和大小，x 轴通常是时间，为了避免重叠问题，将文本纵向展示
    # rotation: 旋转方向
    plot.xticks(rotation=90, fontsize=8)

    # 显示图例
    plot.legend(loc=2)
    params = {'legend.fontsize': 10}
    plot.rcParams.update(params)

    # 显示网格
    if grid:
        plot.grid(True, linestyle='--', alpha=0.7)

    # 图片、X轴、Y轴的标签
    if x_label:
        plot.xlabel(x_label, fontsize=12)
    if y_label:
        plot.ylabel(y_label, fontsize=12)
    if title:
        plot.title(title, fontsize=14)

    # 调整画布留白
    # 四个坐标值分别表示以左下角为原点的四个边的坐标，最大为1；
    # wspace和hspace则分别表示水平方向上图像间的距离和垂直方向上图像间的距离，有多个画布在一张图中时使用
    plot.subplots_adjust(top=0.94, bottom=0.12, right=0.96, left=0.06, hspace=0, wspace=0)

    # 紧凑布局
    plot.tight_layout()

    # 获取图像流
    buffer = io.BytesIO()
    canvas.print_png(buffer)
    stream = buffer.getvalue()

    # 清理缓存
    buffer.close()

    return stream


class GrafanaMonitor:
    """
    Grafana 监控面板截图
    """

    def __init__(self, spec: str):
        self.grafana = load_yaml("")
        self.params = self.grafana.get(spec)

        if not self.params:
            raise RuntimeError(f"不存在的grafana配置: {spec}")

        self.client = session()
        self.client.headers["Authorization"] = self.params.get("api_key") or self.grafana["api_key"]

        self.host = self.params.get("host") or self.grafana.get("host")
        self.uid = self.params.get("uid") or self.grafana.get("uid")

    def panel_snapshot(self, **kwargs):
        """
        根据配置返回需要截图的邮件对象列表
        [(img_id: str, image: MIMEImage), ...]
        :return:
        """
        panels = self.params.pop("panels")
        params = self.params

        params.update(kwargs)

        snapshots = []

        for panel in panels:
            name = panel.pop("name", None)
            params.update(panel)
            try:
                res = self.client.request(method="GET", url=self.host, params=params)
            except Exception as e:
                logging.info(f"panel 截图失败。panelId: {panel.get('panelId')} \nERROR: {str(e)}")
                continue

            if res.status_code == 200:
                mail_image = MIMEImage(res.content)
                snapshots.append((name, f"{self.uid}-{panel.get('panelId')}", mail_image))

        return snapshots


class KubernetesMonitor:
    """
    k8s 资源信息
    """

    # 实例状态，默认不可用
    status = False

    def __init__(self, namespace=None, config_yaml=None):
        if namespace:
            if not config_yaml:
                config_yaml = "kube-admin.yaml"

            if not config_yaml.endswith(".yaml") and not config_yaml.endswith(".yml"):
                config_yaml += ".yaml"

            self.namespace = namespace
            self.config_yaml = os.path.join(K8S_DIR, config_yaml)

            # 检查配置
            if not os.path.exists(self.config_yaml):
                logging.error(f"kubernetes 目标配置文件不存在({self.config_yaml})")

            # 创建链接
            else:
                try:
                    config.kube_config.load_kube_config(self.config_yaml)
                    self.core_api = client.CoreV1Api()
                    self.custom_api = client.CustomObjectsApi()
                except:
                    pass
                else:
                    # 修改状态
                    self.status = True

                    # metric标识
                    self.metric = True

                    # pod重启次数记录
                    self.restart = {}

                    # 微服务资源配置信息，分两个纬度记录
                    self.service_quotas = {"SERVICE": {}, "POD": {}}
                    self._collect_quotas()

                    # 微服务资源使用信息
                    self.usage = {"SERVICE": {}, "POD": {}}

                    # 添加监控任务
                    ScheduleJob.add_job(self.record_usage, interval=5)

    def _collect_quotas(self):
        """
        收集微服务和pod的资源信息
        """
        try:
            res = self.core_api.list_namespaced_pod(namespace=self.namespace)
        except Exception as e:
            logging.error(f"k8s 微服务及POD信息获取失败: {str(e)}")
            self.status = False
        else:
            for pod in res.items:
                pod_name = pod.metadata.name
                # pod 下的容器
                containers = pod.spec.containers

                # 起始pod重启次数
                container_statuses = pod.status.container_statuses

                for container in containers:
                    resources = container.resources
                    service_name = container.name
                    cpu_requests = self.format_quota(resources.requests["cpu"])
                    cpu_limits = self.format_quota(resources.limits["cpu"])
                    mem_requests = self.format_quota(resources.requests["memory"])
                    mem_limits = self.format_quota(resources.limits["memory"])

                    # 记录quota
                    self.service_quotas["POD"].setdefault(service_name, {})[pod_name] \
                        = [cpu_requests, cpu_limits, mem_requests, mem_limits]

                if container_statuses:
                    for status in container_statuses:
                        service_name = status.name
                        self.restart.setdefault(service_name, {})[pod_name] = status.restart_count

            # 聚合得到服务纬度的资源信息
            self.service_quotas["SERVICE"] = self.merge_quotas(self.service_quotas["POD"])

    @property
    def namespace_resource(self):
        """
        获取namespace整体资源
        """
        table = {
            "title": "环境资源配置",
            "heads": ["命名空间", "分类", "cpu.requests", "cpu.limits", "mem.requests", "mem.limits"]
        }
        lines = []

        try:
            res = self.core_api.list_namespaced_resource_quota(namespace=self.namespace)
            resource = res.items[0].status
        except Exception as e:
            logging.error(f"k8s ns 信息获取失败: {str(e)}")
        else:
            total = resource.hard
            line1 = [self.namespace, "资源总量",
                     self.format_quota(total['requests.cpu']),
                     self.format_quota(total['limits.cpu']),
                     self.format_quota(total['requests.memory']),
                     self.format_quota(total['limits.memory'])]

            lines.append(line1)

            used = resource.used
            line2 = [self.namespace, "当前使用",
                     self.format_quota(used['requests.cpu']),
                     self.format_quota(used['limits.cpu']),
                     self.format_quota(used['requests.memory']),
                     self.format_quota(used['limits.memory'])]

            lines.append(line2)

        table["lines"] = lines
        return table

    @property
    def service_resource(self):
        """
        微服务资源信息
        """
        table = {
            "title": "微服务资源及副本",
            "name": "replicas",
            "heads": ["微服务(容器名)", "cpu.requests(G)", "cpu.limits(G)", "mem.requests(G)", "mem.limits(G)",
                      "副本集", "预期数", "实际数", "就绪数", "可用数"]
        }
        lines = []

        try:
            # 收集分片信息
            res1 = self.custom_api.list_namespaced_custom_object('apps', 'v1', self.namespace, 'statefulsets')
            res2 = self.custom_api.list_namespaced_custom_object('apps', 'v1', self.namespace, 'replicasets')
        except Exception as e:
            logging.error(f"k8s 副本集信息获取失败: {str(e)}")
        else:
            replicas = {}
            for item in res1["items"] + res2["items"]:
                container_name = item['spec']['template']['spec']['containers'][0]['name']
                replica_set = item['metadata']['name']
                expect = item['spec'].get('replicas', 0)

                # 如果当前副本管理器副本数为0，则不统计
                if expect == 0:
                    continue

                real = item['status'].get('replicas', 0)
                ready = item['status'].get('readyReplicas', 0)
                available = item['status'].get('readyReplicas', 0) or item['status'].get('availableReplicas', 0)

                # 一个服务可能有多个副本管理器
                replicas.setdefault(container_name, []).append([replica_set, expect, real, ready, available])

            for service, line in self.service_quotas["SERVICE"].items():
                service_replicas = replicas.get(service, [["-", "-", "-", "-", "-"]])
                for replica in service_replicas:
                    lines.append([service] + line + replica)

        table["lines"] = lines
        return table

    @property
    def pod_resource(self):
        """
        pod资源信息
        """
        table = {
            "title": "POD资源配置",
            "heads": ["微服务(容器名)", "POD名称", "cpu.requests(G)", "cpu.limits(G)", "mem.requests(G)", "mem.limits(G)",
                      "restart"]
        }
        lines = []

        if self.status:
            try:
                # 生成表格时，再查询一次重启次数，与测试开始的记录做差，得到过程中的重启次数
                res = self.core_api.list_namespaced_pod(namespace=self.namespace)
            except Exception as e:
                logging.error(f"k8s 微服务及POD信息获取失败: {str(e)}")
            else:
                for pod in res.items:
                    pod_name = pod.metadata.name
                    container_statuses = pod.status.container_statuses

                    if container_statuses:
                        for status in container_statuses:
                            service_name = status.name
                            self.restart[service_name][pod_name] = \
                                status.restart_count - self.restart.get(service_name, {}).get(pod_name, 0)

        for service, pods in self.service_quotas["POD"].items():
            for pod, line in pods.items():
                lines.append([service, pod] + line + [self.restart.get(service, {}).get(pod, 0)])

        table["lines"] = lines
        return table

    def record_usage(self):
        """
        记录资源使用情况
        """
        if self.status and self.metric:
            try:
                res = self.custom_api.list_namespaced_custom_object('metrics.k8s.io', 'v1beta1', self.namespace, 'pods')
            except Exception as e:
                logging.error(f"k8s metric信息查询失败: {str(e)}")
                self.metric = False
            else:
                temp = {}
                for item in res['items']:
                    pod_name = item['metadata']['name']
                    for container in item['containers']:
                        if container['name'] == "POD":
                            continue

                        service_name = container['name']

                        # bot 测试，去除掉一些不必统计的服务模块
                        if 'bot' in self.namespace:
                            # aiforce、algorithm、web、jaeger、xtrabackup、ddp 这部分服务不参与统计
                            if any([key in service_name for key in
                                    ('aiforce', 'algorithm', 'web', 'jaeger', 'xtrabackup', 'ddp')]):
                                continue

                        cpu_usage = self.format_quota(container['usage']['cpu'])
                        mem_usage = self.format_quota(container['usage']['memory'])

                        temp.setdefault(service_name, {})[pod_name] = [cpu_usage, mem_usage]

                s_time = round(time.time(), 2)
                self.usage['SERVICE'][s_time] = self.merge_quotas(temp)
                self.usage['POD'][s_time] = temp

    @property
    def service_usage_charts(self) -> list:
        """
        微服务资源使用图表
        每张图表示一个微服务以及归属它的pod
        :return:
        """
        x_axis = list(self.usage['SERVICE'].keys())

        scp = {}
        smp = {}
        # 微服务级别
        for single in self.usage['SERVICE'].values():
            for service, usage in single.items():
                cpu_usage, mem_usage = usage
                base = self.service_quotas['SERVICE'][service]
                scp.setdefault(service, []).append(self.operate_quota(cpu_usage, base[1], "/"))
                smp.setdefault(service, []).append(self.operate_quota(mem_usage, base[3], "/"))

        pcp = {}
        pmp = {}
        # pod级别
        for single in self.usage['POD'].values():
            for service, pods in single.items():
                for pod, usage in pods.items():
                    cpu_usage, mem_usage = usage
                    base = self.service_quotas['POD'][service][pod]
                    pcp.setdefault(service, {}).setdefault(pod, []).append(self.operate_quota(cpu_usage, base[1], "/"))
                    pmp.setdefault(service, {}).setdefault(pod, []).append(self.operate_quota(mem_usage, base[3], "/"))

        # 生成chart
        charts = []
        for service, scl in scp.items():
            cpu_y_axis = [(service, scl)]
            mem_y_axis = [(service, smp[service])]
            for pod, pod_line in pcp[service].items():
                cpu_y_axis.append((pod, pod_line))
                mem_y_axis.append((pod, pmp[service][pod]))

            base = self.service_quotas['SERVICE'][service]
            cpu_chart = chart(x_axis, cpu_y_axis, title=f"{service} ({base[1]})",
                              y_label="cpu use percent")
            mem_chart = chart(x_axis, mem_y_axis, title=f"{service} ({base[3]})",
                              y_label="memory use percent")

            # 生成邮件可直接使用的数据结构
            charts.append((f"{service} (CPU)", Dynamic.random_str(12), MIMEImage(cpu_chart)))
            charts.append((f"{service} (MEM)", Dynamic.random_str(12), MIMEImage(mem_chart)))

        return charts

    @staticmethod
    def format_quota(val):
        """
        格式化k8s参数指标
        """
        if not isinstance(val, str):
            val = str(str)

        # 格式化CPU，单位用G
        if val.isdigit():
            return val
        elif 'm' in val:
            return round(int(val[:-1]) / 1000, 3)

        # 格式化内存，单位用 G
        elif 'Mi' in val:
            return round(int(val[:-2]) / 1024, 3)
        elif 'Gi' in val:
            return val[:-2]
        elif 'Ki' in val:
            return round(int(val[:-2]) / (1024 * 1024), 3)
        elif 'M' in val:
            return round(int(val[:-1]) / 1024, 3)
        elif 'G' in val:
            return val[:-1]
        elif 'K' in val:
            return round(int(val[:-1]) / (1024 * 1024), 3)

        return 0.0

    @staticmethod
    def operate_quota(v1, v2, op) -> Optional[str]:
        """
        操作运算
        v1,v2 应该是 format 之后的标准值
        op: + - * /
        """
        if isinstance(v1, str):
            v1 = float(v1)

        if isinstance(v2, str):
            v2 = float(v2)

        if op == "+":
            return round(v1 + v2, 3)
        elif op == "-":
            return round(v1 - v2, 3)
        elif op == "*":
            return round(v1 * v2, 3)
        elif op == "/":
            # 除法运算时，返回百分比
            return round((v1 / v2) * 100, 3)

    @staticmethod
    def merge_quotas(data):
        """
        将特定结构的数据按上一级纬度整合
        :param data:
        :return:
        """
        result = {}
        for service in data:
            line = None
            for pod_values in data[service].values():
                if not line:
                    line = [val for val in pod_values]
                else:
                    for idx in range(len(line)):
                        line[idx] = KubernetesMonitor.operate_quota(line[idx], pod_values[idx], "+")

            result[service] = line

        return result


class LocalMonitor:
    """
    本地监控指标
    框架默认使用
    """

    def __init__(self, environment):
        self.environment = environment

        # 统计对象
        self.metrics = {}

    def record_metrics(self):
        """
        记录动态指标
        :return:
        """
        # 记录动态值
        total = self.environment.stats.total
        self.metrics.setdefault("time", []).append(round(time.time(), 2))
        self.metrics.setdefault("rps", []).append(round(total.current_rps, 1))
        self.metrics.setdefault("fps", []).append(round(total.current_fail_per_sec, 1))
        self.metrics.setdefault("50%ile", []).append(total.get_current_response_time_percentile(0.5) or 0)
        self.metrics.setdefault("90%ile", []).append(total.get_current_response_time_percentile(0.9) or 0)
        self.metrics.setdefault("100%ile", []).append(total.get_current_response_time_percentile(1) or 0)

    @property
    def rps_chart(self) -> Optional[tuple]:
        """
        rps 统计图表
        返回满足邮件使用的插图元组
        """
        title = "Requests per second"
        x_axis = self.metrics["time"]
        y_axis = [("rps", self.metrics["rps"]), ("fail/s", self.metrics["fps"])]

        rps_chart = chart(x_axis, y_axis, title=title, y_label="requests/s")

        return title, Dynamic.random_str(12), MIMEImage(rps_chart)

    @property
    def response_time_chart(self) -> Optional[tuple]:
        """
        response 统计图表
        返回满足邮件使用的插图元组
        """
        title = "Response Time"
        x_axis = self.metrics["time"]
        y_axis = [("50%ile", self.metrics["50%ile"]), ("90%ile", self.metrics["90%ile"]),
                  ("100%ile", self.metrics["100%ile"])]

        response_time_chart = chart(x_axis, y_axis, title=title, y_label="percentile(ms)")

        return title, Dynamic.random_str(12), MIMEImage(response_time_chart)
