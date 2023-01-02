import logging
import pymysql

from dbutils.pooled_db import PooledDB
from pymysql.cursors import DictCursor


class DbConnPool:
    """
    数据库连接池
    """

    def __init__(self, host, port, user, password, db=None, mincached=5, maxcached=50):
        self.pool = PooledDB(creator=pymysql,  # 指明创建链接的模块
                             mincached=mincached,  # 池中最小保持的连接数
                             maxcached=maxcached,  # 池中最多存在的连接数
                             ping=0,  # 不主动 ping
                             host=host,
                             port=port,
                             user=user,
                             passwd=password,
                             db=db,
                             use_unicode=True,
                             charset="utf8",
                             cursorclass=DictCursor  # fetch的结果 由默认的元组，改成字典
                             )

    def close(self):
        """
        关闭连接池所有链接
        """
        self.pool.close()

    def _get_(self):
        """
        返回一个链接
        """
        conn = self.pool.connection()
        return conn

    def query(self, sql, params=None, size=None) -> dict:
        """
        执行查询，并取出多条结果集
        @param sql:查询SQL，如果有查询条件，请只指定条件列表，并将条件值使用参数[param]传递进来
        @param params: 可选参数，一级列表/元组
        @param size: 查询条数
        @return: result list(字典对象)/boolean 查询到的结果集
        """
        conn = self._get_()
        cursor = conn.cursor()
        result = None

        try:
            cursor.execute(sql, params)

            if size:
                result = cursor.fetchmany(size)
            else:
                result = cursor.fetchall()
        except Exception as e:
            logging.error(f"\nSQL 查询异常: {str(e)}"
                          f"\n查询语句: {sql}"
                          f"\n参数: {params}\n")
        finally:
            conn.close()

        return result

    def modify(self, sql, params=None) -> int:
        """
        增删改操作多条数据
        @param sql: 要插入的SQL格式
        @param params: 二级列表或元组，根据序列项遍历执行SQL
        @return: count 影响的行数
        """
        conn = self._get_()
        cursor = conn.cursor()
        count = 0

        try:
            if params:
                count = cursor.executemany(sql, params)
            else:
                count = cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error(f"\nSQL 更改异常: {str(e)}"
                          f"\n更改语句: {sql}"
                          f"\n参数: {params}\n")

            conn.rollback()
        finally:
            conn.close()

        return count
