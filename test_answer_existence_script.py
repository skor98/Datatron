import requests


def send_request_to_server(mdx_query: str, cube: str):
    """
    Отправка запроса к серверу Кристы для получения
    ответа по MDX-запросу
    """

    # Подготовка POST-данных и запрос к серверу
    data_to_post = {'dataMartCode': cube, 'mdxQuery': mdx_query}
    api_response = requests.post(
        'http://conf.prod.fm.epbs.ru/mdxexpert/CellsetByMdx',
        data_to_post
    )

    # TODO: костыль на тот случай пока сервер отвечает через раз
    if api_response.status_code != 200:
        api_response = requests.post(
            'http://conf.prod.fm.epbs.ru/mdxexpert/CellsetByMdx',
            data_to_post
        )

    return api_response

response = send_request_to_server(
    'SELECT {[MEASURES].[VALUE]} ON COLUMNS FROM [EXYR03.DB] WHERE ([RZPR].[14-848302],[BGLEVELS].[09-12],[MARKS].[03-4],[YEARS].[2015],[TERRITORIES].[08-67724])',
    'EXYR03'
).json()
a = response["cells"][0][0]["value"]
print(float(a) if a else a)