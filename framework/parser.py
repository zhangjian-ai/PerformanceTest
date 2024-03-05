import sys
import textwrap
import argparse
import configargparse

from locust.argument_parser import LocustArgumentParser


class NightingaleCommandLine:
    """
    命令行工具
    """

    def __init__(self):
        self.args = []

    def store(self, *args, **kwargs):
        self.args.append(" ".join(args).ljust(20, " ") + ("required" if kwargs.get("required") else " ").ljust(12, " ")
                         + kwargs.get("help"))

    def show(self):
        content = "\nUsage command-line args:\n"
        for line in self.args:
            content += "\n\t" + line

        sys.stdout.write(content)


class NightingaleArgumentParser(LocustArgumentParser):
    """
    重写 LocustArgumentParser 实现命令行参数记录
    """

    def __init__(self, cmd: NightingaleCommandLine, *args, **kwargs):
        super(NightingaleArgumentParser, self).__init__(*args, **kwargs)
        self.cmd = cmd

    def add_argument(self, *args, **kwargs) -> configargparse.Action:
        if kwargs.__contains__("show") and kwargs["show"] is True:
            self.cmd.store(*args, **kwargs)

        kwargs.pop("show", None)
        return super(NightingaleArgumentParser, self).add_argument(*args, **kwargs)


def get_empty_argument_parser(add_help=False, default_config_files=["~/.locust.conf", "locust.conf"]):
    parser = NightingaleArgumentParser(
        NightingaleCommandLine(),
        default_config_files=default_config_files,
        add_env_var_help=False,
        add_config_file_help=False,
        add_help=add_help,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage=argparse.SUPPRESS,
        description=textwrap.dedent(
            """
            Usage: python3 nightingale [OPTIONS] 

        """
        )
    )

    return parser


def setup_parser_arguments(parser):
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
        show=True,
        help="Host and port to load test in the following format: http://10.21.32.33:80"
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

