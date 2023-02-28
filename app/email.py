"""邮件功能"""
from threading import Thread
from flask import current_app, render_template
from flask_mail import Message  # 邮件编写扩展包???
from . import mail


def send_async_email(app, msg):  # 发邮件
    """发送邮件：应用 邮件"""
    with app.app_context():  # TODO:人工创建应用上下文
        mail.send(msg)


def send_email(to, subject, template, **kwargs):  # 收件地址 主题 渲染模板 关键字参数列表
    """
    def 发邮件 - 收件地址/邮件主题/模板位置/内容参数列表
        构造邮件 - 主题前缀 /主题 / 发件人 / 收件人
        构造邮件内容 - 邮件模板+txt / 内容参数
        使用邮件模板 - 邮件模板+html / 内容参数
        构造发邮件子线程
        启动线程
    """
    app = current_app._get_current_object()  # 获取当前对象 TODO ???
    msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender=app.config['FLASKY_MAIL_SENDER'], recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    thr = Thread(target=send_async_email, args=[app, msg])  # 创建多线程
    thr.start()  # 启动线程
    return thr
