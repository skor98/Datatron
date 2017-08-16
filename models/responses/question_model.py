class QuestionModel:
    def __init__(self, question):
        self.question = question

    def to_reduced_object(self):
        keys_to_return = []
        keys_to_return.append('question')

        return {key: getattr(self, key, None) for key in keys_to_return}

    def to_reduced_api_object(self):
        res = self.to_reduced_object()

        return res
