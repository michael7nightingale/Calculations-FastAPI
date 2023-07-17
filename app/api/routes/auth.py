from fastapi import APIRouter, Form, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi_authtools.models import UserModel

from app.api.dependencies import get_repository, get_user_register_data
from app.models.schemas import UserRegister
from app.db.repositories import UserRepository
from app.core.config import get_app_settings


auth_router = APIRouter(
    prefix='/auth'
)
templates = Jinja2Templates('app/public/templates/auth/')


@auth_router.get('/github-login/')
async def github_login(request: Request):
    """Login with GitHub."""
    return RedirectResponse(get_app_settings().github_login_url, status_code=303)


@auth_router.get("/github-got")
async def github_get(request: Request, code: str):
    """Add access token from GitHub to cookies"""
    response = RedirectResponse(url='/', status_code=303)
    request.cookies['access-token'] = code
    return response


@auth_router.get("/login")
async def login_get(request: Request):
    """Login GET view."""
    return templates.TemplateResponse('login.html', context={"request": request})


@auth_router.post('/login')
async def login_post(
        request: Request,
        username: str = Form(),
        password: str = Form(),
        user_repo: UserRepository = Depends(get_repository(UserRepository))
):
    """Login POST view."""
    user = await user_repo.login(username, password)
    if user is None:
        return login_redirect()
    response = RedirectResponse("/", status_code=303)
    user_model = UserModel(**user.as_dict())
    request.app.state.auth_manager.login(response, user_model)
    return response


def login_redirect():
    """Just a function to avoid writing redirect every time"""
    return RedirectResponse(auth_router.url_path_for("login_get"), status_code=303)


@auth_router.get("/register")
async def register_get(request: Request):
    """Registration GET view."""
    return templates.TemplateResponse('register.html', context={"request": request})


@auth_router.post("/register")
async def register_post(
        request: Request,
        user_data: UserRegister = Depends(get_user_register_data),
        user_repo: UserRepository = Depends(get_repository(UserRepository))
):
    """Registration POST view."""
    new_user = await user_repo.register(user_data)
    if new_user is None:
        return RedirectResponse(auth_router.url_path_for("register_get"), status_code=303)
    return login_redirect()


@auth_router.get('/logout')
async def logout(request: Request):
    """Logout user view."""
    response = RedirectResponse(url='/', status_code=303)
    request.app.state.auth_manager.logout(response)
    return response
