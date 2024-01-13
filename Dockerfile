FROM python:3.8-slim

WORKDIR /data/pt

# copy项目
COPY . .

# 安装依赖、设置时区
RUN rm -rf /etc/localtime && ln -s /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
&& apt-get update --fix-missing && apt-get install -y procps && apt-get clean \
&& pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt \
&& echo 'alias nightingale="python3 nightingale -f"' >> /etc/bash.bashrc

# 启动命令
ENTRYPOINT ["bash", "-c", "while true;do sleep 1;done"]