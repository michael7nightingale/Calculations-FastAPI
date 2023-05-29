# FastAPI версия веб-приложения для физико-математических вычислений.

Вариант разветвленной архитектуры, настроен на удобство чтения и редактирования.



## Установка зависимостей

Python >= 3.10
> __!!!__ requirements.txt с зависимостями находится в корневой директории проекта

```
 pip install -r requirements.txt
 ```


## Запуск

Запуск приложения без переменных окружения бессмысленнен. В проетке используется PosgreSQL 15 и GitHub Oauth, так что для 
запуска проекта необходимо разобраться сначала с ними.


> __!!!__ main.py для запуска находится в корневой директории проекта


```commandline
python main.py dumpdata
```

```commandline
python main.py runserver
```
