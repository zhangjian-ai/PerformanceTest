"""
capi 的含义是自定义的api，本框架可接入多个产品，因此在新增不同产品的api方法时，应独立分成不同的文件夹
建议格式：
    文件夹名：baidu
    接口文件：baidu.yaml
    封装接口：baidu.py
"""

import grpc
import logging


class Service:
    """
    GRPC服务基类
    """

    def __init__(self, addr):
        logging.info(f"{self.__class__.__name__} 初始化地址: {addr}")

        self.channel = grpc.insecure_channel(addr, options=[('grpc.max_send_message_length', 100 * 1024 * 1024),
                                                            ('grpc.max_receive_message_length', 100 * 1024 * 1024)])

    def close(self):
        """
        关闭通道
        :return:
        """
        if self.channel:
            self.channel.close()
