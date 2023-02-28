from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SelectField, SubmitField, FloatField  # 表单类型
from wtforms.validators import DataRequired, Length, Email, Regexp, NumberRange  # 表单验证函数
from wtforms import ValidationError
from flask_pagedown.fields import PageDownField
from ..models import Role, User, Project


class NameForm(FlaskForm):  # 构建第一个表单类
    """
    表单设计，各字段都定义为类变量：
    1 name输入框：提示文字 + 非空校验
    2 submit按钮：按钮文字
    """
    # select = SelectField(label="项目", choices=['FE', 'KC'])  # 下拉列表
    # name = StringField('what is your name', validators=[AnyOf(['777'], message="必须等于777")])  # 文本字段
    name = StringField('What is your name?', validators=[DataRequired()])  # 文本字段
    submit = SubmitField('Submit')  # 提交按钮


class EditProfileForm(FlaskForm):
    """
    资料编辑表单
    用户资料都是可选的，因此验证函数最小值为0（最大不超过64）
    """
    username = StringField('用户名 Username', validators=[Length(0, 64)])
    location = StringField('位置 Location', validators=[Length(0, 64)])
    about_me = TextAreaField('自我介绍 About me')
    submit = SubmitField('提交 Submit')


class EditProfileAdminForm(FlaskForm):
    """
    管理员资料编辑表单
    版本问题修订：
    从WTForms 2.3.0版本开始，电子邮件验证由称为email-validator（PR＃429）的外部库处理。
    如果要启用电子邮件验证支持，则需要安装WTForms并附带其他要求email：pip install wtforms[email]
    或者，您可以email-validator直接安装：pip install email-validator
    或者，您可以返回旧版本的WTForms：pip install wtforms==2.2.1
    PS:如果使用Flask-WTF,除了直接安装email-validator外，在下一版本（> 0.14.3）中可以直接使用email（flask-WTF打补丁）
    """
    workid = StringField('工号 ID', validators=[DataRequired(), Length(7, 7, '请输入7位数工号')])
    name = StringField('姓名 Real name', validators=[
        DataRequired(), Length(1, 64),
        # Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
        #        'Usernames must have only letters, numbers, dots or '
        #        'underscores')])
    ])
    email = StringField('邮箱 Email', validators=[DataRequired(), Length(1, 64),
                                                Email()])
    confirmed = BooleanField('账户激活 Confirmed')
    role = SelectField('角色权限 Role', coerce=int)  # todo:下拉列表 用于选择用户角色：coerce=int将字段值转为整数
    username = StringField('用户名 Username', validators=[Length(0, 64)])
    location = StringField('位置 Location', validators=[Length(0, 64)])
    about_me = TextAreaField('自我介绍 About me')
    submit = SubmitField('提交 Submit')

    def __init__(self, user, *args, **kwargs):
        """
        role:SelectField
        SelectField实例必须在其choices 属性中设置各选项。
            选项必须是一个由元组构成的列表，各元组都包含两个元素：选项的标识符，以及显示在控件中的文本字符串。
        choices 表在表单的构造函数中设定，
            其值从Role 模型中获取，使用一个查询按照角色名的字母顺序排列所有角色。
            元组中的标识符是角色的id，因为这是个整数，所以在SelectField构造函数中加上了coerce=int参数，把字段的值转换为整数，而不使用默认的字符串。
        """
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)  # todo:用途？？？
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]  # TODO:重要 表单内实现数据库下拉列表
        self.user = user

    def validate_workid(self, field):
        """工号唯一性验证"""
        if field.data != self.user.workid and \
                User.query.filter_by(workid=field.data).first():
            raise ValidationError('此工号已存在 This ID already exists.')

    def validate_name(self, field):
        """姓名唯一性验证"""
        if field.data != self.user.name and \
                User.query.filter_by(name=field.data).first():
            raise ValidationError('已存在此用户 This user already exists.')

    def validate_email(self, field):
        """
        email自定义验证：若email变化但数据库已有 -> 报错
        """
        if field.data != self.user.email and \
                User.query.filter_by(email=field.data).first():
            raise ValidationError('邮箱已注册 Email already registered.')

    def validate_username(self, field):
        """
        username自定义验证：若email变化但数据库已有 -> 报错
        """
        if field.data != self.user.username and \
                User.query.filter_by(username=field.data).first():
            raise ValidationError('用户名已使用 Username already in use.')


class PostForm(FlaskForm):
    """博客帖子模板 ：支持markdown的文章表单"""
    body = PageDownField("记录你的想法 What's on your mind?", validators=[DataRequired()])
    submit = SubmitField('发布 Submit')


class CommentForm(FlaskForm):
    """
    评论输入表单
    # 尝试自动生成表单数量失败
    def __init__(self, num):
        for i in range(num):
            exec('test' + str(i) + ' = ' + "StringField('吐槽', validators=[DataRequired()])")
    """
    body = StringField('吐槽 Enter your comment', validators=[DataRequired()])
    submit = SubmitField('提交 Submit')


class WorkHourForm(FlaskForm):
    # 【+】工时填写表单
    project = SelectField('项目 Project', coerce=int)  # todo:下拉列表 用于选择项目：coerce=int将字段值转为整数
    work = TextAreaField('工作内容 Work', validators=[DataRequired()])
    hour = FloatField('投入工时 Time', validators=[DataRequired(), NumberRange(0, 1, "单个项目工时应在0~1之间")])
    submit = SubmitField('保存 Save')

    def __init__(self, *args, **kwargs):
        super(WorkHourForm, self).__init__(*args, **kwargs)  # todo:用途？？？
        self.project.choices = [(project.id, project.name)
                                for project in Project.query.order_by(Project.name).all()]  # TODO:重要 表单内实现数据库下拉列表


class WorkHourEditForm(FlaskForm):
    # 【+】工时修改表单
    work = TextAreaField('工作内容 Work', validators=[DataRequired()])
    hour = FloatField('投入工时 Time', validators=[DataRequired(), NumberRange(0, 1, "单个项目工时应在0~1之间")])
    submit = SubmitField('保存 Save')



class WorkHourSubmitForm(FlaskForm):
    # 【+】工时提报按钮
    submit1 = SubmitField('提交 Submit')
