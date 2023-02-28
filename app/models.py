"""model数据库模型"""
from datetime import datetime
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from markdown import markdown
import bleach
from flask import current_app, request
from flask_login import UserMixin  # 登录需求属性及方法：登录凭证校验 允许登录 特殊用户 用户标识符等
from flask_login import AnonymousUserMixin  # 检查角色权限
from . import db, login_manager
from flask_sqlalchemy import BaseQuery


class Permission:
    """权限常量 ： 以2的幂表示 每种不同权限组合对应的值唯一"""
    FOLLOW = 1
    COMMENT = 2
    WRITE = 4
    MODERATE = 8
    ADMIN = 16


class Role(db.Model):
    """数据库模型：角色"""
    __tablename__ = 'roles'  # 数据库中表名
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)  # 新用户注册临时角色
    permissions = db.Column(db.Integer)

    # Role和User的一对多关系
    users = db.relationship('User', backref='role', lazy='dynamic')  # 表间关系

    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:  # 新用户注册临时角色
            self.permissions = 0

    @staticmethod
    def insert_roles():
        """
        在数据库中创建角色
        通过角色名查找现有的角色，然后再进行更新。只有当数据库中没有某个角色名时，才会创建新角色对象
        添加新角色，或者修改角色的权限，修改函数顶部的roles 字典，再运行这个函数即可
        “匿名”角色不需要在数据库中表示出来，这个角色的作用就是为了表示不在数据库中的未知用户。
        insert_roles() 是静态方法。无须创建对象，直接在类上调用，例如Role.insert_roles()
        """
        roles = {
            'User': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE],
            'Moderator': [Permission.FOLLOW, Permission.COMMENT,
                          Permission.WRITE, Permission.MODERATE],
            'Administrator': [Permission.FOLLOW, Permission.COMMENT,
                              Permission.WRITE, Permission.MODERATE,
                              Permission.ADMIN],
        }
        default_role = 'User'
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = (role.name == default_role)
            db.session.add(role)
        db.session.commit()

    def add_permission(self, perm):
        """添加权限"""
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        """移除权限"""
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permissions(self):
        """重置权限"""
        self.permissions = 0

    def has_permission(self, perm):
        """检查组合权限是否包含指定单独权限：基于权限常量，使用位与&运算符"""
        return self.permissions & perm == perm

    def __repr__(self):  # 返回具备可读性字符串表示模型 以便调试或测试
        return '<Role %r>' % self.name


class Follow(db.Model):
    """数据库模型：关注关系中的关联表模型"""
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # 增加关注时间 将关联表提升为模型


