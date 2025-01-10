## 概述

本工具命名为 夜莺，如果要问原因，那就是我随便想的。

本框架基于locust二次开发，摒弃了locust传统的执行方式，将能更好的满足性能测试需求。




## 注意事项
1. 易于扩展的设计模式，你的测试脚本必须放在 `scripts` 目录下，包括你使用到的测试数据；
2. 使用框架了解 `CRunner` 基类的实现逻辑，因为测试脚本开发必须使用这个类；
3. 自定义脚本主要包含命令行参数定义和`CRunner`子类的实现；
4. 所有虚拟用户共用一个`CRunner`子类实例（你自己写的那个Runner类）；



## 工程介绍

### 关键默认参数

```shell
Usage command-line args:

        -f                  required    Your test-script file, It should include custom command-line parameters and implementation CRunner
        -h                              Show all arguments to users
        --host                          Host and port to load test in the following format: http://10.21.32.33:80
        --strategy                      测试策略 开始并发数_结束并发数_步进数_持续时间(s)
        --strategy_mode                 策略模式。0 并发间配置间隔；1 并发间没有间隔；2 去掉所有缓冲时间
        --recipients                    收件人邮箱 多个用空格隔开
```

说明：

1. -f 表示你的脚本文件，传入脚本文件名，这个参数无论何时都应该被给；
2. -h 表示查看帮助信息，除了打印上面的公共参数外，脚本内自定义的参数也将打印出来；
3. --host 测试脚本需要的请求地址，执行测试时这是必填参数；
4. --strategy 测试策略，执行测试时这是必填参数；
5. 其它参数不做介绍，还有一部分参数使用 -h 可查看详情；



### CRunner解析

**属性解析：**

1. aggregates：存放测试过程中实时数据的列表
2. annexes：报告邮件的附件
3. charts：存放测试结果曲线图的列表
4. env：locust Enviornment对象
5. options：python内置的Namespace对象，用于存放命令行参数，用点号运算符取出
6. tables：存放测试结果统计表格的列表



**方法解析：**

1. setup：测试前置操作。由于所有虚拟用户共用一个Runner实例，因此整个测试前置只会执行一次；
2. teardown：测试后置操作。框架默认做了数据统计、图表绘制、邮件发送等操作；
3. call：请求接口在这个方法中实现，这是抽象方法，子类必须重写；
4. aggregate：聚合个测试阶段的数据，框架已默认实现通用的聚合指标，可重写扩展；
5. build_instruction：构建测试报告的描述信息，可通过入参扩展；
6. build_aggregate：构建聚合报告，内置方法；
7. collect_monitor：收集绘制的图表。框架默认实现了QPS、响应时间的曲线图绘制；



### scripts 目录

自定义测试脚本和数据都放这个目录下，其中：

1. 脚本文件直接放scripts下面，需要自定义实现Runner子类；

2. 数据文件放 scripts/data 目录中，其他脚本用到的配置放到 scripts/config 目录下

4. 各数据文件、配置文件命名尽量和脚本文件保持一致

5. proto文件用如下方式完成python脚本的生成

   ```shell
   python -m grpc_tools.protoc -I .\scripts\data\protos\ --python_out=scripts\data\protos\queryAssists\ --grpc_python_out=scripts\data\protos\queryAssists\ scripts\data\protos\queryAssists.proto
   
   # -I  指定proto文件所在的目录
   # --python_out  指定proto 消息内容的python文件输出目录
   # --grpc_python_out  指定proto grpc定义内容的python文件输出目录
   ```


### 脚本示例

请多看`CRunner`  基类的实现，里面的属性及方法，可以让脚本的开发变得简单。

脚本开发演示：

```python
# 脚本位于scripts目录下，名字：demo.py

from locust import events

from hamster.core.crunner import CRunner
from hamster.core.users import TestUser
from hamster.utils.utils import logger


@events.init_command_line_parser.add_listener
def _(parser):
    """
    注册自定义命令行参数。用法同python的argparse
    """

    parser.add_argument("--name", show=True, default="", help="演示命令行参数注册")


class DemoRunner(CRunner):
    """·
    自定义runner
    """

    def __init__(self, environment):
        super().__init__(environment)
        
        # options属性可以通过点号运算符获取命令行参数，这是从父类继承的
        self.options
        
	# 测试接口逻辑在call方法里面实现
    def call(self, user: TestUser):
        # catch_response=True 表示我们可以自定义成功还是失败结果
        with user.client.post(url=self.options.host, data={}, catch_response=True) as resp:
            res = resp.json()
            
            # 判断接口成功还是失败
            if res["code"] == 0:
                resp.success()
            else:
                logger.error(resp_data)
                resp.failure("请求错误")
```



### 脚本执行

通常的脚本执行命令如下：

```python
# 查询命令行参数，打印所有可用的参数及参数介绍
python hamster -f 脚本文件.py -h

# 执行测试
python hamster -f 脚本文件.py --host 测试地址 --strategy 测试策略 --recipients 收件人
```

