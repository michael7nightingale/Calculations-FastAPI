import os
from fastapi import APIRouter, Depends, Form, Path
from functools import lru_cache, wraps
from typing import Callable
from datetime import timedelta
from fastapi_login import LoginManager
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import RedirectResponse, FileResponse
from starlette.templating import Jinja2Templates

from package.exceptions import NotAuthenticatedException
from package import database
from package import schema
from configuration.logger import logger
from package import tables

users_router = APIRouter(
    prefix='/accounts'
)
session = database.session()
UserDb = database.UserDb(session)
HistoryDb = database.HistoryDb(session)
templates = Jinja2Templates(directory=os.getcwd() + '/public/templates/users/')

HISTORY_DIR = '/public/static/data/'

loginManager = LoginManager(
    'secret',
    token_url='/accounts/login',
    use_cookie=True,
    custom_exception=NotAuthenticatedException,
    default_expiry=timedelta(hours=12),

)

GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")

GITHUB_LOGIN_URL = f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}"


@loginManager.user_loader()
async def get_user_from_db(username: str):
    return await UserDb.get_user(username)


async def get_current_user(request: Request) -> database.User:
    token = request.cookies.get('access-token')
    if token is not None:
        try:
            user_dict = loginManager._get_payload(token)
            user = await get_user_from_db(username=user_dict['username'])
            logger.info(f"Got user with id: {user.id}!")
            # user = await UsersDb.get_user(user_dict['username'])
        except NotAuthenticatedException:
            user = None
        except:
            raise HTTPException(status_code=403, detail="You are not registered")
        return user


async def is_superuser(request: Request):
    user = await get_current_user(request)
    if user:
        return user if user.is_superuser else None


async def is_stuff(request: Request):
    user = await get_current_user(request)
    if user:
        return user if user.is_stuff else None


async def is_accessed(request: Request):
    return "access-token" in request.cookies


@lru_cache(maxsize=64)
def permission(permissions: tuple):
    __permissions = ('superuser', 'stuff', 'token', 'user')

    def decorator(func: Callable):
        @wraps(func)
        async def inner(request: Request, user=None, **kwargs):
            nonlocal __permissions
            assert all(perm in __permissions for perm in permissions), f"There is not such permissions: {permissions}"
            if "token" in permissions:
                assert len(permissions) == 1, f"Ridiculous permissions: {permissions}"

            if any(i in permissions for i in __permissions[:2]):       # if permissions are set
                for i in set(permissions):
                    if user is None:    # while there is no matching permission
                        if i == 'stuff':
                            user = await is_stuff(request)
                        elif i == 'superuser':
                            user = await is_superuser(request)

                if user is None:    # no matching user permission
                    raise HTTPException(status_code=403, detail='Permission denied')

            elif "user" in permissions:   # if just to check user in db
                user = await get_current_user(request)
                if user is None:
                    return login_redirect()

            elif "token" in permissions:     # if just to check token
                user = await is_accessed(request)
                if user:
                    user = None
                else:
                    return login_redirect()



            res = await func(request=request, user=user, **kwargs)

            return res
        return inner
    return decorator


async def user_login_parameters(
        request: Request, 
        #username: str = Form(default=""),
        #password: str = Form(default=""), 
    ) -> schema.LoginUser:
    form_data = await request.form()
    return schema.LoginUser(**form_data)


async def user_register_parameters(
        request: Request,
        #parameters: dict = Depends(user_login_parameters),
        #email: str = Form()
    ) -> schema.RegisterUser:
    form_data = await request.form()
    return schema.RegisterUser(**form_data)


# =================================== OAUTH ============================ #

@users_router.get('/github-login/')
async def github_login(request: Request):
    """Login with GitHub."""
    return RedirectResponse(GITHUB_LOGIN_URL, status_code=303)


@users_router.get("/github-got")
async def github_get(request: Request, code: str):
    """Add access token from GitHub to cookies"""
    response = RedirectResponse(url='/', status_code=303)
    loginManager.set_cookie(response, token=code)
    request.cookies['access-token'] = code

    return response


# =================================== USERS ============================ #

@users_router.get("/login")
async def login(request: Request):
    return templates.TemplateResponse('login.html', context={"request": request,})


@users_router.post('/login')
async def login_post(
        request: Request,
        user_schema: schema.LoginUser = Depends(user_login_parameters), 

    ):
    user: database.User = await UserDb.login_user(user_schema)
    if user is not None:
        user_access_token = loginManager.create_access_token(
            data=user.as_dict(),
            expires=timedelta(hours=12)
        )
        response = RedirectResponse(url="/", status_code=303)
        loginManager.set_cookie(response, user_access_token)
        request.state.user = user
        request.cookies['access-token'] = user_access_token
        return response
    return login_redirect()


def login_redirect():
    """Just a function to avoid writing redirect every time"""
    return RedirectResponse(users_router.url_path_for("login"), status_code=303)


@users_router.get("/register")
async def register(
        request: Request,

    ):
    return templates.TemplateResponse('register.html', context={"request": request,})


@users_router.post("/register")
async def register_post(
        request: Request,
        user_schema: schema.RegisterUser = Depends(user_register_parameters)
    ):
    user = await UserDb.create_user(user_schema)
    return login_redirect()


@users_router.get('/logout')
async def logout(request: Request):
    """Logout user"""
    response = RedirectResponse(url='/', status_code=303)
    response.delete_cookie(key='access-token')
    return response


@users_router.get('/{username}/')
@permission(permissions=("user", ))
async def cabinet(
        request: Request,
        user=None,
        username: str = Path()
    ):
    if user.username == username:
        context = {
            'request': request,
            "user": user
        }
        return templates.TemplateResponse("personal_cabinet.html", context=context)
    else:
        raise HTTPException(status_code=403, detail='Unauthorized.')


@users_router.get('/history')
@permission(permissions=("user", ))
async def history(request: Request,
                  user=None,):
    delete_history_csv(user.id)
    history_list = await HistoryDb.get_history(user.id)
    context = {
        "title": "История вычислений",
        "history": history_list,
        "user": user,
        'request': request
    }
    return templates.TemplateResponse("history.html", context=context)


@users_router.post('/download_history')
@permission(permissions=("user", ))
async def history_download(
        request: Request,
        user=None,
        filename: str = Form()
    ):
    history_list = await HistoryDb.get_history(user.id)
    filepath = os.getcwd() + HISTORY_DIR + f'{user.id}.csv'
    table = tables.CsvTableManager(filepath)
    history_list = [i.as_dict() for i in history_list]

    if history_list:
        table.init_data(history_list[0].keys())
        for line in history_list:
            table.add_line(line.values())
        table.save_data(filepath)
        return FileResponse(path=filepath, filename=f"{filename}.csv")
    else:
        return RedirectResponse(url=users_router.url_path_for('history'), status_code=303)


def delete_history_csv(user_id: int):
    """Удаление файла .csv с историей вычислений"""
    path = os.getcwd() + HISTORY_DIR + f'{user_id}.csv'
    if os.path.exists(path):
        os.remove(path)
    else:
        return None


@users_router.post('/delete_history')
@permission(permissions=("user", ))
async def history_delete(
        request: Request,
        user=None
    ):
    await HistoryDb.delete_history(user.id)
    return RedirectResponse(url=users_router.url_path_for('history'), status_code=303)
