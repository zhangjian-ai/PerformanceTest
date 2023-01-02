import os
import jinja2
import smtplib
import logging

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from email.mime.base import MIMEBase

from libs.constants import BASE_DIR

smtp_server = 'smtp.exmail.qq.com'
ssl_port = '465'
sender_name = 'Performance-Test'

# 发件人的账号密码
from_addr = ''
password = ''


def send_mail(msg: MIMEBase):
    try:
        smtp = smtplib.SMTP_SSL(host=smtp_server, port=ssl_port)
        smtp.login(user=from_addr, password=password)

        smtp.sendmail(msg["From"], msg["To"].split(","), msg=msg.as_string())
        logging.info("📧 报告邮件已发送，请查收")

    except Exception as e:
        logging.error(f"❌ 邮件发送失败: {str(e)}")

        # 邮件发送失败就保存到本地
        with open(os.path.join(BASE_DIR, "report.eml"), "w") as f:
            f.write(msg.as_string())
            logging.info("报告邮件已持久化保存到项目根目录")


def mail_instance(content: MIMEBase, charts: list = None, recipients: list = None,
                  subject: str = None, annex_files: list = None):
    """
    返回一个邮件实例对象
    :param content:
    :param charts:
    :param recipients:
    :param subject:
    :param annex_files: 文件路径/(文件名, 文件内容)
    :return:
    """
    # 实例化邮件附件
    annexes = []
    if annex_files:
        for file in annex_files:
            if isinstance(file, tuple):
                filename, text = file
            else:
                filename = os.path.basename(file)
                text = open(file, 'rb').read()

            annex_file = MIMEText(text, 'base64', 'utf8')
            annex_file["Content-Type"] = "application/octet-stream"
            annex_file["Content-Disposition"] = f"attachment; filename='{filename}'"
            annexes.append(annex_file)

    # 邮件没有图片时可以直接配置返回
    if not charts and not annexes:
        content["From"] = formataddr((sender_name, from_addr))
        content["To"] = ",".join(recipients)
        content["Subject"] = subject

        return content

    # 需要携带图片/附件
    msg_related = MIMEMultipart('related')

    # 申明一个 可替换媒体类型 的实体来保存文本。以实现对 图片媒体对象的引用
    msg_alternative = MIMEMultipart('alternative')
    msg_alternative.attach(content)

    # 添加文本
    msg_related.attach(msg_alternative)

    # 添加图表
    if charts:
        for _, img_id, image in charts:
            image.add_header('Content-ID', f'<{img_id}>')
            msg_related.attach(image)

    # 添加附件
    if annexes:
        for annex in annexes:
            msg_related.attach(annex)

    # 邮件头部信息
    msg_related["From"] = formataddr((sender_name, from_addr))
    msg_related["To"] = ",".join(recipients)
    msg_related["Subject"] = subject

    return msg_related


def text_instance(template: str = None, **kwargs) -> MIMEText:
    """
    渲染模版，返回文本实例
    :param template: 所有模版都应放在 templates 目录下
    :return:
    """
    if template is None:
        template = "simple_report.html"

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.join(BASE_DIR, "templates")))
    template = env.get_template(template)

    html = template.render(**kwargs)

    return MIMEText(html, "html", "utf8")
