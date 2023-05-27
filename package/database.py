import asyncio
import datetime
import os
from dotenv import load_dotenv
# from functools import singledispatchmethod
import passlib
from fastapi import HTTPException
from starlette.requests import Request
from sqlalchemy import String, Integer, Column, Text, Boolean, select, create_engine, delete
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from passlib.hash import django_pbkdf2_sha256

from package import schema


load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

ECHO = False
FUTURE = True
EXPIRE_ON_COMMIT = False

DATABASE_USER = os.getenv('DATABASE_USER')
DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD')
DATABASE_HOST = os.getenv('DATABASE_HOST')
DATABASE_NAME = os.getenv('DATABASE_NAME')


engine = create_async_engine(
    f"postgresql+asyncpg://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}/{DATABASE_NAME}",
    echo=ECHO,
    future=FUTURE
)
session = sessionmaker(engine,
                       class_=AsyncSession,
                       expire_on_commit=EXPIRE_ON_COMMIT)
Base = declarative_base()


class TableMixin:
    def as_dict(self) -> dict:
        return {i.name: getattr(self, i.name) for i in self.__table__.columns}


class Science(Base, TableMixin):
    __tablename__ = 'sciences'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(40), unique=True)
    content = Column(Text)
    slug = Column(String(40), unique=True)


class User(Base, TableMixin):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(40), unique=True)
    email = Column(String(40), unique=True)
    hasw_psw = Column(String(100))
    last_login = Column(String(50))
    joined = Column(String(50))
    is_stuff = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)


class Category(Base, TableMixin):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String(40), unique=True)
    content = Column(Text)
    super_category = Column(String(40))
    slug = Column(String(40), unique=True)


class Formula(Base, TableMixin):
    __tablename__ = 'formulas'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(40), unique=True)
    formula = Column(String(40))
    content = Column(Text)
    category_id = Column(Integer)
    slug = Column(String(40), unique=True)


class History(Base, TableMixin):
    __tablename__ = 'history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    formula = Column(String(40))
    result = Column(String(40))
    formula_url = Column(String(50))
    date_time = Column(String(40))
    user_id = Column(Integer)

    def history_view(self) -> str:
        return f"{self.formula} | {self.result} | {self.formula_url}"


class DbInterface:
    __slots__ = ('__db_session', )
    def __init__(self, db_session: AsyncSession):
        self.__db_session = db_session

    @property
    def db_session(self):
        return self.__db_session

def nowTime() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def unfined(f):
    async def inner(*a, **k):
        try:
            return await f(*a, **k)
        except TypeError:
                return None
    return inner


class UserDb(DbInterface):
    __slots__ = ()

    async def create_user(self, user_schema: schema.RegisterUser) -> User:
        psw = user_schema.password
        hashed_pws = django_pbkdf2_sha256.hash(psw)
        user_schema.password = hashed_pws
        user = User(
            **user_schema.dict(),
            last_login=nowTime(),
            joined=nowTime()
        )
        self.db_session.add(user)
        await self.db_session.commit()
        return user

    @unfined
    async def login_user(self, user_schema: schema.LoginUser):
        res = await self.db_session.execute(select(User).where(User.username == user_schema.username))
        user = res.first()[0]
        if user:
            if django_pbkdf2_sha256.verify(user_schema.password, user.hasw_psw):
                user.last_login = nowTime()
                self.db_session.add(user)
                await self.db_session.commit()
                return user


    async def get_user(self, identifier):
        if isinstance(identifier, int):
            res = await self.db_session.execute(select(User).where(User.id == identifier))
        elif isinstance(identifier, str):
            res = await self.db_session.execute(select(User).where(User.username == identifier))
        else:
            raise HTTPException(status_code=500)
        return res.first()[0]


    async def delete_user(self, id_: int):
        User.query.get(id_).delete()
        await self.db_session.commit()

    @staticmethod
    def get_hashed_password(password: str) -> str:
        return passlib.hash.django_pbkdf2_sha256.hash(password)

    @staticmethod
    def verify_password(password: str, secret_hash: str) -> bool:
        return passlib.hash.django_pbkdf2_sha256.verify(password, secret_hash)

    async def authenticate_user(self, username: str, password: str):
        user = await self.get_user(username)
        if user is None:
            return False
        if not self.verify_password(password, user.hasw_psw):
            return False
        return user


