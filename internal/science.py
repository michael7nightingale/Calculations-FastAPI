import os
import sys
sys.path.append(os.getcwd())

from fastapi import APIRouter, Depends, Form, Path
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import FileResponse

from formulas import contextBuilder, plots
from internal.users import get_current_user, permission
from package.schema import RequestSchema, ScienceEnum
from package import database
from configuration.logger import logger


science_router = APIRouter(
    prefix='/science'
)
STATIC_DIR = "/public/static/"       # appends to BASE_DIR
PLOTS_DIR = "/plots/"

session = database.session()
FormulaDb = database.FormulaDb(session)
CategoryDb = database.CategoryDb(session)
ScienceDb = database.ScienceDb(session)

templates = Jinja2Templates(directory=os.getcwd() + '/public/templates/science/')


@science_router.on_event("startup")
async def create_formulas():
    """Перед запуском сервера формируется кэш-словарь формул и категорий из БД."""
    await FormulaDb.update_data()
    logger.info("Updated formulas database info!")


# ================================= PLOTS ================================ #

async def plotsView(request: Request,
                    science_slug: str,
                    *_, **__):
    context = {"request": request,
               "current_science": science_slug}
    user = await get_current_user(request)
    if user is not None:
        plot_path = STATIC_DIR + PLOTS_DIR + f'/{user.id}.png'
        if os.path.exists(os.getcwd() + plot_path):
            context.update(image_url=plot_path)
    return templates.TemplateResponse(f"plots.html", context=context)


# @permission(permissions=())
async def plotsViewPost(request, science_slug, **_):
    """
    Создание графика функции. Отображание только для авторизованных пользователей.
    SQL: _.
    """
    data = await request.form()
    context = dict(request=request, current_science=science_slug)
    message = ""
    user = await get_current_user(request)
    if user is not None:
        functions_list = [data[f"function{i}"] for i in range(1, 5) if data[f"function{i}"]]
        x_lim = data['xmin'], data['xmax']
        if all(x_lim) and functions_list:
            y_lim = data['ymin'], data['ymax']
            y_lim = y_lim if all(y_lim) else None
            plot = plots.Plot(functions_list, x_lim, y_lim)
            plot_path = os.getcwd() + STATIC_DIR + PLOTS_DIR + f"{user.id}.png"
            plot.save_plot(plot_path)
            context.update(image_url=plot_path.replace(os.getcwd(), ''))
        else:
            message = "Неполные данные."
    else:
        message = "Авторизуйтесь, чтобы увидеть график"
    context.update(message=message)
    return templates.TemplateResponse(f"plots.html", context=context)


@science_router.post('/download_plot')
@permission(permissions=())
async def download_plot(request: Request, user=None):
    """Скачать график (только для авторизованных пользователей)."""
    data = await request.form()
    filename, filesurname = data['filename'], data['filesurname']
    return FileResponse(path=os.getcwd() + filename, filename=filesurname + '.png')


SPECIAL_CATEGORIES_GET = {
    "plots": plotsView,
    "equations": 'equations.html'
}

SPECIAL_CATEGORIES_POST = {
    "plots": plotsViewPost,
    "equations": 'equations.html'
}


# =================================== DEPENDENCIES ================================== #

async def science_basic(
        request: Request,
        science_slug: ScienceEnum = Path(),
    ):
    """Зависимость для науки."""
    return {
        "science_slug": science_slug.value,
        "request": request
    }
        

async def formula_basic(
        science_slug: ScienceEnum = Path(),
        formula_slug: str = Path()
    ):
    """Зависимость для формулы."""
    formula = await FormulaDb.get_formula(formula_slug)
    category = await CategoryDb.get_category(formula.category_id)
    if category.super_category == science_slug:
        return {
            "science_slug": science_slug.value,
            "category": category,
            "formula": formula,
                }
    raise HTTPException(status_code=404,
                        detail="Not matching data!")


# ============================== SCIENCE ============================ #

@science_router.get('/{science_slug}')
async def science_main( 
        request: Request, 
        science_slug: str = Path(),
    ):
    """
    Главная страница науки. Для всех пользователей.
    SQL: science; categories on science.
    """
    science = await ScienceDb.get_science(science_slug)
    categories = await CategoryDb.get_all_categories(science=science_slug)
    context = {
        "science": science, 
        "categories": categories,
        "request": request
    }
    return templates.TemplateResponse("main.html", context=context)


@science_router.get('/{science_slug}/category/{cat_slug}/')
async def science_category(
        params: dict = Depends(science_basic),
        cat_slug: str = Path()
    ):
    """
    Category page. For all sciences. Available for everyone.
    SQL: - category; formulas on category;
    """
    context = params.copy()
    
    if cat_slug in SPECIAL_CATEGORIES_GET:
        return await SPECIAL_CATEGORIES_GET[cat_slug](**params)
    else:
        formulas_objects = await FormulaDb.get_formulas_by_cat(cat_slug)
        category = await CategoryDb.get_category(cat_slug)
        formulas = [i.as_dict() for i in formulas_objects]
        context.update({'formulas': formulas, "title": category.category_name})
        return templates.TemplateResponse("category.html", context=context)


@science_router.post('/{science_slug}/category/{cat_slug}/')
async def science_category_post(
        params: dict = Depends(science_basic),
        cat_slug: str = Path()
    ):
    """
    Маршрут необходим только для одностраничных специальных категорий. Для всех пользователей.
    SQL: _.
    """
    context = {"request": params['request'],
               "current_science": params['science_slug']}
    if cat_slug in SPECIAL_CATEGORIES_POST:
        return await SPECIAL_CATEGORIES_POST[cat_slug](**params)
    else:
       raise HTTPException(status_code=404)


@science_router.get('/{science_slug}/formula/{formula_slug}/')
async def science_formula(
        request: Request,
        context: dict = Depends(formula_basic)
    ):
    """
     Форма c формулой при первом открытии или обновлении страницы. Для всех пользователей.
     SQL: category; formula on category.
     """
    user = await get_current_user(request)
    requestSchema = RequestSchema(
        url=request.url.path,
        method=request.method,
    )
    built_context = await contextBuilder.build_template(
        request=requestSchema,
        science_slug=context['science_slug'], 
        formula_slug=context['formula'].slug,
    )
    context.update(built_context, request=request)
    return templates.TemplateResponse("template_formula.html", context=context)


@science_router.post('/{science_slug}/formula/{formula_slug}/')
async def science_formula_post(
        request: Request,
        context: dict = Depends(formula_basic),
        nums_comma: int = Form(),
        find_mark: str = Form()):
    """
     Форма в формулой после отправки формы впервые. Для всех пользователей.
     SQL: category; formula on category.
     """
    user = await get_current_user(request)
    data = await request.form()
    requestSchema = RequestSchema(
        url=request.url.path,
        method=request.method,
        find_mark=find_mark,
        user_id=user.id if user is not None else None,
        data=data,
        nums_comma=nums_comma
    )
    built_context = await contextBuilder.build_template(
        request=requestSchema,
        science_slug=context['science_slug'], 
        formula_slug=context['formula'].slug,
    )
    context.update(built_context, request=request)
    return templates.TemplateResponse("template_formula.html", context=context)

