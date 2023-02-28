"""用户蓝本视图函数：登入 登出 注册 重复登录 未确认全局钩子+未确认账户跳转 再发确认邮件"""
from flask import render_template, redirect, request, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from . import auth  # 引导蓝图
from .. import db  # 数据库对象
from ..models import User  # 用户类
from ..email import send_email  # 邮件
from .forms import LoginForm, RegistrationForm, ChangePasswordForm, \
    PasswordResetRequestForm, PasswordResetForm, ChangeEmailForm, \
    PasswordResetRequestWithoutEmailForm  # 模板


@auth.before_app_request  # 针对全局请求应用的钩子
def before_request():
    """
    定义钩子:使用 @before_app_request 在每次请求前进行判定及处理
    用户已登录
        -> 更新登录时间
        若 账户未确认 + 请求端点名称存在? + URL不在用户蓝本中 + 不是对静态文件的请求 TODO ???
            -> 重定向至 未确认页面
    """
    if current_user.is_authenticated:
        current_user.ping()
        if not current_user.confirmed \
                and request.endpoint \
                and request.blueprint != 'auth' \
                and request.endpoint != 'static':
            return redirect(url_for('auth.unconfirmed'))


@auth.route('/unconfirmed')
def unconfirmed():
    """用户页面跳转 根据登录状态"""
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    """登录"""
    form = LoginForm()  # 登录表单
    if form.validate_on_submit():
        user = User.query.filter_by(workid=form.workid.data).first()  # 通过工号查找用户
        if user is not None and user.verify_password(form.password.data):  # 用户存在且密码验证通过
            login_user(user, form.remember_me.data)  # 调用Flask-Login 的login_user() 函数，在用户会话中把用户标记为已登录。参数：用户名+rememberme
            next = request.args.get('next')  # 获取用户希望访问跳转页面（从其他访问页面跳转至登录页面情况下）
            if next is None or not next.startswith('/'):  # 若无访问页面或页面定位错误
                next = url_for('main.index')  # 重定向至主页
            return redirect(next)  # 重定位到用户希望访问页面
        flash('工号或密码错误 Invalid ID or password.')  # 登录失败闪现消息
    return render_template('auth/login.html', form=form)  # 初始页面


@auth.route('/logout')
@login_required
def logout():
    """退出路由"""
    logout_user()  # 调用Flask-Login 的logout_user() 函数，删除并重设用户会话
    flash('已退出登录')
    return redirect(url_for('main.index'))


@auth.route('/register', methods=['GET', 'POST'])
def register():
    """注册"""
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(workid=form.workid.data,
                    name=form.name.data,
                    email=form.email.data.lower(),
                    confirmed=True,  # 【关闭邮件功能+】
                    password=form.password.data)
        db.session.add(user)
        db.session.commit()
        # token = user.generate_confirmation_token()  # 根据用户ID生成确认令牌，有效期3600秒   # 【关闭邮件功能-】
        # send_email(user.email, '账户激活 Confirm Your Account',  # 【关闭邮件功能-】
        #            'auth/email/confirm', user=user, token=token)  # 【关闭邮件功能-】
        flash('注册成功 You can now login.')  # 【关闭邮件功能+】
        # flash('激活邮件已发送至邮箱，请及时激活！ A confirmation email has been sent to you by email.')  # 【关闭邮件功能-】
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)

# 令牌加密及解密示意
# from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
# s = Serializer(app.config['SECRET_KEY'], expires_in=3600)
# token = s.dumps({ 'confirm': 23 })
# token
# data = s.loads(token)
# data


@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    """确认用户的账户 检查是否重复登录-进行登录校验"""
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    if current_user.confirm(token):
        db.session.commit()
        flash('账户已激活 You have confirmed your account. Thanks!')
    else:
        flash('确认链接无效或已过期 The confirmation link is invalid or has expired.')
    return redirect(url_for('main.index'))


@auth.route('/confirm')
@login_required
def resend_confirmation():
    """重新发送账户确认邮件"""
    token = current_user.generate_confirmation_token()  # 根据用户ID生成确认令牌，有效期3600秒
    send_email(current_user.email, '账户确认 Confirm Your Account',
               'auth/email/confirm', user=current_user, token=token)
    flash('新激活邮件已发送至邮箱 A new confirmation email has been sent to you by email.')
    return redirect(url_for('main.index'))


@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """修改密码"""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.add(current_user)
            db.session.commit()
            flash('密码已更改 Your password has been updated.')
            return redirect(url_for('main.index'))
        else:
            flash('密码错误 Invalid password.')
    return render_template("auth/change_password.html", form=form)


# 【关闭邮件功能+】
@auth.route('/reset', methods=['GET', 'POST'])
def password_reset_request_without_email():
    """忘记密码 无需邮件确认"""
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = PasswordResetRequestWithoutEmailForm()
    if form.validate_on_submit():
        user = User.query.filter_by(workid=form.workid.data,
                                    name=form.name.data,
                                    email=form.email.data.lower()).first()
        if user:
            token = user.generate_reset_token()
            return redirect(url_for('auth.password_reset', token=token))
        else:
            flash('工号或姓名或邮箱错误！ The input information is incorrect！')
    return render_template('auth/reset_password.html', form=form)


# 【关闭邮件功能-】
# @auth.route('/reset', methods=['GET', 'POST'])
def password_reset_request():
    """忘记密码"""
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            token = user.generate_reset_token()
            send_email(user.email, '密码重置 Reset Your Password',
                       'auth/email/reset_password',
                       user=user, token=token)
        flash('密码重置邮件已发送，请尽快处理！ '
              'An email with instructions to reset your password has been '
              'sent to you.')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)


@auth.route('/reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    """重置密码"""
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = PasswordResetForm()
    if form.validate_on_submit():
        if User.reset_password(token, form.password.data):
            db.session.commit()
            flash('密码已重置 Your password has been updated.')
            return redirect(url_for('auth.login'))
        else:
            return redirect(url_for('main.index'))
    return render_template('auth/reset_password.html', form=form)


@auth.route('/change_email', methods=['GET', 'POST'])
@login_required
def change_email_request():
    """修改邮箱"""
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data.lower()
            token = current_user.generate_email_change_token(new_email)
            send_email(new_email, '邮箱确认 Confirm your email address',
                       'auth/email/change_email',
                       user=current_user, token=token)
            flash('邮箱更改邮件已发送，请尽快处理！ '
                  'An email with instructions to confirm your new email '
                  'address has been sent to you.')
            return redirect(url_for('main.index'))
        else:
            flash('邮箱或密码错误。 Invalid email or password.')
    return render_template("auth/change_email.html", form=form)


@auth.route('/change_email/<token>')
@login_required
def change_email(token):
    """修改邮箱确认"""
    if current_user.change_email(token):
        db.session.commit()
        flash('邮箱已更改 Your email address has been updated.')
    else:
        flash('请求无效 Invalid request.')
    return redirect(url_for('main.index'))
