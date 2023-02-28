"""主蓝本视图函数：index"""
from datetime import datetime
from flask import render_template, redirect, url_for, abort, flash, request,\
    current_app, make_response
from flask_login import login_required, current_user
from . import main  # 引导蓝图
from .forms import EditProfileForm, EditProfileAdminForm, PostForm, CommentForm, WorkHourForm, WorkHourEditForm, WorkHourSubmitForm  # 表单
from .. import db  # 数据库对象
from ..models import Permission, Role, User, Post, Comment, WorkHour, Project  # 用户类
from ..decorators import admin_required, permission_required  # 权限检查
from sqlalchemy import func

from .. import admin
from flask_admin.contrib.sqla import ModelView
from flask_admin.menu import MenuLink

admin.add_view(ModelView(User, db.session))  # 管理页面增加表展示
admin.add_view(ModelView(Project, db.session))
admin.add_view(ModelView(WorkHour, db.session))
admin.add_view(ModelView(Post, db.session))
admin.add_view(ModelView(Comment, db.session))

admin.add_link(MenuLink(name='Home Page', url='/'))

# from flask_admin.contrib.fileadmin.s3 import S3FileAdmin
# admin.add_view(S3FileAdmin('files_bucket', 'us-east-1', 'key_id', 'secret_key')


@main.route('/', methods=['GET', 'POST'])  # 主蓝本中定义的应用路由 路由装饰器由蓝本提供，因此使用的是main.route，而非app.route
def index():
    """
    登录首页:只有欢迎字样
    """
    current_user
    return render_template('index.html')


@main.route('/blog', methods=['GET', 'POST'])  # 主蓝本中定义的应用路由 路由装饰器由蓝本提供，因此使用的是main.route，而非app.route
def blog():
    """
    博客文章首页路由
        V1写新博客 -> 需先进行写权限校验
        V3切换选项卡 显示所有博客文章或只显示所关注用户的文章
        V1显示博客列表 V2分页显示
    """
    form = PostForm()
    if current_user.can(Permission.WRITE) and form.validate_on_submit():
        post = Post(body=form.body.data,
                    author=current_user._get_current_object())  # 获取当前用户ID TODO:重点:属性用author，而非author_id
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('.blog'))
    page = request.args.get('page', 1, type=int)  # 渲染/展示页数

    # 从cookie中获取切换选项卡的值，根据值从数据库查询所有用户blog或者关注用户blog
    # 未登录用户采用默认值，返回所有blog
    show_followed = False

    # 登录用户从用户cookies中获取值
    if current_user.is_authenticated:  # 如果用户提供的登录凭据有效，返回True，否则返回False
        show_followed = bool(request.cookies.get('show_followed', ''))  # 查询cookies中的show_followed值并转为布尔值

    # 根据选项卡值（所有对象or关注对象）进行查询
    if show_followed:  # 如果为真，查询当数据库中前用户的followed_posts：使用最近添加的User.followed_posts 属性
        query = current_user.followed_posts  # current_user本身就是用户对象，可以直接调用User的方法转化的属性
    else:  # 如果为假，直接查询所有post
        query = Post.query
    # 查询对象分页并传入模板
    pagination = query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('blog.html', form=form, posts=posts,
                           show_followed=show_followed, pagination=pagination)
    # # V2 分页显示POST (无切换选项卡)
    # pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
    #     page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
    #     error_out=False)  # 查询此页面
    # posts = pagination.items
    # return render_template('blog.html', form=form, posts=posts,
    #                        pagination=pagination)
    # # V1 单页显示所有post
    # posts = Post.query.order_by(Post.timestamp.desc()).all()
    # return render_template('blog.html', form=form, posts=posts)

    # url_for在应用的路由中默认为视图函数的名称。
    # 在蓝本中就不一样了，Flask会为蓝本中的全部端点加上一个命名空间
    # 这样就可以在不同的蓝本中使用相同的端点名定义视图函数，而不产生冲突
    # 命名空间是蓝本的名称（Blueprint构造函数的第一个参数），而且它与端点名之间以一个点号分隔。
    # 因此，视图函数index()注册的端点名是main.index，其URL使用url_for('main.index')获取
    # url_for()函数还支持一种简写的端点形式，在蓝本中可以省略蓝本名
    # url_for('.index')。在这种写法中，使用当前请求的蓝本名补足端点名。
    # 这意味着，同一蓝本中的重定向可以使用简写形式，但跨蓝本的重定向必须使用带有蓝本名的完全限定端点名


