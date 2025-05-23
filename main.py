import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Update
from flask import Flask, request
from database import init_db, add_question, remove_question, get_questions, add_result, get_results, add_feedback, get_feedback, clear_results, move_questions_to_old
from utils import create_buttons
import time
import threading
from datetime import datetime
import os
import isoweek

# Bot configuration
API = os.environ.get("TELEGRAM_BOT_TOKEN")  # Use environment variable
if not API:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
bot = telebot.TeleBot(API)

# Flask app for webhook
app = Flask(__name__)

# Emojis for UI
admin_emoji = "👨🏽‍💻"
question_emoji = "❓"
feedback_emoji = "📝"
leaderboard_emoji = "🏆"
timer_emoji = "🕒"
correct_emoji = "✅"
incorrect_emoji = "❌"
star_emoji = "⭐"

# Global state
ADMINS_ID = [6473677687]  # Add your Telegram ID
QUIZ_ACTIVE = False
CURRENT_QUIZ_USER = None
QUIZ_ENABLED = False  # Controls access to new questions
user_state = {}  # {user_id: {"current_question": int, "score": int, "start_time": float, "answers": [], "message_id": int, "week_category": str}}
TIMER_INTERVAL = 5  # Update timer every 5 seconds
QUESTION_TIME = 90  # 90 seconds per question

# Initialize database
init_db()

# Markup definitions
def user_home_markup():
    return create_buttons(
        [
            f"{question_emoji} ጥያቄ ጀምር",
            f"{feedback_emoji} መልእክት ላክ",
        ],
        1
    )

def admin_home_markup():
    return create_buttons(
        [
            f"{question_emoji} ጥያቄ ጨምር",
            f"{question_emoji} ጥያቄ አስወግድ",
            f"{leaderboard_emoji} ውጤቶችን ተመልከት",
            f"{feedback_emoji} መልእክቶችን ተመልከት",
            f"{question_emoji} ዕለታዊ ደረጃ አጽዳ",
        ],
        2
    )

def back_markup():
    return create_buttons([f"◀️ ተመለስ"], 1)

def question_type_markup():
    buttons = [f"{question_emoji} አዲስ ጥያቄዎች"] if QUIZ_ENABLED else []
    buttons.append(f"{question_emoji} አሮጌ ጥያቄዎች")
    return create_buttons(buttons, 1)

def question_markup(question_id, week_category):
    questions = get_questions(week_category)
    if question_id >= len(questions):
        return None
    question = questions[question_id]
    markup = InlineKeyboardMarkup(row_width=2)
    for i, choice in enumerate(question["choices"]):
        markup.add(InlineKeyboardButton(f"{chr(65+i)}. {choice}", callback_data=f"answer_{question_id}_{i}_{week_category}"))
    return markup

def feedback_rating_markup():
    return create_buttons([f"{i}{star_emoji}" for i in range(1, 6)], 5)

# Start command
@bot.message_handler(commands=["start"])
def start(message):
    user_state[message.chat.id] = {"current_question": -1, "score": 0, "start_time": 0, "answers": [], "message_id": None, "week_category": None}
    
    if message.chat.id in ADMINS_ID:
        bot.send_message(
            message.chat.id,
            f"{admin_emoji} እንኳን ደህና መጣህ አስተዳዳሪ!",
            reply_markup=admin_home_markup()
        )
    else:
        bot.send_message(
            message.chat.id,
            f"🎉 እንኳን ወደ ፭ ኪሎ ጥያቄና መልስ ውድድር ቦት መጡ!",
            reply_markup=user_home_markup()
        )

# Start quiz command for admins
@bot.message_handler(commands=["startquiz"])
def start_quiz_command(message):
    global QUIZ_ENABLED
    if message.chat.id in ADMINS_ID:
        QUIZ_ENABLED = True
        bot.reply_to(message, "✅ አዲስ ጥያቄዎች ለተጠቃሚዎች ተከፍቷል!")
    else:
        bot.reply_to(message, "🚫 ይህ ትዕዛዝ ለአስተዳዳሪዎች ብቻ ነው።")

# Enough command to move new questions to old
@bot.message_handler(commands=["enough"])
def enough_command(message):
    if message.chat.id in ADMINS_ID:
        current_week = datetime.now().isocalendar()[1]
        week_category = f"Week {current_week}"
        move_questions_to_old(week_category)
        bot.reply_to(message, f"✅ የ{week_category} ጥያቄዎች ወደ አሮጌ ጥያቄዎች ተዛውረዋል!")
    else:
        bot.reply_to(message, "🚫 ይህ ትዕዛዝ ለአስተዳዳሪዎች ብቻ ነው።")

