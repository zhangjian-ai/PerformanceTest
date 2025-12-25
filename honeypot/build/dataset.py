import pandas
import requests

from io import BytesIO
from typing import List, Dict


def build_dataset(file: str) -> List[Dict]:
    """
    根据提供的表格文件按行构建数据
    """
    # 获取文件链接
    url = f"http://localhost:8888/common/file/url?fileName={file}"
    resp = requests.get(url).json()
    if resp["code"] != 0:
        raise RuntimeError(f"数据文件不存在 file={file}")
    file_url = resp["data"]
    content = requests.get(file_url).content

    # 构建数据
    lines = []
    if ".csv" in file:
        data = pandas.read_csv(BytesIO(content))
    else:
        data = pandas.read_excel(BytesIO(content))

    cols = [name for name in data.columns]
    for row in data.values:
        line = {}
        for idx in range(len(row)):
            val = row[idx]
            if val == "NAN":
                val = None
            line[cols[idx]] = val
        lines.append(line)

    return lines
