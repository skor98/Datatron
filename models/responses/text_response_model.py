import json
import logging
from core.answer_object import CoreAnswer
from core.cube_docs_processing import CubeAnswer, CubeProcessor
from core.minfin_docs_processing import MinfinAnswer

from models.responses.link_model import LinkModel
from models.responses.question_model import QuestionModel

class TextResponseModel:
# модель ответа клиенту

    def __init__(self):
        self.status = False
        self.question = None
        self.full_answer = 'Ответ не найден'
        self.short_answer = 'Ответ не найден'
        self.document_links = None
        self.image_links = None
        self.http_ref_links = None
        self.associated_quesions = None

    def toJSON(self):
        return json.dumps(self, default=lambda obj: obj.__dict__, indent=4, ensure_ascii=False)

    def toJSON_API(self):
        keys_to_return = (
            'status',
            'question',
            'full_answer',
            'short_answer',
            'associated_quesions',
        )

        # если есть списки документов, изображений или ссылок,
        # добавим их в конечный ответ
        if self.document_links is not None:
            keys_to_return = keys_to_return + ('document_links',)

        if self.image_links is not None:
            keys_to_return = keys_to_return + ('image_links',)

        if self.http_ref_links is not None:
                keys_to_return = keys_to_return + ('http_ref_links',)

        result_dict = {key: getattr(self, key, None) for key in keys_to_return}

        return json.dumps(
            result_dict,
            default=lambda obj: getattr(obj, 'to_reduced_api_object', lambda: None)(),
            ensure_ascii=False,
        ).encode("utf-8")

    @staticmethod
    def from_answer(response: CoreAnswer):
        # формирование ответа для клиента
        text_response = TextResponseModel()
        text_response.status = response.status

        text_response.associated_quesions = TextResponseModel.get_associated_quesions(
            response.more_answers_order,
            response.more_cube_answers,
            response.more_minfin_answers
        )

        if response.answer is None:
            return text_response

        if isinstance(response.answer, CubeAnswer):
            logging.info('ответ по кубу')
            TextResponseModel.from_cube_answer(text_response, response)

        if isinstance(response.answer, MinfinAnswer):
            logging.info('ответ по минфину')
            TextResponseModel.from_minfin_answer(text_response, response)

        return text_response

    @staticmethod
    def from_cube_answer(text_response, response: CubeAnswer):
        # формирование ответа для клиента по ответу по кубу
        pretty_feedback = response.answer.feedback.get('pretty_feedback')
        formatted_response = response.answer.formatted_response

        if pretty_feedback is not None:
            answer = "Datatron понял ваш запрос как '{}'".format(pretty_feedback)

        if formatted_response is not None:
            answer = "{}\nОтвет: {}".format(answer, formatted_response)

        time_data_relevance = CubeProcessor.get_time_data_relevance(response.answer)
        if time_data_relevance is not None:
            answer = "{}{}".format(answer, time_data_relevance)

        text_response.short_answer = answer
        text_response.full_answer = answer

        return text_response

    @staticmethod
    def from_minfin_answer(text_response, response: CubeAnswer):
        # формирование ответа для клиента по ответу по минфину
        if response.answer is not None:
            text_response.question = response.answer.question
            text_response.full_answer = response.answer.full_answer
            text_response.short_answer = response.answer.short_answer
            text_response.document_links = TextResponseModel.get_document_links(response)
            text_response.image_links = TextResponseModel.get_image_links(response)
            text_response.http_ref_links = TextResponseModel.get_gttp_ref_links(response)

        return text_response

    @staticmethod
    def get_associated_quesions(answer_order: str, cube_answer_list: list, minfin_answer_list: list):
        # формирование блока associated_quesions
        associated_quesions_items = []
        minfin_answer_counter = 0
        cube_answer_counter = 0
        for mask in list(answer_order):
            if mask == '1':
                question = minfin_answer_list[minfin_answer_counter].question
                minfin_answer_counter += 1
            else:
                question = cube_answer_list[cube_answer_counter].feedback.get('pretty_feedback')
                cube_answer_counter += 1

            associated_quesions_items.append(QuestionModel(question))

            for item in associated_quesions_items:
                logging.info("{}".format(item.question))

        return associated_quesions_items

    @staticmethod
    def get_document_links(response: CoreAnswer):
        # формирование блока списка документов
        if response.answer.document is not None:
            document_links = []
            document_link = LinkModel('document', response.answer.document_caption[0], response.answer.document[0])
            document_links.append(document_link)
        else:
            return None

    @staticmethod
    def get_image_links(response: CoreAnswer):
        # формирование блока списка изображений
        if response.answer.picture is not None:
            image_links = []
            image_link = LinkModel('image', response.answer.picture_caption[0], response.answer.picture[0])
            image_links.append(image_link)
            return image_links
        else:
            return None

    @staticmethod
    def get_gttp_ref_links(response: CoreAnswer):
        # формирование блока списка http ссылок
        if response.answer.link is not None:
            http_ref_links = []
            http_ref_link = LinkModel('http_ref', response.answer.link_name[0], response.answer.link[0])
            http_ref_links.append(http_ref_link)
            return http_ref_links
        else:
            return None