class User(UserMixin, db.Model):
    """数据库模型：用户"""
    __tablename__ = 'users'  # 数据库中表名
    id = db.Column(db.Integer, primary_key=True)
    workid = db.Column(db.String(64), unique=True, index=True)
    # username = db.Column(db.String(64), unique=True, index=True)
    name = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(64), unique=True, index=True)

    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)  # 令牌状态确认字段
    # name = db.Column(db.String(64))  # 真实姓名
    username = db.Column(db.String(64))  # 真实姓名
    location = db.Column(db.String(64))  # 地址
    about_me = db.Column(db.Text())  # 自我介绍
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)  # 注册时间
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)  # 最后访问时间
    avatar_hash = db.Column(db.String(32))

    # 设置表间关系：所有表间关系都在”一“方定义
    # users与posts的一对多关系
    posts = db.relationship('Post', backref='author', lazy='dynamic')  # todo:注意反向引用名称是 author ！
    # users与users的多对多关系：借用Follow实现，使用两个一对多关系实现自引用情况下的多对多关系
    followed = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],  # 外键
                               backref=db.backref('follower', lazy='joined'),  # 反向调用 回引模型参数
                               lazy='dynamic',  # 跨表查询时返回查询对象而非记录，以便添加过滤器
                               cascade='all, delete-orphan')  # 层叠选项 TODO 级联删除？
    followers = db.relationship('Follow',
                                foreign_keys=[Follow.followed_id],  # 外键
                                backref=db.backref('followed', lazy='joined'),  # 反向调用 回引模型参数
                                lazy='dynamic',  # 跨表查询时返回查询对象而非记录，以便添加过滤器
                                cascade='all, delete-orphan')  # 层叠选项 TODO 级联删除？
    # users与comments的一对多关系
    comments = db.relationship('Comment', backref='author', lazy='dynamic')

    # 【+】user与workhours的一对多关系
    workhours = db.relationship('WorkHour', backref='worker', lazy='dynamic')

    @staticmethod
    def add_self_follows():
        """手工数据更新：将数据库中已有用户全部设为自己的关注者"""
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()

    def __init__(self, **kwargs):
        """定义默认的用户角色：除管理员以配置变量中的邮箱识别外，全部默认为用户"""
        super(User, self).__init__(**kwargs)
        # 设置默认的用户角色：管理员直接根据邮箱设置，其余默认为用户角色
        if self.role is None:
            if self.email == current_app.config['FLASKY_ADMIN']:  # 定义管理员角色
                self.role = Role.query.filter_by(name='Administrator').first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        # 数据库中缓存用户头像散列值 --> 减少重复计算
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = self.gravatar_hash()  # 定义avatar_hash
        # 将用户设为自己的关注者
        self.follow(self)

    @property  # @property装饰器：将类的方法转为类的只读属性，即user.password => 修改需用@fun.setter装饰器另写方法
    def password(self):
        """读取密码时报错：密码转为散列值后无法还原，只能用于校验对错"""
        raise AttributeError('password is not a readable attribute')

    @password.setter  # @fun.setter装饰器：@property将类的方法转为只读属性后 setter定义修改方法
    def password(self, password):
        """密码设置：将密码转为散列值保存"""
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        """密码校验"""
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        """根据用户ID生成确认令牌，有效期3600秒"""
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id}).decode('utf-8')

    def confirm(self, token):
        """验证用户令牌：令牌解码-当前用户ID比对-令牌状态确认-会话提交（数据库未更新）"""
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def generate_reset_token(self, expiration=3600):
        """TODO 用途？"""
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id}).decode('utf-8')

    @staticmethod
    def reset_password(token, new_password):
        """TODO 用途？"""
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        user = User.query.get(data.get('reset'))
        if user is None:
            return False
        user.password = new_password
        db.session.add(user)
        return True

    def generate_email_change_token(self, new_email, expiration=3600):
        """TODO 用途？"""
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps(
            {'change_email': self.id, 'new_email': new_email}).decode('utf-8')

    def change_email(self, token):
        """更改邮箱"""
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = self.gravatar_hash()
        db.session.add(self)
        return True

    def can(self, perm):
        """权限检查"""
        return self.role is not None and self.role.has_permission(perm)

    def is_administrator(self):
        """管理员权限检查"""
        return self.can(Permission.ADMIN)

    def ping(self):
        """刷新用户最后访问时间"""
        self.last_seen = datetime.utcnow()
        db.session.add(self)
        db.session.commit()  # TODO:无需commit？？？

    def gravatar_hash(self):
        """计算散列值"""
        return hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()

    def gravatar(self, size=100, default='identicon', rating='g'):
        """
        生成Gravatar URL:和邮箱关联的用户头像
            根据邮箱信息显示上传至gra网站的头像 无则显示默认头像 TODO 下载or计算？
        """
        # 代码逻辑变了？
        # if request.is_secure:
        #     url = 'https://secure.gravatar.com/avatar'
        # else:
        #     url = 'http://www.gravatar.com/avatar'
        # hash = hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()
        url = 'https://secure.gravatar.com/avatar'
        hash = self.avatar_hash or self.gravatar_hash()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)

    def follow(self, user):
        """添加关注：在follow表中增加关注关系"""
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)  # TODO 和模型字段对不上
            db.session.add(f)

    def unfollow(self, user):
        """取消关注：删除follow表中关注关系"""
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    def is_following(self, user):
        """所有关注我的对象"""
        if user.id is None:
            return False
        return self.followed.filter_by(followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        """所有我关注的对象"""
        if user.id is None:
            return False
        return self.followers.filter_by(follower_id=user.id).first() is not None

    @property  # 用装饰器将方法定义为属性，调用时无需加()。如此一来，所有关系的句法都一样了
    def followed_posts(self):
        """获取所关注用户的文章  ==> 使用跨表联结查询 TODO SQLAlchemy语句总结"""
        return Post.query.join(Follow, Follow.followed_id == Post.author_id) \
            .filter(Follow.follower_id == self.id)

    def __repr__(self):  # 返回具备可读性字符串表示模型 以便调试或测试
        return '<User %r>' % self.name


class AnonymousUser(AnonymousUserMixin):
    """为了操作方便定义AnonymousUser类 实现can()方法和is_administrator()方法"""
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False


login_manager.anonymous_user = AnonymousUser


@login_manager.user_loader
def load_user(user_id):
    """加载用户"""
    return User.query.get(int(user_id))  # 根据ID查找用户对象


# TODO:PASS
class Project(db.Model):
    """
    【+】项目模型
    """
    __tablename__ = 'projects'  # 数据库中表名
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, index=True)
    upl_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # 设置表间关系：所有表间关系都在”一“方定义
    # projects与workhours的一对多关系
    workhours = db.relationship('WorkHour', backref='project', lazy='dynamic')

    # 参考
    # users与posts的一对多关系
    # posts = db.relationship('Post', backref='author', lazy='dynamic')
    # projects与users的多对多关系
    # posts = db.relationship('Post', backref='author', lazy='dynamic')
    # projects与users的多对多关系：借用Follow实现，使用两个一对多关系实现自引用情况下的多对多关系
    # followed = db.relationship('Follow',
    #                            foreign_keys=[Follow.follower_id],  # 外键
    #                            backref=db.backref('follower', lazy='joined'),  # 反向调用 回引模型参数
    #                            lazy='dynamic',  # 跨表查询时返回查询对象而非记录，以便添加过滤器
    #                            cascade='all, delete-orphan')  # 层叠选项 TODO 级联删除？


