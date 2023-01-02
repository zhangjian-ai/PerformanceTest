import os
import re
import sys
import time
import logging
import platform

from pathlib import Path
from copy import deepcopy

BASE_DIR = Path(__file__).resolve().parent.parent.__str__()
sys.path.insert(0, BASE_DIR)

from libs.cio import load_yaml
from libs.constants import SCENE_DIR, LOCUST_DIR, LOG_DIR, valid_path

# 配置默认logger输出格式
logging.basicConfig(format='%(asctime)s | %(levelname)-6s | %(filename)-20s [ %(lineno)-4d ] - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO)


def manager(file, scenes, workers, master_host, master_port, others: dict):
    """
    启动测试。默认为每个测试场景生成一个日志文件，保存到 test/logs 中
    :param file:
    :param scenes:
    :param workers:
    :param master_host:
    :param master_port:
    :param others: 这部分参数将透传给locust文件
    :return:
    """
    # 检查文件是否存在
    locust_file = os.path.join(LOCUST_DIR, file)
    if not os.path.exists(locust_file):
        logging.error(f"locust文件({locust_file})不存在。")
        return

    # 根据场景生成locust的命令行参数
    cmd_lines = []

    if scenes:
        scene_file = os.path.join(SCENE_DIR, file.replace(".py", ".yaml"))
        if not os.path.exists(scene_file):
            logging.error(f"配置文件({scene_file})不存在。")
            return

        all_scenes = load_yaml(scene_file)

        # 默认场景配置
        default = all_scenes.get("default", {})

        for scene_name in scenes:
            scene = all_scenes.get(scene_name)
            if scene:
                # 实时配置的参数覆盖scene默认配置
                cur = deepcopy(default)
                cur.update(scene)
                cur.update(others)
                cmd_lines.append((format_args(cur), os.path.join(LOG_DIR, scene_name + ".log"), scene_name))
            else:
                logging.error(f"不存在的场景配置: {scene_name}")
                return
    else:
        cmd_lines.append((format_args(others), os.path.join(LOG_DIR, file.split(".")[0] + ".log"), file.split(".")[0]))

    if not cmd_lines:
        logging.error("locust 命令行构建失败，请检查命令行参数的合法性。")
        return

    # 按场景启动测试
    for line, log_path, scene_name in cmd_lines:
        logging.info(f"{scene_name} 场景测试开始，可通过日志文件({log_path})查看测试进度。")

        # 听说Windows不支持locust的分布式
        if workers and platform.system() != "Windows":
            # 启动主机
            os.system(
                f"nohup locust -f {locust_file} --headless --only-summary --master --expect-workers {workers} "
                f"--master-bind-host {master_host} --master-bind-port {master_port} {line} > {log_path} 2>&1 &")

            # 从节点的日志单独记录到日志
            for i in range(workers):
                os.system(
                    f"nohup locust -f {locust_file} --headless --only-summary --worker --master-host {master_host} "
                    f"--master-port {master_port} {line} > {log_path.replace('.log', f'_{i + 1}.log')} 2>&1 &")

            # 检查当前测试是否完成，完成则进入下一轮测试
            count = 0
            while True:
                out = os.popen(cmd="ps -ef | grep locust")
                ps = out.readlines()

                has_worker = False
                has_master = False
                for p in ps:
                    if "--master-host" in p:
                        has_worker = True
                    elif "--expect-workers" in p:
                        has_master = True

                # 只有从节点需要杀掉从节点进程，上限5次
                if has_worker and not has_master:
                    count += 1
                    if count == 6:
                        os.system("kill -9 $(ps -ef | grep ' --master-host' | awk '{print $2}')")
                # 只有主节点需要杀掉主节点进程，上限5次
                elif has_master and not has_worker:
                    count += 1
                    if count == 6:
                        os.system("kill -9 $(ps -ef | grep ' --expect-workers' | awk '{print $2}')")
                # 如果都没有，则说明测试结束
                elif not has_master and not has_worker:
                    break

                # 如果在测试中，那么就等待5秒再次检查
                time.sleep(5)
        else:
            # os.system(f"locust -f {locust_file} --headless --only-summary {line} 2>&1 |tee -a {log_path}")
            os.system(f"nohup locust -f {locust_file} --headless --only-summary {line} > {log_path} 2>&1 &")


def format_args(data: dict) -> str:
    """
    根据KV生成命令行
    :param data:
    :return:
    """
    line = ""
    for key, val in data.items():
        if val:
            if isinstance(val, (list, tuple)):
                val = " ".join(val)
            line += f"--{key} {val} "

    return line


def parse_args(line: list) -> dict:
    """
    根据cmd列表生成字典
    :param line:
    :return:
    """
    target = {}
    point = 0

    if len(line) == 0:
        return target

    if not line[point].startswith("-"):
        raise RuntimeError("命令行参数有误")

    while point < len(line):
        if line[point].startswith("-"):
            target[line[point].lstrip("-")] = None
            if point + 1 >= len(line):
                break

        cursor = point + 1

        # 连续出现两个参数名时，那么当前key值就是None，继续向后走
        if line[cursor].startswith("-"):
            point = cursor
            continue

        # 若key出现有效值，则进行连续查找
        # 有多个知识，以列表形式为key赋值
        while True:
            if cursor + 1 >= len(line) or line[cursor + 1].startswith("-"):
                break

            cursor += 1

        if cursor - point == 1:
            target[line[point].lstrip("-")] = line[cursor]
        elif cursor - point > 1:
            target[line[point].lstrip("-")] = line[point + 1: cursor + 1]

        point = cursor + 1

    return target


def build_help(file) -> str:
    """
    返回locust文件各参数的帮助信息
    """
    # 返回值
    string = f"\n  {file} 文件帮助信息如下: \n\n"

    # 后缀检查
    if not file.endswith(".py"):
        file += ".py"

    # 检查文件是否存在
    file = os.path.join(LOCUST_DIR, file)
    if not os.path.exists(file):
        string += f"    文件不存在({file})\n"

    # 构建帮助信息
    out = os.popen(cmd=f"grep 'parser.add_argument' {file}")
    lines = out.readlines()

    for line in lines:
        name = "--" + re.findall(r'--([\w_]+?)\"', line)[0]
        text = re.findall(r'help=\"(.+?)\"', line)[0]
        default = re.findall(r'default=(.+), [a-z]+=', line)
        default = default[0] if default else "null"
        multi = 'nargs' in line
        required = 'required' in line

        label = f"【默认值：{default}{', required' if required else ''}{', multi' if multi else ''}】"
        string += f"{name.rjust(24)}: {label.ljust(48)} {text}\n"

    return string + "\n"


def show_config(file):
    """
    返回config目录下，配置文件内容
    """
    if not file:
        return "\n  命令行参数 -c 必须显示的指定一个配置文件名\n\n"

    # 所有配置文件默认都是yaml格式
    if not file.endswith(".yaml"):
        file += ".yaml"

    # 目标文件绝对路径
    target = None

    # 遍历查找目标文件
    for root, _, files in os.walk(valid_path('config')):
        if file in files:
            target = os.path.join(root, file)
            break

    if not target:
        return f"\n  配置文件目录中未找到目标文件({file})\n\n"

    out = os.popen(cmd=rf"cat -n {target}")
    return f"\n{out.read()}\n"


def enum_file(path):
    """
    返回目录下的文件(不包含目录)
    """
    if not os.path.isdir(path):
        logging.error(f"目标路径不是目录({path})")
        return []

    _, _, files = os.walk(path).__next__()

    return filter(lambda x: not x.startswith("__"), files)


if __name__ == '__main__':
    # 解析命令行参数为字典
    args_dict = parse_args(sys.argv[1:])

    if "h" in args_dict:
        # 帮助信息
        # 如果h无值，就返回manage的帮助信息
        if not args_dict.get("h"):
            sys.stdout.write(
                "\n  manege文件帮助信息如下:\n\n"
                f"{'-h'.rjust(16)}: 查看帮助信息，接受一个locust文件名(可不带后缀)。无值时返回manage帮助信息，有值时返回对应locust文件的帮助信息\n"
                f"{'-c'.rjust(16)}: 查看配置信息，接受一个配置文件名(可不带后缀)，若传入locust一个文件名，则返回其scene配置信息(locust文件与scene文件同名)\n"
                f"{'--file'.rjust(16)}: * 测试的locust文件名(可不带后缀)，执行测试时必填(在manage层面通常也只需要关注该参数)。"
                f"可取值: {' '.join(enum_file(valid_path('test/scripts')))}\n"
                f"{'--scenes'.rjust(16)}: 场景配置(可不配置)，接受多值。通常locust文件命令行参数繁多，可通过scene将常用的参数配置好，测试时只传递变更的几个参数即可\n"
                f"{'--workers'.rjust(16)}: 分布式节点数量。默认不启动分布式，该字段赋值且大于0时，将启动分布式测试，工作节点数量为该值\n"
                f"{'--master_host'.rjust(16)}: 分布式测试时，主节点的IP。默认值: 127.0.0.1\n"
                f"{'--master_port'.rjust(16)}: 分布式测试时，主节点的PORT。默认值: 5557\n"
                "\n"
                "  注意: \n"
                "   1、优先级 h > c > 其他，高优先级的参数存在时，忽略低优先级参数\n"
                "   2、在线测试时，locust文件参数直接写在manage参数后面即可\n"
                "   3、场景配置，挂载到 config/scenes 路径下，如果命令行参数与scene重复，则以命令行为准\n"
                "   4、k8s配置，挂载到 config/k8s 路径下，具体使用方式取决于 locust 脚本\n\n"
            )
        else:
            # 有值返回目标文件的帮助信息
            file = args_dict.get("h")
            info = build_help(file)
            sys.stdout.write(info)
    elif "c" in args_dict:
        # 查看配置文件信息
        file = args_dict.get("c")
        info = show_config(file)
        sys.stdout.write(info)
    else:
        # 测试进程管理
        file = args_dict.pop("file")
        scenes = args_dict.pop("scenes", [])
        workers = args_dict.pop("workers", 0)
        master_host = args_dict.pop("master_host", "127.0.0.1")
        master_port = args_dict.pop("master_port", 5557)

        # 节点数量和端口号转成int
        workers = int(workers)
        master_port = int(master_port)

        # 如果只有一个场景，将其转成列表
        if scenes and isinstance(scenes, str):
            scenes = [scenes]

        # 检查file文件知否有后缀
        if not file.endswith(".py"):
            file += ".py"

        manager(file, scenes, workers, master_host, master_port, args_dict)