# Text handler
@bot.message_handler(content_types=["text"])
def serve(message):
    global QUIZ_ACTIVE, CURRENT_QUIZ_USER
    chat_id = message.chat.id
    
    if "◀️ ተመለስ" in message.text:
        if QUIZ_ACTIVE and CURRENT_QUIZ_USER == chat_id:
            QUIZ_ACTIVE = False
            CURRENT_QUIZ_USER = None
        user_state[chat_id] = {"current_question": -1, "score": 0, "start_time": 0, "answers": [], "message_id": None, "week_category": None}
        start(message)
        return

    if chat_id in ADMINS_ID:
        handle_admin_actions(message)
    else:
        handle_user_actions(message)

def handle_admin_actions(message):
    chat_id = message.chat.id
    text = message.text

    if question_emoji + " ጥያቄ ጨምር" in text:
        bot.reply_to(
            message,
            "ጥያቄውን በዚህ ቅርጸት ላክ:\nጥያቄ: <ጽሑፍ>\nመልሶች: <መልስ1>, <መልስ2>, <መልስ3>, <መልስ4>\nትክክለኛ መልስ: <0-3 መልስ ቁጥር>\nመግለጫ (ከተፈለገ): <ጽሑፍ>",
            reply_markup=back_markup()
        )
        user_state[chat_id]["mode"] = "add_question"
    elif question_emoji + " ጥያቄ አስወግድ" in text:
        questions = get_questions()
        if not questions:
            bot.reply_to(message, "ምንም ጥያቄዎች የሉም።")
            return
        markup = InlineKeyboardMarkup(row_width=1)
        for q in questions:
            markup.add(InlineKeyboardButton(f"{q['week_category']}: {q['text']}", callback_data=f"remove_{str(q['_id'])}"))
        bot.reply_to(message, "የሚያስወግዱትን ጥያቄ ይምረጡ:", reply_markup=markup)
    elif leaderboard_emoji + " ውጤቶችን ተመልከት" in text:
        results = get_results()
        if not results:
            bot.reply_to(message, "ምንም ውጤቶች የሉም።")
            return
        sorted_results = sorted(results, key=lambda x: (-x["score"], x["time_taken"]))
        response = f"{leaderboard_emoji} ውጤቶች (በነጥብ እና ሰዓት ደረጃ):\n\n"
        for i, result in enumerate(sorted_results, 1):
            response += f"{i}. {result['username']} (ID: {result['user_id']})\n   ነጥብ: {result['score']}/10\n   ሰዓት: {result['time_taken']:.2f} ሰከንድ\n\n"
        bot.reply_to(message, response)
    elif feedback_emoji + " መልእክቶችን ተመልከት" in text:
        feedback = get_feedback()
        if not feedback:
            bot.reply_to(message, "ምንም መልእክቶች የሉም።")
            return
        response = f"{feedback_emoji} የተጠቃሚ መልእክቶች:\n\n"
        for fb in feedback:
            response += f"ተጠቃሚ: {fb['username']} (ID: {fb['user_id']})\nመልእክት: {fb['text']}\nደረጃ: {fb['rating']}{star_emoji}\n\n"
        bot.reply_to(message, response)
    elif question_emoji + " ዕለታዊ ደረጃ አጽዳ" in text:
        clear_results()
        bot.reply_to(message, f"{leaderboard_emoji} ዕለታዊ ደረጃ ጸድቷል።")
    elif user_state.get(chat_id, {}).get("mode") == "add_question":
        try:
            lines = message.text.split("\n")
            question = lines[0].replace("ጥያቄ: ", "").strip()
            choices = lines[1].replace("መልሶች: ", "").split(", ")
            answer = int(lines[2].replace("ትክክለኛ መልስ: ", "").strip())
            explanation = lines[3].replace("መግለጪያ (ከተፈለገ): ", "").strip() if len(lines) > 3 else ""
            if len(choices) != 4 or answer < 0 or answer > 3:
                raise ValueError
            current_week = datetime.now().isocalendar()[1]
            week_category = f"Week {current_week}"
            add_question({"text": question, "choices": choices, "answer": answer, "explanation": explanation, "week_category": week_category})
            bot.reply_to(message, f"{correct_emoji} ጥያቄ ተጨምሯል!", reply_markup=admin_home_markup())
            user_state[chat_id]["mode"] = None
        except:
            bot.reply_to(
                message,
                "ተገቢ ቅርጸት ይጠቀሙ:\nጥያቄ: <ጽሑፍ>\nመልሶች: <መልስ1>, <መልስ2>, <መልስ3>, <መልስ4>\nትክክለኛ መልስ: <0-3 መልስ ቁጥር>\nመግለጫ (ከተፈለገ): <ጽሑፍ>",
                reply_markup=back_markup()
            )

