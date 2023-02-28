"""
主脚本
"""
import os
import click
from flask_migrate import Migrate
from app import create_app, db
from app.models import User, Follow, Role, Permission, Post, Comment, Project, WorkHour

from gevent import pywsgi


app = create_app(os.getenv('FLASK_CONFIG') or 'default')  # 根据配置参数创建一个应用实例
migrate = Migrate(app, db)  # 初始化flask_migrate


@app.shell_context_processor
def make_shell_context():
    """初始化为Python shell定义的上下文"""
    return dict(db=db, User=User, Follow=Follow, Role=Role, Permission=Permission, Post=Post, Comment=Comment,
                Project=Project, WorkHour=WorkHour)


@app.cli.command()
@click.argument('test_names', nargs=-1)
def test(test_names):
    """启动单元测试 Run the unit tests."""
    import unittest
    if test_names:
        tests = unittest.TestLoader().loadTestsFromNames(test_names)
    else:
        tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)


if __name__ == "__main__":
    # 测试服务器
    # app.run()
    # app.run(debug=True)
    app.run(debug=True, host='0.0.0.0', port=8000)

    # 生产服务器
    # server = pywsgi.WSGIServer(('0.0.0.0', 8000), app)
    # server.serve_forever()


"""
本机访问：
http://127.0.0.1:5000/
http://localhost:5000/

内网访问：
http://{内网IP地址}:8000/
http://172.20.10.5:8000/

# 5000是内置端口并未打开，仅用于调试，必须指定运行端口以实现网络交互

查看端口开放情况
netstat -ano
查看某个端口开放情况 [failed]
netstat -ano|findstr 127.0.0.1 8383
"""
