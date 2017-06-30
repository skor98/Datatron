from messenger_manager import MessengerManager
from data_retrieving import DataRetrieving
from bottle import Bottle, request, run, BaseRequest
import codecs
import uuid
import os
from random import choice
from string import ascii_lowercase, digits
from config import SETTINGS

# увеличения допустимого размера файла до 3мб для избежания 413 ошибки
BaseRequest.MEMFILE_MAX = 1024 * 3
app = Bottle()


@app.get('/')
def main():
    """Чтобы что-то выводило при GET запросе - простая проверка рабочего состояния серевера"""

    return '<center><h1>Welcome to Datatron Home API page</h1></center>'


@app.post('/text')
def post_basic():
    """POST запрос для текстовых запросов к системе"""

    # Получение полей
    request_text = request.forms.get('Request')
    source = request.forms.get('Source')
    user_id = request.forms.get('UserId')
    user_name = request.forms.get('UserName')
    request_id = request.forms.get('RequestId')

    # Исправление кодировки для кириллицы
    request_text = codecs.decode(bytes(request_text, 'iso-8859-1'), 'utf-8')

    # если все поля заполнены
    if request_text and source and user_id and user_name and request_id:
        return MessengerManager.make_request(request_text, source, user_id, user_name, request_id).toJSON()


@app.post('/test')
def post_test():
    """POST запрос для удаленного тестирования системы на сервере"""

    request_text = request.forms.get('Request')
    request_text = codecs.decode(bytes(request_text, 'iso-8859-1'), 'utf-8')

    if request_text:
        return DataRetrieving.get_data(request_text, uuid.uuid4(), formatted=False).toJSON()


@app.post('/audio')
def post_audio_file():
    """POST запрос для голосовых запросов с помощью передачи файла запроса"""

    # Получение файла
    file = request.files.get('File')

    # Определение его формата
    file_extension = file.filename.split('.')[-1]

    # Определение дериктории для сохранения файла
    save_path = r'{}\tmp'.format(os.getcwd())
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    # Генерация случайного имени файла
    new_file_name = ''.join(choice(ascii_lowercase + digits) for _ in range(10))

    # Сохранения полученного файла под новым именем в папку для хранения временных файлов
    file_path = r"{}\{}.{}".format(save_path, new_file_name, file_extension)
    file.save(file_path)

    source = request.forms.get('Source')
    user_id = request.forms.get('UserId')
    user_name = request.forms.get('UserName')
    request_id = request.forms.get('RequestId')

    # если все поля заполнены
    if file and source and user_id and user_name and request_id:
        return MessengerManager.make_voice_request(source, user_id, user_name, request_id, filename=file_path).toJSON()


@app.error(404)
def error404(error):
    """Чтобы выводилась ошибка, если файл не найден"""

    return '<center><h1>Nothing here sorry: %s</h1></center>' % error


run(app, host=SETTINGS.HOST, port=8019, debug=True)
