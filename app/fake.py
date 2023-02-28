"""创建虚拟博客文章数据"""
from random import randint
from sqlalchemy.exc import IntegrityError
from faker import Faker
from . import db
from .models import User, Post


def users(count=100):
    """创建虚拟用户"""
    # fake = Faker()
    fake = Faker(locale='zh_CN')  # 中文信息
    i = 0
    while i < count:
        u = User(email=fake.email(),
                 username=fake.user_name(),
                 password='password',
                 confirmed=True,
                 name=fake.name(),
                 location=fake.city(),
                 about_me=fake.text(),
                 member_since=fake.past_date())
        db.session.add(u)
        try:
            db.session.commit()
            i += 1
        except IntegrityError:
            db.session.rollback()  # 若用户重复则回滚，直至满足条件


def posts(count=100):
    """创建虚拟博客文章"""
    fake = Faker()
    user_count = User.query.count()
    for i in range(count):
        u = User.query.offset(randint(0, user_count - 1)).first()
        p = Post(body=fake.text(),
                 timestamp=fake.past_date(),
                 author_id=u.id)  # author=u?
        db.session.add(p)
    db.session.commit()
