"""应用包的构造文件"""
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_pagedown import PageDown

from config import config

from flask_admin import Admin  # 管理模块


bootstrap = Bootstrap()
mail = Mail()
moment = Moment()
db = SQLAlchemy()
pagedown = PageDown()

login_manager = LoginManager()
login_manager.login_view = 'auth.login'  # 设置登录页面端点 TODO:用途？

admin = Admin()  # 管理模块


def create_app(config_name):
    """
    工厂函数:根据配置名称导入配置参数实例化项目
    """
    app = Flask(__name__)
    app.config.from_object(config[config_name])  # app.config配置对象提供的from_object()方法导入配置类
    config[config_name].init_app(app)  # 配置对象，则可以通过名称从config 字典中选择

    # 初始化扩展 在之前创建的扩展对象上调用init_app()便可以完成初始化
    bootstrap.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    pagedown.init_app(app)

    admin.init_app(app)  # 管理模块

    """以下添加路由和自定义的错误页面"""

    """注册主蓝本"""
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    """注册身份验证蓝本"""
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')


    return app
