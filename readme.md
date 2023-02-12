## 性能测试

基于 locust。

通过配置不同的测试策略，来控制性能测试流程。比如 负载测试、压力测试、可靠性测试等。

## 框架特点

1. 可为多个系统编写压测脚本，在启动时通过命令行指定脚本即可执行；
2. 通过配置 测试策略，可轻松实现多组并发的压测，不需要多次手动执行；
3. 支持 k8s metric指标采集，体现在报告中；
4. 测试报告中可绘制资源信息图表，对资源使用率一目了然；
5. 框架已经规范好测试执行的流程并实现了CRunner基类，扩展方便。