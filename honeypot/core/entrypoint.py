import os
import sys
import time

import locust
import inspect
import logging
import importlib

from importlib.machinery import SourceFileLoader
from locust.main import create_environment, is_user_class

sys.path.insert(0, os.getcwd())

from honeypot import LOCUST_DIR
from honeypot.core.users import TestUser
from honeypot.core.crunner import CRunner
from honeypot.core.strategy import DefaultStrategy
from honeypot.libs.utils import parse_args, set_logging
from honeypot.libs.parser import get_empty_argument_parser, setup_parser_arguments


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

        # load builtin hooks
        importlib.import_module("honeypot.core.hooks")

        # logger
        self.logger = logging.getLogger("locust.runners")

    def _test_before(self):
        """
        测试前的逻辑
        处理帮助信息或完成前置操作
        """
        # load locust file
        module_name = os.path.splitext(self.locust_file)[0]
        source = SourceFileLoader(module_name, self.locust_file_full_path)
        module = source.load_module(module_name)

        # parse command line args
        parser = get_empty_argument_parser()
        setup_parser_arguments(parser)
        locust.events.init_command_line_parser.fire(parser=parser)

        if sys.argv.count("-h") == 1:
            sys.argv.insert(sys.argv.index("-h") + 1, "help")

        self.options = parser.parse_args(args=None)

        if sys.argv.count("-h") == 1:
            parser.cmd.show()
            sys.exit(0)

        if not self.options.__contains__("host"):
            self.logger.error("命令行参数 host 必须提供")
            sys.exit(-1)

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
            raise RuntimeError(f"目标文件中要求有且仅有一个 runner_class")

        if len(user_classes) == 0:
            user_classes.append(TestUser)

        # env
        self.env = create_environment(
            user_classes, self.options, events=locust.events, shape_class=DefaultStrategy(),
            locustfile=os.path.basename(self.locust_file_full_path)
        )

        # create runner
        if self.options.master:
            if self.options.worker:
                raise RuntimeError("The --master argument cannot be combined with --worker")
            if self.options.expect_workers_max_wait and not self.options.expect_workers:
                raise RuntimeError("The --expect-workers-max-wait argument only makes sense "
                                   "when combined with --expect-workers")
            self.env.create_master_runner(
                master_bind_host=self.options.master_bind_host,
                master_bind_port=self.options.master_bind_port)
        elif self.options.worker:
            try:
                self.env.create_worker_runner(self.options.master_host, self.options.master_port)
                self.logger.debug("Connected to locust master: %s:%s", self.options.master_host,
                                  self.options.master_port)
            except OSError as e:
                self.logger.error("Failed to connect to the Locust master: %s", e)
                sys.exit(-1)
        else:
            self.env.create_local_runner()

        # c_runner
        self.env.c_runner = c_runner_classes[0](self.env)

    def _test(self):
        """
        测试执行
        """
        # perform init
        self.env.events.init.fire(environment=self.env, runner=self.env.runner)
        runner = self.env.runner
        if self.options.master:
            # wait for worker nodes to connect
            start_time = time.monotonic()
            while len(runner.clients.ready) < self.options.expect_workers:
                if self.options.expect_workers_max_wait and self.options.expect_workers_max_wait < time.monotonic() - start_time:
                    self.logger.error("Gave up waiting for workers to connect.")
                    runner.quit()
                    sys.exit(1)
                logging.info(
                    "Waiting for workers to be ready, %s of %s connected", len(runner.clients.ready),
                    self.options.expect_workers)

                time.sleep(3)

        # perform performance test
        if not self.options.worker:
            self.env.runner.start_shape()
            self.env.runner.shape_greenlet.join()
        else:
            # worker 模式：等待 runner greenlet 完成（保持与 master 的连接并等待任务）
            self.logger.info("Worker is ready and waiting for tasks from master...")
            self.env.runner.greenlet.join()

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
