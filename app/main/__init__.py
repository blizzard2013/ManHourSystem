"""创建主蓝本"""
from flask import Blueprint

main = Blueprint('main', __name__)  # 创建主蓝本

from . import views, errors  # 相对导入 语句中的.表示当前包。
from ..models import Permission


@main.app_context_processor
def inject_permissions():
    """
    上下文处理器：把Permission类加入模板上下文
    使Permission类的所有常量能在模板中访问，用于在模板中检查权限
    """
    return dict(Permission=Permission)