@main.route('/user/<name>')
def user(name):
    """
    用户资料页面路由：用户信息 用户博客文章
    first_or_404 Flask-SQLAlchemy提供的简要方法：存在则返回第一个，不存在报404

    同以下语句：
    user = User.query.filter_by(name=name).first()
    if user is None:
        return render_template(‘404.html’)
    return render_template('user.html', user=user)
    """
    user = User.query.filter_by(name=name).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('user.html', user=user, posts=posts,
                           pagination=pagination)


@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """用户编辑资料路由"""
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user._get_current_object())
        db.session.commit()
        flash('个人资料已更新 Your profile has been updated.')
        return redirect(url_for('.user', name=current_user.name))
    form.username.data = current_user.username
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)


@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required  # 管理员权限检查
def edit_profile_admin(id):
    """管理员编辑资料路由"""
    user = User.query.get_or_404(id)  # 查找用户信息
    form = EditProfileAdminForm(user=user)  # 导入用户资料
    if form.validate_on_submit():
        user.workid = form.workid.data
        user.name = form.name.data
        user.email = form.email.data
        user.confirmed = form.confirmed.data
        # 外键特殊写法注意：子表.反向引用名称 = 主表.query.get(form.role.data) 为什么这么写
        user.role = Role.query.get(form.role.data)  # TODO 外键语法注意：通过表单中的role.id查找role对象，存入子表反向引用
        user.username = form.username.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        db.session.commit()
        flash('[Admin] 用户资料已更新 The profile has been updated.')
        return redirect(url_for('.user', name=user.name))
    form.workid.data = user.workid
    form.email.data = user.email
    form.name.data = user.name
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id  # 角色权限，注意此处提供权限id而非权限名称
    form.username.data = user.username
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)


@main.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
    """
    博客文章页面
        为文章提供单独页面/固定链接:
        博客文章的URL使用插入数据库时分配的唯一id字段构建
    """
    # 检索博客文章
    post = Post.query.get_or_404(id)
    # 实例化评论表单
    form = CommentForm()
    # 提交评论处理：获取评论信息-提交-更新数据库-重定向/刷新页面（定位至最后一页以显示评论）
    if form.validate_on_submit():
        comment = Comment(body=form.body.data,
                          post=post,
                          author=current_user._get_current_object())  # 通过上下文获取评论用户
        db.session.add(comment)
        db.session.commit()
        flash('评论已发布 Your comment has been published.')
        return redirect(url_for('.post', id=post.id, page=-1))
    # 评论列表分页：获取希望展示的页数-构造分页对象
    page = request.args.get('page', 1, type=int)
    if page == -1:
        page = (post.comments.count() - 1) // \
               current_app.config['FLASKY_COMMENTS_PER_PAGE'] + 1
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
        page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('post.html', posts=[post], form=form,
                           comments=comments, pagination=pagination)


