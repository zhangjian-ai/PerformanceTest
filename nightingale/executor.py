import os
import sys
import locust
import inspect

sys.path.insert(0, os.getcwd())

from importlib.machinery import SourceFileLoader
from locust.argument_parser import parse_options
from locust.main import create_environment, is_user_class

from libs.settings import LOCUST_DIR
from libs.framework.hooks import *
from libs.framework.users import TestUser
from libs.framework.crunner import CRunner
from libs.framework.strategy import DefaultStrategy
from libs.framework.utils import parse_args, set_logging


class Executor:

    def __init__(self):
        # command line args dict
        cmd = parse_args(sys.argv[1:])

        # make sure locust file exists.
        self.locust_file = cmd.get("f")
        self.locust_file_full_path = os.path.join(LOCUST_DIR, self.locust_file)

        if not os.path.exists(self.locust_file_full_path):
            raise RuntimeError(f"文件不存在  {self.locust_file_full_path}")

        # set log
        set_logging(cmd.get("loglevel", "INFO"), cmd.get("logfile"))

    def _test_before(self):
        """
        测试前的逻辑
        处理帮助信息或完成前置操作
        """
        # load locust file
        module_name = os.path.splitext(self.locust_file)[0]
        source = SourceFileLoader(module_name, self.locust_file_full_path)
        module = source.load_module(module_name)

        # load user_class shape_class c_runner_class
        user_classes = list()
        # shape_classes = list()
        c_runner_classes = list()

        for value in vars(module).values():
            if is_user_class(value):
                user_classes.append(value)

            if inspect.isclass(value) and issubclass(value, CRunner) and value != CRunner:
                c_runner_classes.append(value)

        if len(c_runner_classes) != 1:
            raise RuntimeError(f"目标文件中要求有且仅有一个 shape_class")

        if len(user_classes) == 0:
            user_classes.append(TestUser)

        # command line args
        self.options = parse_options()

        # env
        self.env = create_environment(
            user_classes, self.options, events=locust.events, shape_class=DefaultStrategy(),
            locustfile=os.path.basename(self.locust_file_full_path)
        )

        # create runner
        self.env.create_local_runner()

        # c_runner
        self.c_runner_class = c_runner_classes[0](self.env)

    def _test(self):
        """
        测试执行
        """
        # perform init
        self.env.events.init.fire(environment=self.env, runner=self.env.runner, c_runner=self.c_runner_class)

        # perform performance test
        self.env.runner.start_shape()
        self.env.runner.shape_greenlet.join()

    def _test_after(self):
        """
        测试后置
        """
        self.env.runner.quit()

    def run(self):
        """
        执行入口
        """
        self._test_before()

        self._test()

        self._test_after()


if __name__ == '__main__':
    Executor().run()
