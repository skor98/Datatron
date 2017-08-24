from os import path

from flask import abort, send_file

from config import SETTINGS


class ResourceHelper:
    # помогает получить ресурсы

    @staticmethod
    def get_image(image_id):
        return ResourceHelper.get_resource(image_id, "img", 'image/jpeg')

    @staticmethod
    def get_document(document_id):
        return ResourceHelper.get_resource(document_id, "doc", 'application/pdf')

    @staticmethod
    def get_resource(resource_id, resource_type, resource_mimetype):
        if not resource_id:
            abort(404)
        resource_path = path.join(SETTINGS.DATATRON_FOLDER, "data", "minfin", resource_type, resource_id)
        if not path.isfile(resource_path):
            abort(404, message="Resource {} is NOT valid".format(resource_id))

        return send_file(resource_path, mimetype=resource_mimetype)
