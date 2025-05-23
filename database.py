import os

from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv
load_dotenv()


MONGO_URI = os.getenv("MONGO_URI") or "mongodb+srv://loariftech:Loarif1227@cluster0.i958ogv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"


client = MongoClient(MONGO_URI)
db = client.quiz_bot

def init_db():
    # Create indexes for performance
    db.questions.create_index([("category", 1)])
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
        "category": question["category"],
        "explanation": question["explanation"]
    })

def remove_question(question_id):
    db.questions.delete_one({"_id": ObjectId(question_id)})

def get_questions(category=None):
    if category:
        questions = db.questions.find({"category": category})
    else:
        questions = db.questions.find()
    return [
        {
            "_id": str(q["_id"]),
            "text": q["text"],
            "choices": q["choices"],
            "answer": q["answer"],
            "category": q["category"],
            "explanation": q["explanation"]
        }
        for q in questions
    ]

def add_result(result):
    db.results.insert_one({
        "user_id": result["user_id"],
        "username": result["username"],
        "score": result["score"],
        "time_taken": result["time_taken"],
        "category": result["category"],
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
            "category": r["category"],
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