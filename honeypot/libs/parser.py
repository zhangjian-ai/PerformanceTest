import sys
import textwrap
import argparse
import configargparse

from locust.argument_parser import LocustArgumentParser


class HoneypotCommandLine:
    """
    命令行工具
    """

    def __init__(self):
        self.args = []

    def store(self, *args, **kwargs):
        self.args.append(" ".join(args).ljust(32, " ") +
                         ("required" if kwargs.get("required") else str(kwargs.get("default", ""))).ljust(24, " ")
                         + kwargs.get("help"))

    def show(self):
        content = "\nUsage command-line args:\n"
        for line in self.args:
            content += "\n\t" + line

        sys.stdout.write(content)


class ArgumentGroup(argparse._ArgumentGroup):
    def __init__(self, container, title=None, description=None, **kwargs):
        self.container = container
        super(ArgumentGroup, self).__init__(container, title=title, description=description, **kwargs)

    def add_argument(self, *args, **kwargs):
        if kwargs.__contains__("show") and kwargs["show"] is True:
            self.container.cmd.store(*args, **kwargs)

        kwargs.pop("show", None)
        super(ArgumentGroup, self).add_argument(*args, **kwargs)


class HoneypotArgumentParser(LocustArgumentParser):
    """
    重写 LocustArgumentParser 实现命令行参数记录
    """

    def __init__(self, cmd: HoneypotCommandLine, *args, **kwargs):
        super(HoneypotArgumentParser, self).__init__(*args, **kwargs)
        self.cmd = cmd

    def add_argument(self, *args, **kwargs) -> configargparse.Action:
        if kwargs.__contains__("show") and kwargs["show"] is True:
            self.cmd.store(*args, **kwargs)

        kwargs.pop("show", None)
        return super(HoneypotArgumentParser, self).add_argument(*args, **kwargs)

    def add_argument_group(self, *args, **kwargs) -> ArgumentGroup:
        group = ArgumentGroup(self, *args, **kwargs)
        self._action_groups.append(group)
        return group


def get_empty_argument_parser(add_help=False, default_config_files=None):
    if default_config_files is None:
        default_config_files = ["~/.locust.conf", "locust.conf"]

    parser = HoneypotArgumentParser(
        HoneypotCommandLine(),
        default_config_files=default_config_files,
        add_env_var_help=False,
        add_config_file_help=False,
        add_help=add_help,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage=argparse.SUPPRESS,
        description=textwrap.dedent("Usage: python3 honeypot [OPTIONS]")
    )

    return parser


def setup_parser_arguments(parser: HoneypotArgumentParser):
    """
    Setup command-line options
    """
    parser._optionals.title = "Common options"

    parser.add_argument(
        "-f",
        required=True,
        show=True,
        help="Your test-script file, "
             "It should include custom command-line parameters and implementation CRunner",
        env_var="LOCUST_LOCUSTFILE",
        default="locustfile"
    )

    parser.add_argument(
        "-h",
        show=True,
        help="Show all arguments to users"
    )

    parser.add_argument(
        "--host",
        default="http://example.com",
        show=True,
        help="Transfer host to script file"
    )

    stats_group = parser.add_argument_group("Request statistics options")
    stats_group.add_argument(
        "--reset-stats",
        action="store_true",
        env_var="LOCUST_RESET_STATS",
    )
    stats_group.add_argument(
        "--html",
        dest="html_file",
        help="Store HTML report to file path specified",
        env_var="LOCUST_HTML",
    )

    master_group = parser.add_argument_group(
        "Master options",
        "Options for running a Locust Master node when running Locust distributed",
    )

    # if locust should be run in distributed mode as master
    master_group.add_argument(
        "--master",
        action="store_true",
        show=True,
        help="Set locust to run in distributed mode with this process as master",
        env_var="LOCUST_MODE_MASTER",
    )
    master_group.add_argument(
        "--master-bind-host",
        default="*",
        show=True,
        help="Interfaces (hostname, ip) that locust master should bind to. Only used when running with --master",
        env_var="LOCUST_MASTER_BIND_HOST",
    )
    master_group.add_argument(
        "--master-bind-port",
        type=int,
        default=5557,
        show=True,
        help="Port that locust master should bind to. Only used when running with --master. Defaults to 5557.",
        env_var="LOCUST_MASTER_BIND_PORT",
    )
    master_group.add_argument(
        "--expect-workers",
        type=int,
        default=1,
        show=True,
        help="How many workers master should expect to connect before starting the test",
        env_var="LOCUST_EXPECT_WORKERS",
    )
    master_group.add_argument(
        "--expect-workers-max-wait",
        type=int,
        default=0,
        show=True,
        help="How long should the master wait for workers to connect before giving up. Defaults to wait forever",
        env_var="LOCUST_EXPECT_WORKERS_MAX_WAIT",
    )

    master_group.add_argument(
        "--expect-slaves",
        action="store_true",
        help=configargparse.SUPPRESS,
    )

    worker_group = parser.add_argument_group(
        "Worker options",
        """Options for running a Locust Worker node when running Locust distributed.
    Only the LOCUSTFILE (-f option) needs to be specified when starting a Worker, since other options such as -u, -r, -t are specified on the Master node.""",
    )
    # if locust should be run in distributed mode as worker
    worker_group.add_argument(
        "--worker",
        action="store_true",
        show=True,
        help="Set locust to run in distributed mode with this process as worker",
        env_var="LOCUST_MODE_WORKER",
    )
    worker_group.add_argument(
        "--slave",
        action="store_true",
        help=configargparse.SUPPRESS,
    )
    # master host options
    worker_group.add_argument(
        "--master-host",
        default="127.0.0.1",
        show=True,
        help="Host or IP address of locust master for distributed load testing",
        env_var="LOCUST_MASTER_NODE_HOST",
        metavar="MASTER_NODE_HOST",
    )
    worker_group.add_argument(
        "--master-port",
        type=int,
        default=5557,
        show=True,
        help="The port to connect to that is used by the locust master for distributed load testing",
        env_var="LOCUST_MASTER_NODE_PORT",
        metavar="MASTER_NODE_PORT",
    )

    other_group = parser.add_argument_group("Other options")
    other_group.add_argument(
        "-s",
        "--stop-timeout",
        action="store",
        type=int,
        dest="stop_timeout",
        default=None,
        env_var="LOCUST_STOP_TIMEOUT",
    )
    other_group.add_argument(
        "--enable-rebalancing",
        action="store_true",
        default=True,
        dest="enable_rebalancing",
        help="Allow to automatically rebalance users if new workers are added or removed during a test run.",
    )

    tag_group = parser.add_argument_group(
        "Tag options",
    )
    tag_group.add_argument(
        "-T",
        "--tags",
        nargs="*",
        metavar="TAG",
        env_var="LOCUST_TAGS",
        help="List of tags to include in the test, so only tasks with any matching tags will be executed",
    )
    tag_group.add_argument(
        "-E",
        "--exclude-tags",
        nargs="*",
        metavar="TAG",
        env_var="LOCUST_EXCLUDE_TAGS",
        help="List of tags to exclude from the test, so only tasks with no matching tags will be executed",
    )

    web_ui_group = parser.add_argument_group("Web UI options")
    web_ui_group.add_argument(
        "--headless",
        action="store_true",
        env_var="LOCUST_HEADLESS",
    )

    log_group = parser.add_argument_group("Logging options")
    log_group.add_argument(
        "--logfile",
        help="Path to log file. If not set, log will go to stderr",
        env_var="LOCUST_LOGFILE",
    )
