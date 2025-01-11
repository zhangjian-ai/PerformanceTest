import random

from faker import Faker
from string import ascii_letters, digits, punctuation


class Dynamic:
    """
    动态/随机数据类
    """

    faker = Faker(locale='zh_CN')

    @staticmethod
    def random_str(n: int = 10):
        """
        返回一个随机字符串，默认10位
        :param n:
        :return:
        """
        string = ascii_letters + digits

        return "".join(random.sample(string, n))

    @classmethod
    def random_query(cls, num: int = 0) -> list:
        """
        准备num条随机问句，返回一个列表
        :param num:
        :return:
        """
        queries = []
        chinese_symbol = "！¥，。/、……（）""''；？｜%～·"
        all_bytes = ascii_letters + digits + punctuation + chinese_symbol

        for i in range(num):
            symbol = random.sample(all_bytes, (i + 2) % 5)
            sentence = cls.faker.sentence().strip(".")
            union = symbol + list(sentence)

            # 打乱序列
            random.shuffle(union)

            queries.append("".join(union))

        return queries

    @classmethod
    def random_text(cls):
        """
        随机文本
        :return:
        """
        return cls.faker.sentence().strip(".")

