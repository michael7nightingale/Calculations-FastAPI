from tortoise import fields
from tortoise.exceptions import IntegrityError

from src.base.models import TortoiseModel
from src.services.hash import hash_password, verify_password


class User(TortoiseModel):
    username = fields.CharField(max_length=100, unique=True)
    password = fields.CharField(max_length=255, null=True)
    email = fields.CharField(max_length=100, unique=True)
    first_name = fields.CharField(max_length=100, null=True)
    last_name = fields.CharField(max_length=100, null=True)
    is_superuser = fields.BooleanField(default=False)
    is_admin = fields.BooleanField(default=False)
    is_active = fields.BooleanField(default=False)
    time_registered = fields.DatetimeField(auto_now=True)
    last_login = fields.DatetimeField(auto_now_add=True, null=True)

    @classmethod
    async def login(cls, password: str, username: str | None = None, email: str | None = None):
        if username:
            user = await cls.get_or_none(username=username)
        elif email:
            user = await cls.get_or_none(email=email)
        else:
            return None
        if user is not None:
            if verify_password(password, user.password) and user.is_active:
                return user

    @classmethod
    async def register(cls, **kwargs):
        kwargs.update(password=hash_password(kwargs['password']))
        try:
            user = await cls.create(**kwargs)
        except IntegrityError:
            return
        return user

    @classmethod
    async def activate(cls, id_: str):
        user = await cls.get_or_none(id=id_)
        await user.update_from_dict({"is_active": True})
        await user.save()

    def __str__(self):
        return self.username

    def full_name(self) -> str:
        if self.first_name or self.last_name:
            return f"{self.first_name or ''} {self.last_name or ''}"
        return self.username
