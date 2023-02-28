"""应用的配置"""
import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard to guess string'  # 表单必须设置密钥，生成签名和token，Flask-WTF用他来防止CSRF攻击
    # MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.googlemail.com')
    # MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
    # MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    # MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    # MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_SERVER = 'smtp.sina.com'  # 邮件服务器地址
    MAIL_PORT = 25  # 邮件服务器端口
    MAIL_USE_TLS = True  # 启用传输安全协议
    MAIL_USERNAME = 'simon2025@sina.com'  # 邮件账户用户名 TODO:SECRET
    MAIL_PASSWORD = 'xt112233'  # 邮件账户密码 TODO:SECRET

    FLASKY_MAIL_SUBJECT_PREFIX = '[Flasky]'  # 邮件主题前缀
    FLASKY_MAIL_SENDER = 'Flasky Admin <simon2025@sina.com>'  # 发件人<邮箱地址>

    # FLASKY_ADMIN = os.environ.get('FLASKY_ADMIN')
    FLASKY_ADMIN = 'simon2025@sina.com'  # 管理员邮箱

    SQLALCHEMY_TRACK_MODIFICATIONS = False  # 数据库变化跟踪模式：不跟踪变化设为False降低内存消耗
    FLASKY_POSTS_PER_PAGE = 20  # 每页数量-帖子
    FLASKY_FOLLOWERS_PER_PAGE = 50  # 每页数量-关注
    FLASKY_COMMENTS_PER_PAGE = 30  # 每页数量-评论

    # FLASK_ADMIN_SWATCH = 'cerulean'  # todo 管理模块

    @staticmethod
    def init_app(app):  # TODO：用途？
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'data-dev.sqlite')  # 设置数据库，URL位置保存至flask配置对象


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
                              'sqlite://'


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'data.sqlite')


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
