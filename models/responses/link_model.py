class LinkModel:
    def __init__(self, link_type, description, uri):
        self.type = link_type
        self.description = description
        self.uri = uri

    def to_reduced_object(self):
        keys_to_return = (
            'type',
            'description',
            'uri'
        )

        return {key: getattr(self, key, None) for key in keys_to_return}

    def to_reduced_api_object(self):
        res = self.to_reduced_object()

        return res
