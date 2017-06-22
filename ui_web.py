from messenger_manager import MessengerManager
from bottle import Bottle, request, run, BaseRequest
import codecs
import os
from random import choice
from string import ascii_lowercase, digits
from config import SETTINGS

# увеличения допустимого размера файла до 3мб для избежания 413 ошибки
BaseRequest.MEMFILE_MAX = 1024 * 3
app = Bottle()


@app.get('/')
def main():
    return '<center><h1>Welcome to Datatron Home API page</h1></center>'


@app.post('/post')
def post_basic():
    # Получение полей
    request_text = request.forms.get('Request')
    source = request.forms.get('Source')
    user_id = request.forms.get('UserId')
    user_name = request.forms.get('UserName')
    request_id = request.forms.get('RequestId')

    # Исправление кодировки
    request_text = codecs.decode(bytes(request_text, 'iso-8859-1'), 'utf-8')

    # если все поля заполнены
    if request_text and source and user_id and user_name and request_id:
        return MessengerManager.make_request(request_text, source, user_id, user_name, request_id).toJSON()


@app.post('/post')
def post_audio_file():
    # Получение полей
    file = request.files.get('File')

    save_path = r'{}\tmp'.format(os.getcwd())
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    new_file_name = ''.join(choice(ascii_lowercase + digits) for _ in range(10))
    file_extension = file.filename.split('.')[-1]
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
    return '<center><h1>Nothing here sorry: %s</h1></center>' % error


run(app, host=SETTINGS.HOST, port=8019, debug=True)
