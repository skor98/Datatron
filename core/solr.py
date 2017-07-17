#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Взаимодействие с Apache Solr
"""

import requests
from config import SETTINGS
from model_manager import MODEL_CONFIG


class Solr:
    """
    Класс для взимодействия с поисковой системой Apache Solr
    """

    def __init__(self, core: str):
        self.core = core

    def get_data(self, user_request: str):
        return self._send_request_to_solr(user_request)

    def _send_request_to_solr(self, user_request: str):
        """Реализация запроса к Solr

        :param user_request: запрос пользователя
        :return: ответ от Apache Solr в формате JSON-строки
        """

        request = 'http://{}:8983/solr/{}/select'.format(
            SETTINGS.SOLR_HOST,
            self.core
        )

        # Просим Solr выдать solr_documents_to_return (default: 50)
        # документов в формате json, а также указать score каждого
        params = {
            'q': user_request,
            'rows': MODEL_CONFIG["solr_documents_to_return"],
            'wt': 'json',
            'fl': '*,score'
        }
        docs = requests.get(request, params=params).json()
        return docs