@main.route('/workhour', methods=['GET', 'POST'])
def workhour():
    """
    【+】工时填写提交页面
    workhour(name):
    """
    form = WorkHourForm()
    form2 = WorkHourSubmitForm()

    # 保存工时
    if current_user.can(Permission.WRITE) and form.submit.data and form.validate_on_submit():  # 检查用户权限和提交动作
        # V1:检查数据库中是否存在重复项目工时，重复则提醒，不重复则写入数据库
        # V2:update数据库，存在则提醒已更新，
        # print(current_user)
        # 注意：需要在构造工时前check，否则能查到
        check = WorkHour.query.filter_by(project_id=form.project.data, worker_id=current_user.id).first()

        # TODO 外键语法注意：通过表单中的role.id查找role对象，存入子表反向引用
        workhour = WorkHour(project=Project.query.get(form.project.data),  # TODO 特殊用法注意 通过表单中的ID查询到对象赋值给属性
                            work=form.work.data,
                            hour=form.hour.data,
                            worker=current_user._get_current_object(),  # 获取当前用户，赋值给work_id的反向引用？
                            state='保存',
                            )
        if check:
            db.session.delete(check)
            db.session.add(workhour)
            db.session.commit()
            # flash('请勿重复填写项目工时')
            flash('工时已更新')
        else:
            db.session.add(workhour)
            db.session.commit()
            flash('工时已保存')
        return redirect(url_for('.workhour'))  # 有参需要传参
        # return redirect(url_for('.workhour', name=current_user.name))  # 有参需要传参

    # 提交工时
    if current_user.can(Permission.WRITE) and form2.submit1.data and form2.validate_on_submit():  # 检查用户权限和提交动作
        # 检查数据库中所有工时之和是否等于1
        check = db.session.query(func.sum(WorkHour.hour)).filter(WorkHour.worker_id == current_user.id).scalar()
        # print(check)

        # # TODO:数据库查询优化： 一次查询，多次计算取值
        # query = WorkHour.query.filter_by(worker_id=current_user.id).all()
        # print(query)
        # query.state = '测试'
        # print(query)
        # # check = query(func.sum(WorkHour.hour)).scalar()
        # # print(check)
        # # check = WorkHour.query.filter_by(project_id=form.project.data).first()
        # check = 0.5

        if check == 1.00:
            # 修改状态为提交
            db.session.query(WorkHour).filter(WorkHour.worker_id == current_user.id).update({"state": "已提交待审批"})
            db.session.commit()  # 提交
            flash('工时已提交，进入审批环节')
        else:
            flash('所有项目工时之和必须为1')  # todo:flash 格式参数 category="xxx"无效： message error info warning

    # 获取当前用户的工时记录
    user = current_user.id  # 获取当前用户ID / RECORD:获取当前用户对象current_user._get_current_object() ==》 <User 'simon'>
    workhours = WorkHour.query.filter_by(worker_id=user).order_by(WorkHour.submit_time.desc()).all()  # 当前用户所有工时记录
    totalhour = sum([i.hour for i in workhours])  # 当前用户所有工时合计
    # 用户工时状态：无工时记录或状态设为1 =》允许编辑 TODO:逻辑判断较多，思考如何简化逻辑加速性能
    workeditflag = 1 if not workhours or workhours[0].state in ['保存', '', '驳回'] else 0

    return render_template('workhour.html', form=form, form2=form2,
                           workeditflag=workeditflag, workhours=workhours, totalhour=totalhour)


@main.route('/workhour/Edit/<int:id>', methods=['GET', 'POST'])
@login_required
def workhourEdit(id):
    """【+】编辑工时的路由 TODO：优化为弹窗更改"""
    # 查找记录并校核权限
    edit_workhour = WorkHour.query.get_or_404(id)
    if current_user != edit_workhour.worker and not current_user.can(Permission.ADMIN):
        abort(403)  # 不是用户本人或管理员时报错

    form = WorkHourEditForm()
    # 保存工时
    if form.validate_on_submit():  # TODO 无需检查用户权限？ if current_user.can(Permission.WRITE)

        # print(type(form.hour.data))
        # print(form.hour.data)
        # 构造对象
        # TODO 外键语法注意：通过表单中的role.id查找role对象，存入子表反向引用
        workhour = WorkHour(project=edit_workhour.project,  # TODO 特殊用法注意 通过表单中的ID查询到对象赋值给属性
                            work=form.work.data,
                            hour=form.hour.data,
                            worker=current_user._get_current_object(),  # 获取当前用户，赋值给work_id的反向引用？
                            state='保存',
                            )
        db.session.delete(edit_workhour)  # 删除上一个记录
        db.session.add(workhour)  # 添加新记录
        db.session.commit()
        flash('工时信息已更改')
        return redirect(url_for('.workhour'))  # 有参需要传参

    # 将数据导入表单 =》注意代码块必须放在
    form.work.data = edit_workhour.work
    form.hour.data = edit_workhour.hour
    return render_template('workhourEdit.html', form=form, project=edit_workhour.project.name)  # 有参需要传参
    # return render_template('workhour.html', form=form)



