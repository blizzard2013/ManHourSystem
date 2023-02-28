"""用户表单"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Email, Regexp, EqualTo
from wtforms import ValidationError
from ..models import User


class LoginForm(FlaskForm):
    """登录表单"""
    # email = StringField('Email 邮箱', validators=[DataRequired(), Length(1, 64), Email()])
    workid = StringField('工号 ID', validators=[DataRequired(), Length(7, 7, '请输入7位数工号')])
    password = PasswordField('密码 Password', validators=[DataRequired()])
    remember_me = BooleanField('保持登录状态 Keep me logged in')  # 复选框
    submit = SubmitField('登录 Log In')


class RegistrationForm(FlaskForm):
    """
    注册表单
    用户名要求：以字母开头，而且只包含字母、数字、下划线和点号。
    这个验证函数中正则表达式后面的两个参数分别是正则表达式的标志和验证失败时显示的错误消息。
    """
    workid = StringField('工号 ID', validators=[DataRequired(), Length(7, 7, '请输入7位数工号')])
    name = StringField('姓名 Name', validators=[DataRequired(), Length(1, 64), ])
    email = StringField('邮箱 Email', validators=[DataRequired(), Length(1, 64), Email()])
    # username = StringField('用户名', validators=[
    #     DataRequired(), Length(1, 64),
    #     Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
    #            'Usernames must have only letters, numbers, dots or '
    #            'underscores')])  # 用户名正则校验：Regexp(正则表达式,正则表达式匹配模式,验证失败提示)
    password = PasswordField('密码 Password', validators=[
        DataRequired(), EqualTo('password2', message='密码不一致 Passwords must match.')])
    password2 = PasswordField('请再次输入密码 Confirm password', validators=[DataRequired()])
    submit = SubmitField('注册 Register')

    def validate_workid(self, field):
        """工号唯一性验证"""
        if User.query.filter_by(workid=field.data).first():
            raise ValidationError('此工号已存在 This ID already exists.')

    def validate_name(self, field):
        """姓名唯一性验证"""
        if User.query.filter_by(name=field.data).first():
            raise ValidationError('已存在此用户 This user already exists.')

    def validate_email(self, field):
        """邮箱唯一性验证"""
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('此邮箱已注册 Email already registered.')

    def validate_username(self, field):
        """用户名唯一性验证"""
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('此名称已被使用 Username already in use.')


class ChangePasswordForm(FlaskForm):
    """密码修改表单"""
    old_password = PasswordField('老密码 Old password', validators=[DataRequired()])
    password = PasswordField('新密码 New password', validators=[
        DataRequired(), EqualTo('password2', message='密码不一致 Passwords must match.')])
    password2 = PasswordField('请再次输入新密码 Confirm new password',
                              validators=[DataRequired()])
    submit = SubmitField('更改密码 Update Password')


class PasswordResetRequestForm(FlaskForm):
    """忘记密码表单"""
    email = StringField('邮箱 Email', validators=[DataRequired(), Length(1, 64),
                                             Email()])
    submit = SubmitField('重置密码 Reset Password')


class PasswordResetRequestWithoutEmailForm(FlaskForm):
    """忘记密码表单"""
    workid = StringField('工号 ID', validators=[DataRequired(), Length(7, 7, '请输入7位数工号')])
    name = StringField('姓名 Name', validators=[DataRequired(), Length(1, 64), ])
    email = StringField('邮箱 Email', validators=[DataRequired(), Length(1, 64), Email()])
    submit = SubmitField('重置密码 Reset Password')


class PasswordResetForm(FlaskForm):
    """密码重设表单"""
    password = PasswordField('新密码 New Password', validators=[
        DataRequired(), EqualTo('password2', message='密码不一致 Passwords must match')])
    password2 = PasswordField('请再次输入新密码 Confirm password', validators=[DataRequired()])
    submit = SubmitField('重设密码 Reset Password')


class ChangeEmailForm(FlaskForm):
    """修改邮箱表单"""
    email = StringField('新邮箱 New Email', validators=[DataRequired(), Length(1, 64),
                                                 Email()])
    password = PasswordField('密码 Password', validators=[DataRequired()])
    submit = SubmitField('更改邮箱 Update Email Address')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('此邮箱已注册！ Email already registered.')