def handle_user_actions(message):
    global QUIZ_ACTIVE, CURRENT_QUIZ_USER
    chat_id = message.chat.id
    text = message.text

    if question_emoji + " ጥያቄ ጀምር" in text:
        questions = get_questions()
        if not questions:
            bot.reply_to(message, "ምንም ጥያቄዎች የሉም። ቆይተው ይሞክሩ።")
            return
        if QUIZ_ACTIVE:
            bot.reply_to(message, "ጥያቄ እየተካሄደ ነው። ቀጣዩን ዙር ይጠብቁ።")
            return
        bot.reply_to(message, "የትኛውን ጥያቄ መጀመር ይፈልጋሉ?", reply_markup=question_type_markup())
        user_state[chat_id]["mode"] = "select_question_type"
    elif text == f"{question_emoji} አዲስ ጥያቄዎች" and user_state.get(chat_id, {}).get("mode") == "select_question_type":
        if not QUIZ_ENABLED:
            bot.reply_to(message, "🚫 አዲስ ጥያቄዎች ገና አልተከፈቱም። አስተዳዳሪው እስኪጀምር ይጠብቁ።")
            return
        current_week = datetime.now().isocalendar()[1]
        week_category = f"Week {current_week}"
        questions = get_questions(week_category)
        if not questions:
            bot.reply_to(message, f"ምንም አዲስ ጥያቄዎች በ{week_category} ውስጥ የሉም።")
            return
        QUIZ_ACTIVE = True
        CURRENT_QUIZ_USER = chat_id
        user_state[chat_id] = {"current_question": 0, "score": 0, "start_time": time.time(), "answers": [], "message_id": None, "week_category": week_category}
        send_question(chat_id, 0, week_category)
        user_state[chat_id]["mode"] = None
    elif text == f"{question_emoji} አሮጌ ጥያቄዎች" and user_state.get(chat_id, {}).get("mode") == "select_question_type":
        questions = get_questions("Old Questions")
        if not questions:
            bot.reply_to(message, "ምንም አሮጌ ጥያቄዎች የሉም።")
            return
        QUIZ_ACTIVE = True
        CURRENT_QUIZ_USER = chat_id
        user_state[chat_id] = {"current_question": 0, "score": 0, "start_time": time.time(), "answers": [], "message_id": None, "week_category": "Old Questions"}
        send_question(chat_id, 0, "Old Questions")
        user_state[chat_id]["mode"] = None
    elif feedback_emoji + " መልእክት ላክ" in text:
        user_state[chat_id]["mode"] = "feedback"
        bot.reply_to(message, "መልእክትህን ላክ እና ደረጃ ስጥ:", reply_markup=feedback_rating_markup())
    elif leaderboard_emoji + " ደረጃ ተመልከት" in text:
        bot.reply_to(message, "🚫 ይህ ተግባር ለአስተዳዳሪዎች ብቻ ነው።")
    elif user_state.get(chat_id, {}).get("mode") == "feedback":
        try:
            rating = int(message.text[0]) if message.text[0].isdigit() else 1
            feedback_text = message.text[1:].strip() or "ምንም መልእክት የለም"
            add_feedback({
                "user_id": chat_id,
                "username": message.from_user.username or message.from_user.first_name,
                "text": feedback_text,
                "rating": rating,
                "timestamp": datetime.now().isoformat()
            })
            bot.reply_to(message, f"{feedback_emoji} መልእክት ተልኳል! እናመሰግናለን!", reply_markup=user_home_markup())
            user_state[chat_id]["mode"] = None
        except:
            bot.reply_to(message, "እባክህ ደረጃ (1-5) እና መልእክት ላክ:", reply_markup=feedback_rating_markup())

def send_question(chat_id, question_idx, week_category):
    questions = get_questions(week_category)
    if question_idx >= 10 or question_idx >= len(questions):
        end_quiz(chat_id)
        return
    question = questions[question_idx]
    time_remaining = QUESTION_TIME
    message = bot.send_message(
        chat_id,
        f"{question_emoji} ጥያቄ {question_idx + 1}/10 ({week_category}):\n{question['text']}\n\n{timer_emoji} ቀሪ ሰዓት: {time_remaining} ሰከንድ",
        reply_markup=question_markup(question_idx, week_category)
    )
    user_state[chat_id]["message_id"] = message.message_id
    user_state[chat_id]["current_question"] = question_idx
    # Start timer
    threading.Timer(0, update_timer, args=(chat_id, question_idx, week_category, time.time())).start()
    threading.Timer(QUESTION_TIME, lambda: next_question(chat_id, question_idx, week_category)).start()