@main.route('/workhour/Delete/<int:id>', methods=['GET', 'POST'])
@login_required
def workhourDelete(id):
    """【+】删除工时的路由"""
    workhour = WorkHour.query.get_or_404(id)
    if current_user != workhour.worker and \
            not current_user.can(Permission.ADMIN):
        abort(403)  # 不是用户本人或管理员时报错
    db.session.delete(workhour)
    db.session.commit()
    flash('工时已删除 The workhour has been deleted.')
    return redirect(url_for('.workhour'))


def workhourSubmit():
    pass

@main.route('/workhour/total')
@login_required
@permission_required(Permission.MODERATE)
def workhourTotal():
    """工时状态页面路由 - 工时审批跳转"""
    # 获取所有项目工时状态：项目-提交工时-批准工时-驳回工时-提交人数-批准人数-驳回人数？
    # workhourStates = []
    # 方法1 SQLAlchemy查询 =》最佳实践 TODO
    pass

    # 方法2 sql查询
    sql = 'SELECT projects.name, workhours.project_id, projects.upl_id, ' \
          'SUM(workhours.hour) AS totalhours, ' \
          'COUNT(workhours.project_id) AS totalnum, ' \
          'SUM (CASE WHEN workhours.state="批准" THEN workhours.hour ELSE 0 END) AS okhours, ' \
          'COUNT (CASE WHEN workhours.state="批准" THEN workhours.project_id ELSE NULL END) AS oknum, ' \
          'SUM (CASE WHEN workhours.state="驳回" THEN workhours.hour ELSE 0 END) AS nokhours, ' \
          'COUNT (CASE WHEN workhours.state="驳回" THEN workhours.project_id ELSE NULL END) AS noknum, ' \
          'SUM (CASE WHEN workhours.state="已提交待审批" THEN workhours.hour ELSE 0 END) AS tbdhours, ' \
          'COUNT (CASE WHEN workhours.state="已提交待审批" THEN workhours.project_id ELSE NULL END) AS tbdnum ' \
          'FROM projects LEFT JOIN workhours ' \
          'ON workhours.project_id = projects.id ' \
          'GROUP BY workhours.project_id;'  # 跨表查询 所有项目名称 左连接
    data = db.session.execute(sql)
    project_state = [dict(zip(result.keys(), result)) for result in data]
    # print(project_state)

    return render_template('workhourTotal.html', project_state=project_state)
    # todo:仅能展示全部状态，细节状态怎么展示 1 一次查询所有结果 2 分开查询，重新构造传入 3 分开查询分开传入 模板二次查找展示
    # todo:加速查询，此处需要查询三次，能否查询一次，然后筛选分别获取结果


    # # 获取当前用户的工时记录
    # user = current_user.id  # 获取当前用户ID / RECORD:获取当前用户对象current_user._get_current_object() ==》 <User 'simon'>
    # workhours = WorkHour.query.filter_by(worker_id=user).order_by(WorkHour.submit_time.desc()).all()  # 当前用户所有工时记录
    # totalhour = sum([i.hour for i in workhours])  # 当前用户所有工时合计
    # # 用户工时状态：无工时记录或状态设为1 =》允许编辑 TODO:逻辑判断较多，思考如何简化逻辑加速性能
    # workeditflag = 1 if not workhours or workhours[0].state in ['保存', '', '驳回'] else 0
    #
    # return render_template('workhourTotal.html', form=form, form2=form2,
    #                        workeditflag=workeditflag, workhours=workhours, totalhour=totalhour)


    #
    # page = request.args.get('page', 1, type=int)
    # pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
    #     page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
    #     error_out=False)
    # comments = pagination.items
    # return render_template('workhourTotal.html', comments=comments,
    #                        pagination=pagination, page=page)