class WorkHour(db.Model):
    """
    【+】工时模型
    """
    __tablename__ = 'workhours'  # 数据库中表名
    id = db.Column(db.Integer, primary_key=True)
    work = db.Column(db.String(64))  # 工作内容
    hour = db.Column(db.Float)  # 工时
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))  # 项目ID -> backref='project'
    worker_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # 填写人ID -> backref='worker'
    submit_time = db.Column(db.DateTime(), index=True, default=datetime.utcnow)  # 填写时间
    state = db.Column(db.String(64))
    confirm_time = db.Column(db.DateTime(), default=datetime.utcnow)  # 注册时间


class Post(db.Model):
    """数据库模型：博客文章"""
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)  # 用户输入的markdown存入body
    body_html = db.Column(db.Text)  # 在服务器上将markdown转为html存入body_html 避免重复转换
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    # posts与comments的一对多关系
    comments = db.relationship('Comment', backref='post', lazy='dynamic')

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        """markdown格式转换"""
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))


# 定义事件：修改body字段内容时触发，执行Comment.on_changed_body自动把Markdown文本转换成HTML。
# on_changed_body()函数注册在body字段上，是SQLAlchemy“set”事件的监听程序，只要body字段设了新值，这个函数就会自动被调用。
db.event.listen(Post.body, 'set', Post.on_changed_body)


class Comment(db.Model):
    """数据库模型：评论"""
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean)  # 查禁不当评论用
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'em', 'i',
                        'strong']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))


# 定义监控事件：修改body字段内容时触发，执行Comment.on_changed_body自动把Markdown文本转换成HTML。
# on_changed_body()函数注册在body字段上，是SQLAlchemy“set”事件的监听程序，只要body字段设了新值，这个函数就会自动被调用。
db.event.listen(Comment.body, 'set', Comment.on_changed_body)

# ——————————————————————————————————————————————————————————
#
# def addTestData():
#     """测试数据写入数据库"""
#     from werkzeug.security import generate_password_hash
#
#     role1 = Role(name="administer",)
#     db.session.add(role1)
#
#     password_hash = generate_password_hash('cat')
#     user1 = User(email="john@example.com",
#                  username='john',
#                  password_hash=password_hash
#                  )
#     db.session.add(user1)
#
#     db.session.commit()


# if __name__ == "__main__":
#     # #  更新数据库
#     # 删除表
#     db.drop_all()
#     # 创建表
#     db.create_all()
#     # 添加数据
#     addTestData()  # 慎用/数据库已有会导致冲突


# # if __name__ == '__main__':
# u = User()
# u.password = 'cat'
# # print(u.password)  # 报错
# print(u.password_hash)
# print(u.verify_password('cat'))
# print(u.verify_password('dog'))
# u2 = User()
# u2.password = 'cat'
# print(u2.password_hash)