def update_timer(chat_id, question_idx, week_category, start_time):
    if chat_id not in user_state or user_state[chat_id]["current_question"] != question_idx:
        return
    elapsed = time.time() - start_time
    remaining = max(0, QUESTION_TIME - elapsed)
    if remaining <= 0:
        return
    questions = get_questions(week_category)
    if question_idx >= len(questions):
        return
    question = questions[question_idx]
    try:
        bot.edit_message_text(
            f"{question_emoji} ጥያቄ {question_idx + 1}/10 ({week_category}):\n{question['text']}\n\n{timer_emoji} ቀሪ ሰዓቴ: {int(remaining)} ሰከንድ",
            chat_id=chat_id,
            message_id=user_state[chat_id]["message_id"],
            reply_markup=question_markup(question_idx, week_category)
        )
        threading.Timer(TIMER_INTERVAL, update_timer, args=(chat_id, question_idx, week_category, start_time)).start()
    except:
        pass  # Message not modified (e.g., deleted)

def next_question(chat_id, current_idx, week_category):
    if chat_id not in user_state or user_state[chat_id]["current_question"] != current_idx:
        return
    user_state[chat_id]["current_question"] += 1
    send_question(chat_id, user_state[chat_id]["current_question"], week_category)

def end_quiz(chat_id):
    global QUIZ_ACTIVE, CURRENT_QUIZ_USER
    score = user_state[chat_id]["score"]
    time_taken = time.time() - user_state[chat_id]["start_time"]
    week_category = user_state[chat_id]["week_category"]
    add_result({
        "user_id": chat_id,
        "username": bot.get_chat(chat_id).username or bot.get_chat(chat_id).first_name,
        "score": score,
        "time_taken": time_taken,
        "week_category": week_category,
        "timestamp": datetime.now().isoformat()
    })
    bot.send_message(
        chat_id,
        f"🎉 ጥያቄ ተጠናቋል!\nነጥብህ: {score}/10\nሰዓት: {time_taken:.2f} ሰከንድ\nምድብ: {week_category}",
        reply_markup=user_home_markup()
    )
    QUIZ_ACTIVE = False
    CURRENT_QUIZ_USER = None
    user_state[chat_id] = {"current_question": -1, "score": 0, "start_time": 0, "answers": [], "message_id": None, "week_category": None}

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    questions = get_questions()
    
    if call.data.startswith("answer_"):
        _, question_id, choice_idx, week_category = call.data.split("_")
        question_id = int(question_id)
        choice_idx = int(choice_idx)
        if chat_id not in user_state or user_state[chat_id]["current_question"] != question_id:
            return
        questions = get_questions(week_category)
        if question_id >= len(questions):
            return
        question = questions[question_id]
        correct = choice_idx == question["answer"]
        if correct:
            user_state[chat_id]["score"] += 1
            bot.answer_callback_query(call.id, f"{correct_emoji} ትክክል!")
        else:
            bot.answer_callback_query(call.id, f"{incorrect_emoji} ስህተት!")
        user_state[chat_id]["answers"].append(choice_idx)
        explanation = question.get("explanation", "")
        if explanation:
            bot.send_message(chat_id, f"📚 መግለጫ: {explanation}")
        bot.delete_message(chat_id, call.message.message_id)
        user_state[chat_id]["current_question"] += 1
        send_question(chat_id, user_state[chat_id]["current_question"], week_category)
    elif call.data.startswith("remove_"):
        question_id = call.data.split("_")[1]
        remove_question(question_id)
        bot.reply_to(call.message, f"{correct_emoji} ጥያቄ ተወግዷል!", reply_markup=admin_home_markup())
        bot.delete_message(chat_id, call.message.message_id)

# Flask webhook endpoint
@app.route(f"/{API}", methods=["POST"])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return '', 400

# Health check endpoint for debugging
@app.route('/')
def health_check():
    return "Bot is running!", 200

# Main function to set webhook and start Flask
def main():
    bot.remove_webhook()
    DOMAIN = "gibigubae.onrender.com"
    WEBHOOK_URL = f"https://{DOMAIN}/{API}"
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8443)))

if __name__ == "__main__":
    main()
