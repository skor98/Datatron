from db.user_db_creation import User, Feedback


def check_user_existence(user_id):
    if User.select().where(User.user_id == user_id).count():
        return True
    else:
        return False


def create_user(user_id, user_name, full_user_name):
    User.create(user_id=user_id, user_name=user_name, full_user_name=full_user_name, expert_mode=0, question_mode=0)


def create_feedback(user_id, time, feedback):
    if check_user_existence(user_id):
        u = User.select().where(User.user_id == user_id)
        Feedback.create(user=u, time=str(time), feedback=feedback)


def get_feedbacks():
    feedbacks = []
    for feedback in Feedback.select():
        for user in User.select().where(User.id == feedback.user_id):
            fb = '{} {} {}'.format(feedback.time, user.full_user_name, feedback.feedback)
            feedbacks.append(fb)
    return '\n'.join(feedbacks)


def define_question_mode(user_id, question_mode):
    User.update(question_mode=question_mode).where(User.user_id == user_id).execute()


def get_question_mode(user_id):
    return User.get(User.user_id == user_id).question_mode


def define_expert_mode(user_id, expert_mode):
    User.update(expert_mode=expert_mode).where(User.user_id == user_id).execute()


def get_expert_mode(user_id):
    return User.get(User.user_id == user_id).expert_mode
