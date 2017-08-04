#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Взаимодействие с Apache Solr
"""

import logging
import requests

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
            'fl': '*,score',
            'bf': "recip(max(1,lem_member_caption_len),1.5,5,0)",
            'defType': "edismax"  # тип парсера, этот самый мощный
        }

        # recip(x,m,a,b) implementing a/(m*x+b)
        # пробела запрщенеы
        # max нужен, чтобы поправить минфин, у которых этого поля вовсе пока нет

        # Свободный 0 и 1.5 коэфф.
        # 5(0.75,0.29) -> 10 (0.76,0.286) -> 2(0.77,0.294) -> 0(0.78, 0.30)
        # Свободный 1
        # 2(0.767, 0.30)

        # 1.5,5,0 -> 0.89,0.92 по минфину
        # 2.5, 8, 0 -> 0.89,0.92 по минфину

        docs = requests.get(request, params=params).json()

        logging.info(
            'Query_ID: {}\tMessage: Solr нашел {} документ(ов), макс. score = {}'.format(
                request_id,
                docs['response']['numFound'],
                docs['response'].get('maxScore', 0)
            )
        )

        return docs
