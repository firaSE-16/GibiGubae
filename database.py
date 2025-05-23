from pymongo import MongoClient
from bson.objectid import ObjectId
import os

# MongoDB Atlas connection
MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable not set")
client = MongoClient(MONGO_URI)
db = client.quiz_bot

def init_db():
    # Create indexes for performance
    db.questions.create_index([("week_category", 1)])
    db.results.create_index([("user_id", 1), ("timestamp", 1)])
    db.feedback.create_index([("user_id", 1), ("timestamp", 1)])
    # Ensure admin collection has at least one admin
    if db.admins.count_documents({}) == 0:
        db.admins.insert_one({"admin_ids": [6473677687]})

def add_question(question):
    db.questions.insert_one({
        "text": question["text"],
        "choices": question["choices"],
        "answer": question["answer"],
        "explanation": question["explanation"],
        "week_category": question["week_category"]
    })

def remove_question(question_id):
    db.questions.delete_one({"_id": ObjectId(question_id)})

def get_questions(week_category=None):
    if week_category:
        questions = db.questions.find({"week_category": week_category})
    else:
        questions = db.questions.find()
    return [
        {
            "_id": str(q["_id"]),
            "text": q["text"],
            "choices": q["choices"],
            "answer": q["answer"],
            "explanation": q["explanation"],
            "week_category": q["week_category"]
        }
        for q in questions
    ]

def move_questions_to_old(week_category):
    db.questions.update_many(
        {"week_category": week_category},
        {"$set": {"week_category": "Old Questions"}}
    )

def add_result(result):
    db.results.insert_one({
        "user_id": result["user_id"],
        "username": result["username"],
        "score": result["score"],
        "time_taken": result["time_taken"],
        "week_category": result["week_category"],
        "timestamp": result["timestamp"]
    })

def get_results():
    results = db.results.find()
    return [
        {
            "user_id": r["user_id"],
            "username": r["username"],
            "score": r["score"],
            "time_taken": r["time_taken"],
            "week_category": r.get("week_category", "Unknown"),
            "timestamp": r["timestamp"]
        }
        for r in results
    ]

def add_feedback(feedback):
    db.feedback.insert_one({
        "user_id": feedback["user_id"],
        "username": feedback["username"],
        "text": feedback["text"],
        "rating": feedback["rating"],
        "timestamp": feedback["timestamp"]
    })

def get_feedback():
    feedback = db.feedback.find()
    return [
        {
            "user_id": f["user_id"],
            "username": f["username"],
            "text": f["text"],
            "rating": f["rating"],
            "timestamp": f["timestamp"]
        }
        for f in feedback
    ]

def clear_results():
    db.results.delete_many({})
