import json
import logging
import requests


def http_request(method="POST", url=None, data=None, params=None, headers=None, cookies=None, verify=False):
    """
    二次封装 http request 方法
    """

    # 为POST请求处理Content-Type
    if method.upper() == "POST":
        if headers is None:
            headers = {}

        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

        if 'json' in headers.get("Content-Type"):
            data = json.dumps(data)
    try:
        response = requests.request(method, url, data=data, params=params, headers=headers, cookies=cookies,
                                    verify=verify)

        if response.status_code != 200:
            logging.info(f'请求地址: {response.request.url}')
            logging.info(f'请求方式: {response.request.method}')
            logging.info(f"表单参数: {data}")
            logging.info(f"查询参数: {params}")
            logging.error(f"状态码: {response.status_code}")
            logging.error(f"响应体: {response.text}")

    except Exception as e:
        raise e

    return response
