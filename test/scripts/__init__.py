import os
import time
import logging
import traceback

from locust import events, stats
from locust.runners import MasterRunner, LocalRunner

from libs.tool_cls import ScheduleJob, Strategy


def register(c_runner=None, strategy_cls=None):
    """
    配置locust
    指定 CRunner 类 和 LoadTestShape 类
    :param c_runner: CRunner 子类
    :param strategy_cls: LoadTestShape 子类
    :return:
    """
    # c_runner类必传
    if not c_runner:
        raise RuntimeError("必须为当前locust指定CRunner类")

    # 策略类必传
    if not strategy_cls:
        raise RuntimeError("必须为当前locust指定Strategy类")

    # 配置瞬时指标的统计窗口，默认是最近的10s
    stats.CURRENT_RESPONSE_TIME_PERCENTILE_WINDOW = 2

    @events.init.add_listener
    def _(environment, **kwargs):
        # 只在主节点为策略类绑定信息
        if isinstance(environment.runner, (MasterRunner, LocalRunner)):
            strategy_cls.strategies = Strategy.parse_strategy(environment.parsed_options)
            strategy_cls.environment = environment

    @events.test_start.add_listener
    def _(environment, **kwargs):
        """
        session 级别的setup
        注意：此时的 environment 并没有创建完成
        :param environment:
        :param kwargs:
        :return:
        """
        try:
            # 自定义runner放到environment中统一叫c_runner
            # 因为在策略中需要触发结果收集，因此需要统一命名
            environment.c_runner = c_runner(environment)

            if isinstance(environment.runner, (MasterRunner, LocalRunner)):
                # 主节点初始化环境
                environment.c_runner.set_up()

            if not isinstance(environment.runner, MasterRunner):
                # 准备测试样本
                environment.c_runner.build_sample()

            if isinstance(environment.runner, (MasterRunner, LocalRunner)):
                # 如果当前测试进行了数据发布，那么在所有策略之前加一个2分钟的等待时间
                # 通过CRunner类的publish_end来判断
                if getattr(environment.shape_class, "strategies",  0) and environment.c_runner.publish_end:
                    wait_stage = Strategy.strategy_stage(120, 0, 5)
                    environment.shape_class.strategies.insert(0, wait_stage)

                # 通知策略开始执行
                environment.shape_class.start = True

                # 调度任务授权并开始调度
                ScheduleJob.GRANT = True
                ScheduleJob.run()

        except Exception as e:
            logging.error(f"❌ [test_start]测试异常终止({e})\n\n{traceback.format_exc()}")

            # if isinstance(environment.runner, (MasterRunner, LocalRunner)):
            #     try:
            #         # 结束任务调度
            #         ScheduleJob.FINISH = True
            #         # 异常结束是策略无法给结束时间正确赋值，这里手动给值避免teardown出错
            #         environment.shape_class.finish = round(time.time() * 1000)
            #
            #         # 保存测试数据记录信息，并执行后置
            #         environment.c_runner.save_records()
            #         environment.c_runner.tear_down()
            #     except Exception as e:
            #         logging.error(f"❌ [test_start]测试异常终止({e})\n{traceback.format_exc()}")

            # 终止所有测试进程
            os.system("kill -9 $(ps -ef | grep 'locust' | awk '{print $2}')")

    @events.test_stop.add_listener
    def _(environment, **kwargs):
        """
        session 级别的teardown
        :param environment:
        :param kwargs:
        :return:
        """
        # 后处理
        if isinstance(environment.runner, (MasterRunner, LocalRunner)):
            try:
                # 结束任务调度
                ScheduleJob.FINISH = True

                # 执行后置
                environment.c_runner.tear_down()

            except Exception as e:
                logging.error(f"❌ [test_stop]测试异常终止({e})\n\n{traceback.format_exc()}")
                # 终止所有测试进程
                os.system("kill -9 $(ps -ef | grep 'locust' | awk '{print $2}')")
            else:
                logging.info("✅ 测试完成")
