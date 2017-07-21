#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Взаимодействие с Apache Solr
"""

import requests
import logging

from config import SETTINGS
from model_manager import MODEL_CONFIG

import logs_helper  # pylint: disable=unused-import


class Solr:
    """
    Класс для взимодействия с поисковой системой Apache Solr
    """

    @staticmethod
    def get_data(user_request: str, request_id: str, core: str):
        """Реализация запроса к Solr"""

        request = 'http://{}:8983/solr/{}/select'.format(
            SETTINGS.SOLR_HOST,
            core
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

        # TODO: подумать на структурой строки для логирования
        logging.info(
            'Query_ID: {}\tMessage: From-Solr, maxScore-{}, docsFound-{}'.format(
                request_id,
                docs['response'].get('maxScore', 0),
                docs['response']['numFound']
            )
        )

        return docs