@main.route('/workhour/project/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def workhourApprove(id):
    """
    工时审批页面路由
    方案1
    三个页面 所有 - 待审批 - 已审批(同意)
    每个页面展示逐个工时
    待审批及所有显示审批按钮
    方案2
    筛选按钮
    """
    # todo：最佳实践 ASQL查询

    sql = 'SELECT workhours.id, users.name, workhours.project_id, projects.upl_id, ' \
          'workhours.work, workhours.hour, workhours.submit_time, workhours.state, workhours.confirm_time ' \
          'FROM (projects INNER JOIN workhours ON projects.id = workhours.project_id)' \
          'INNER JOIN users ON workhours.worker_id = users.id ' \
          'WHERE  project_id={} '.format(id)  # 跨表查询 所有项目名称 左连接

    data = db.session.execute(sql)
    workhour_all = [dict(zip(result.keys(), result)) for result in data]
    # print(workhour_all)
    return render_template('workhourApprove.html', workhours=workhour_all)


@main.route('/workhour/ok/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def workhour_ok(id):
    """批准工时路由"""
    workhour = WorkHour.query.get_or_404(id)
    workhour.state = '批准'
    # print(workhour)
    # db.session.add(workhour)  # 只有要插入新的记录或要将现有的记录添加到会话中时才需要使用add()方法，单纯要更新现有的记录时只需要直接为属性赋新值，然后提交会话。
    db.session.commit()
    return redirect(url_for('.workhourApprove', id=workhour.project_id))


@main.route('/workhour/nok/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def workhour_nok(id):
    """拒绝工时路由"""
    workhour = WorkHour.query.get_or_404(id)
    user_id = workhour.worker_id
    db.session.query(WorkHour).filter(WorkHour.worker_id == user_id).update({"state": "驳回"})
    db.session.commit()
    return redirect(url_for('.workhourApprove', id=workhour.project_id))


@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """编辑博客文章的路由"""
    post = Post.query.get_or_404(id)
    if current_user != post.author and \
            not current_user.can(Permission.ADMIN):
        abort(403)  # 不是用户本人或管理员时报错
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        db.session.add(post)
        db.session.commit()
        flash('帖子已更新 The post has been updated.')
        return redirect(url_for('.post', id=post.id))
    form.body.data = post.body
    return render_template('edit_post.html', form=form)


@main.route('/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete(id):
    """【+】删除博客文章的路由"""
    post = Post.query.get_or_404(id)
    if current_user != post.author and \
            not current_user.can(Permission.ADMIN):
        abort(403)  # 不是用户本人或管理员时报错
    db.session.delete(post)
    db.session.commit()
    flash('帖子已删除 The post has been deleted.')
    return redirect(url_for('.blog'))


# @main.route('/delete/comment/<int:id>', methods=['GET', 'POST'])
@main.route('/delete/comment/<string:location>/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_comment(id, location):
    # def delete_comment(id):
    """【+】删除评论的路由"""
    comment = Comment.query.get_or_404(id)
    if current_user != comment.author and \
            not current_user.can(Permission.ADMIN):
        abort(403)  # 不是用户本人或管理员时报错
    db.session.delete(comment)
    db.session.commit()
    flash('评论已删除 The comment has been deleted.')

    # 删除后返回当前页面
    # print(location)  # 1st:postpage, 2nd:moderatepage
    # print(request.path)  # 1st:/delete/comment/postpage/15, 2nd:/delete/comment/moderatepage/16
    # print(request.full_path)  # 1st:/delete/comment/postpage/15?, 2nd:/delete/comment/moderatepage/16?
    if location == 'postpage':
        return redirect(url_for('.post', id=comment.post_id, page=-1))
    elif location == 'moderatepage':
        return redirect(url_for('.moderate'))
    # return redirect(url_for('.post', id=comment.post_id, page=-1))  # 删除后返回帖子页面


@main.route('/follow/<name>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(name):
    """关注路由和视图函数：添加关注关系"""
    # 加载请求的用户
    user = User.query.filter_by(name=name).first()
    # 确保用户存在且还没有关注这个用户
    if user is None:
        flash('用户不存在 Invalid user.')
        return redirect(url_for('.blog'))
    if current_user.is_following(user):
        flash('已关注此用户 You are already following this user.')
        return redirect(url_for('.user', name=name))
    # 添加关注关系
    current_user.follow(user)
    db.session.commit()
    flash('你关注了此用户 You are now following %s.' % name)
    # 刷新视图
    return redirect(url_for('.user', name=name))


@main.route('/unfollow/<name>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(name):
    """取消关注关系"""
    user = User.query.filter_by(name=name).first()
    if user is None:
        flash('用户不存在 Invalid user.')
        return redirect(url_for('.blog'))
    if not current_user.is_following(user):
        flash('已关注此用户 You are not following this user.')
        return redirect(url_for('.user', name=name))
    current_user.unfollow(user)
    db.session.commit()
    flash('你取消了对此用户的关注 You are not following %s anymore.' % name)
    return redirect(url_for('.user', name=name))


@main.route('/followers/<name>')
def followers(name):
    """关注者路由及视图函数：查看关注者清单"""
    # 加载并验证请求的用户
    user = User.query.filter_by(name=name).first()
    if user is None:
        flash('用户不存在 Invalid user.')
        return redirect(url_for('.blog'))
    # 分页显示该用户的关注者/followers
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(
        page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    # 转换为新列表以便渲染
    follows = [{'user': item.follower, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="关注我 Followers of",
                           endpoint='.followers', pagination=pagination,
                           follows=follows)


@main.route('/followed_by/<name>')
def followed_by(name):
    """被关注者路由及视图函数：查看被关注者清单 ==> 和关注者路由区别是用户列表从user.followed获取"""
    # 加载并验证请求的用户
    user = User.query.filter_by(name=name).first()
    if user is None:
        flash('用户不存在 Invalid user.')
        return redirect(url_for('.blog'))
    # 分页显示该用户的关注者/followers
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(
        page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    # 转换为新列表以便渲染
    follows = [{'user': item.followed, 'timestamp': item.timestamp}  # todo:followed_by？
               for item in pagination.items]
    return render_template('followers.html', user=user, title="我关注 Followed by",
                           endpoint='.followed_by', pagination=pagination,
                           follows=follows)  # todo:followed_by？


@main.route('/all')
@login_required
def show_all():
    """更改查询对象为查询所有文章 ==> 将cookie中show_followed值设为空值 即NO"""
    resp = make_response(redirect(url_for('.blog')))
    resp.set_cookie('show_followed', '', max_age=30*24*60*60)  # 30天过期
    return resp


@main.route('/followed')
@login_required
def show_followed():
    """更改查询对象为查询所有文章 ==> 将cookie中show_followed值设为1 即YES"""
    resp = make_response(redirect(url_for('.blog')))
    resp.set_cookie('show_followed', '1', max_age=30*24*60*60)  # 30天过期
    return resp


@main.route('/moderate')
@login_required
@permission_required(Permission.MODERATE)
def moderate():
    """评论管理页面路由"""
    page = request.args.get('page', 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('moderate.html', comments=comments,
                           pagination=pagination, page=page)


@main.route('/moderate/enable/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def moderate_enable(id):
    """评论启用路由"""
    # 加载评论对象
    comment = Comment.query.get_or_404(id)
    # 设置评论显示状态关键字
    comment.disabled = False
    # 更新数据库
    db.session.add(comment)
    db.session.commit()
    # 重定向/渲染
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)))


@main.route('/moderate/disable/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def moderate_disable(id):
    """评论禁用路由"""
    # 加载评论对象
    comment = Comment.query.get_or_404(id)
    # 设置评论显示状态关键字
    comment.disabled = True
    # 更新数据库
    db.session.add(comment)
    db.session.commit()
    # 重定向/渲染
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)))