class HistoryDb(DbInterface):
    __slots__ = ()
    async def form_history(self, data: schema.HistorySchema):
        history = History(**data.dict())
        self.db_session.add(history)
        await self.db_session.commit()
        return history

    # @singledispatchmethod
    async def get_history(self, user_id: int):
        res = await self.db_session.execute(select(History).where(History.user_id == user_id))
        history_list = [i[0] for i in res.all()]
        return history_list

    async def delete_history(self, user_id: int):
        res = await self.db_session.execute(delete(History).where(History.user_id == user_id))
        await self.db_session.commit()


class FormulaDb(DbInterface):
    __slots__ = ("__db_session", "__cat_db", "__science_db", "CATEGORIES", "FORMULAS", "SCIENCES")

    def __init__(self, db_session):
        super().__init__(db_session)
        self.__cat_db = CategoryDb(self.db_session)
        self.__science_db = ScienceDb(self.db_session)
        self.CATEGORIES = {}
        self.FORMULAS = {}
        self.SCIENCES = {}

    async def get_formulas_by_cat(self, category_name, _initial=False) -> list:
        if _initial or not self.FORMULAS:
            cat = await self.__cat_db.get_category(category_name)
            res = await self.db_session.execute(select(Formula).where(Formula.category_id == cat.id))
            return [i[0] for i in res.all()]
        else:
            return self.CATEGORIES[category_name]

    async def get_formula(self, formula_name: str) -> Formula:
        if not self.FORMULAS:
            res = await self.db_session.execute(select(Formula).where(Formula.slug == formula_name))
            formula = res.first()
            if formula is not None:
                return formula[0]
            raise HTTPException(status_code=404)
        else:
            try:
                return self.FORMULAS[formula_name]
            except KeyError:
                raise HTTPException(status_code=404)

    async def update_data(self):
        await create_db()
        for i in await self.__science_db.get_all_sciences():
            self.SCIENCES[i.slug] = await self.__cat_db.get_all_categories(i.slug)
        for science, categories in self.SCIENCES.items():
            for category in categories:
                print(category)
                self.CATEGORIES[category.slug] = await self.get_formulas_by_cat(category.slug, _initial=True)
        for category, formulas in self.CATEGORIES.items():
            for formula in formulas:
                self.FORMULAS[formula.slug] = formula
        return

    async def create_formula(self, **data):
        formula = Formula(**data)
        self.db_session.add(formula)
        await self.db_session.commit()
        return formula


class ScienceDb(DbInterface):
    __slots__ = ()
    async def get_science(self, slug: str):
        res = await self.db_session.execute(select(Science).where(Science.slug == slug))
        return res.first()[0]

    async def get_all_sciences(self):
        res = await self.db_session.execute(select(Science))
        return [i[0] for i in res.all()]


class CategoryDb(DbInterface):
    __slots__ = ()

    async def get_category(self, identifier):
        if isinstance(identifier, str):
            res = await self.db_session.execute(select(Category).where(Category.slug == identifier))
        elif isinstance(identifier, int):
            res = await self.db_session.execute(select(Category).where(Category.id == identifier))
        else:
            raise HTTPException(status_code=500)
        cat = res.first()
        if cat is not None:
            return cat[0]
        raise HTTPException(status_code=404)

    async def get_all_categories(self, science: str) -> list:
        res = await self.db_session.execute(select(Category).where(Category.super_category == science))
        return [i[0] for i in res.all()]



async def main():
    userdb = UserDb(session())
    await userdb.create_user('michael', 'suslan@mail.ru', 'password')
    await userdb.create_user('michael7', 'suslan7@mail.ru', 'password7')


async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    # asyncio.run(create_db())
    ...
