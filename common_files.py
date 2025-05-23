from utils import *

admin_question_emoji = "🖋"
answer_emoji = "✍️"
comment_emoji = "📖"
question_emoji = "❓"
info_emoji = "ℹ️"
admin_emoji = "👨🏽‍💻"
back_button_emoji = "◀️"

back_markup = create_buttons(["{} ተመለስ".format(back_button_emoji)], 1)
admin_home_markup = create_buttons(
    [
        "{} ጥያቄ ጨምር".format(admin_question_emoji),
        "{} መልሶችን ለማየት".format(answer_emoji),
        "{} አስተያየቶችን ለማየት".format(comment_emoji),
        "{} የተጠየቁ ጥያቄዎችን ለማየት".format(question_emoji),
        "{} መረጃ ለመጨመር".format(info_emoji),
    ],
    3,
)
user_home_markup = create_buttons(
    [
        "{} መልስ ለመመለስ".format(answer_emoji),
        "{} አስተያየት ለመስጠት".format(comment_emoji),
        "{} ጥያቄ ለመጠየቅ".format(question_emoji),
        "{} መረጃ ለማግኘት".format(info_emoji),
    ],
    2,
)
