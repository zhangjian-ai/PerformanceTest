import time
import gevent
import schedule


class ScheduleJob:
    """
    自定义任务调度
    """
    # 有job任务
    has_job = False

    # 运行标识
    running = False

    @classmethod
    def add_job(cls, job_func=None, interval=1, *args, **kwargs):
        # 创建任务
        schedule.every(interval).seconds.do(job_func, *args, **kwargs)

        cls.has_job = True

    @classmethod
    def run(cls):
        cls.running = True

        def worker(sj: ScheduleJob):
            # 持续调度
            while sj.has_job:
                schedule.run_pending()
                time.sleep(4)

            # 结束调度
            schedule.clear()

        # 启动调度任务
        gevent.spawn(worker, cls)
