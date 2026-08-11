import uuid
from datetime import datetime
import requests
import os
from dotenv import load_dotenv
from storage import (
    add_entry,
    find_entry,
    initialize_data_file,
    load_entries,
    load_suggestions
)

from flask import Flask, abort, redirect, render_template, request, url_for

app = Flask(__name__)

load_dotenv()

KEYWORD_FILTER_SERVICE_URL = os.getenv(
    "KEYWORD_FILTER_SERVICE_URL",
    "http://localhost:5556"
)

DATE_TIME_SERVICE_URL = os.getenv(
    "DATE_TIME_SERVICE_URL",
    "http://localhost:5555"
)

HF_TOKEN = os.getenv("HF_TOKEN")
FAVORITES_USER_ID = os.getenv("FAVORITES_USER_ID", "local-user")
FAVORITES_SERVICE_URL = os.getenv(
    "FAVORITES_SERVICE_URL",
    "http://localhost:3001"
)

MOOD_FORMATTER_SERVICE_URL = os.getenv(
    "MOOD_FORMATTER_SERVICE_URL",
    "http://localhost:3000"
)

print(HF_TOKEN)

VALID_MOODS = {
    "very-happy": {
        "name": "very happy",
        "emoji": "😄"
    },
    "happy": {
        "name": "happy",
        "emoji": "🙂"
    },
    "neutral": {
        "name": "neutral",
        "emoji": "😐"
    },
    "sad": {
        "name": "sad",
        "emoji": "😢"
    },
    "angry": {
        "name": "angry",
        "emoji": "😠"
    }
}


def send_to_mood_formatter(entry):
    text = (
        f"Mood: {entry['mood_name']}. "
        f"Note: {entry['note']}"
    )

    response = requests.post(
        f"{MOOD_FORMATTER_SERVICE_URL}/api/mood/format",
        json={
            "endpoint": (
                "/hf-inference/models/"
                "j-hartmann/"
                "emotion-english-distilroberta-base"
            ),
            "method": "POST",
            "language": "python",
            "parameters": [
                {
                    "key": "inputs",
                    "value": text,
                    "type": "body"
                }
            ]
        }
    )

    response.raise_for_status()

    return response.json()


def call_emotion_api(formatted_request):
    request_data = formatted_request[
        "result"
    ][
        "request"
    ]

    headers = request_data.get(
        "headers",
        {}
    )

    headers["Authorization"] = (
        f"Bearer {HF_TOKEN}"
    )

    response = requests.request(
        method=request_data["method"],
        url=request_data["url"],
        headers=headers,
        json=request_data["body"]
    )

    response.raise_for_status()

    return response.json()


def convert_emotion_result(result):

    # Hugging Face returns a list of emotions
    best_match = result[0][0]

    emotion = best_match["label"]
    confidence = best_match["score"]

    emotion_map = {
        "joy": "happy",
        "surprise": "happy",
        "neutral": "neutral",
        "sadness": "sad",
        "anger": "angry",
        "fear": "stress",
        "disgust": "angry"
    }

    return {
        "emotion": emotion_map.get(
            emotion,
            "neutral"
        ),
        "confidence": confidence
    }


def get_suggestion(emotion):
    suggestions = load_suggestions(
        emotion
    )

    if suggestions:
        return suggestions

    return "Take a moment for yourself"

# ---------------------------------------------------------
# FAVORITING MICROSERVICE FUNCTIONS
# ---------------------------------------------------------

def favorite_entry(entry):
    response = requests.post(
        f"{FAVORITES_SERVICE_URL}/save-mood/{FAVORITES_USER_ID}",
        json={
            "mood_id": entry["id"],
            "mood": entry["mood_name"],
            "note": entry["note"]
        }
    )

    response.raise_for_status()
    return response.json()


def unfavorite_entry(entry_id):
    response = requests.delete(
        f"{FAVORITES_SERVICE_URL}/remove-mood/{FAVORITES_USER_ID}",
        json={
            "mood_id": entry_id
        }
    )

    response.raise_for_status()
    return response.json()


def get_favorites():
    response = requests.get(
        f"{FAVORITES_SERVICE_URL}/saved-moods",
        params={
            "id": FAVORITES_USER_ID
        }
    )

    response.raise_for_status()
    return response.json()

def filter_keywords(keywords, filter_text, filter_type="includes"):
    response = requests.post(
        f"{KEYWORD_FILTER_SERVICE_URL}/filter-keywords",
        json={
            "keywords": keywords,
            "filter": filter_text,
            "filterType": filter_type
        }
    )

    response.raise_for_status()

    data = response.json()

    return data["filteredKeywords"]

@app.route("/favorites")
def favorites():
    try:
        saved_moods = get_favorites()

        entries = load_entries()

        favorite_ids = {
            saved_mood.get("mood_id")
            for saved_mood in saved_moods
        }

        favorite_entries = [
            entry
            for entry in entries
            if entry.get("id") in favorite_ids
        ]

        favorite_entries.sort(
            key=lambda entry: entry.get(
                "created_at",
                ""
            )
        )

        for entry in favorite_entries:
            entry["is_favorite"] = True

            add_formatted_date_time(
                entry
            )

    except requests.RequestException as error:
        print(
            f"Could not connect to favorites service: {error}"
        )

        favorite_entries = []

    return render_template(
        "favorites.html",
        entries=favorite_entries
    )


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/entry", methods=["GET", "POST"])
def create_entry():
    if request.method == "POST":
        mood_key = request.form.get("mood", "").strip()
        note = request.form.get("note", "").strip()

        if mood_key not in VALID_MOODS:
            return render_template(
                "entry.html",
                moods=VALID_MOODS,
                error="Please choose a mood before saving.",
                previous_note=note
            ), 400

        now = datetime.now()
        selected_mood = VALID_MOODS[mood_key]

        entry = {
            "id": str(uuid.uuid4()),
            "mood_key": mood_key,
            "mood_name": selected_mood["name"],
            "emoji": selected_mood["emoji"],
            "note": note,
            "date": now.strftime("%m/%d/%Y"),
            "time": now.strftime("%I:%M %p"),
            "created_at": now.isoformat()
        }

        add_entry(entry)


        try:
            formatted_request = send_to_mood_formatter(entry)

            emotion_response = call_emotion_api(
               formatted_request
            )

            print(
                "Emotion response:",
                emotion_response
            )

            emotion_result = convert_emotion_result(
                emotion_response
            )

            emotion_result["suggestion"] = get_suggestion(
                emotion_result["emotion"]
            )

        except requests.RequestException as error:
            print(
                f"Analysis service error: {error}"
            )

        # return render_template(
        #     "analysis.html",
        #     analysis=emotion_result,
        #     entry=entry
        # )
        #return redirect(url_for("history", saved="true"))

        # return redirect(
        #     url_for(
        #         "details",
        #         entry_id=entry["id"]
        #     )
        # )
            emotion_result = {
                "emotion": "unavailable",
                "confidence": 0,
                "suggestion": (
                    "Your entry was saved, but "
                    "analysis is currently unavailable."
                )
            }

        return redirect(
            url_for(
                "details",
                entry_id=entry["id"],
                analysis=emotion_result["emotion"],
                confidence=round(
                    emotion_result["confidence"] * 100,
                    1
                ),
                suggestion=emotion_result["suggestion"]
            )
        )  

    return render_template(
        "entry.html",
        moods=VALID_MOODS,
        error=None,
        previous_note=""
    )


@app.route("/history")
def history():
    entries = load_entries()

    entries.sort(
        key=lambda entry: entry.get(
            "created_at",
            ""
        )
    )

    search = request.args.get(
        "search",
        ""
    ).strip()

    if search:
        notes = [
            entry.get("note", "")
            for entry in entries
            if entry.get("note", "")
        ]

        try:
            filtered_notes = filter_keywords(
                notes,
                search,
                "includes"
            )

            entries = [
                entry
                for entry in entries
                if entry.get("note", "")
                in filtered_notes
            ]

        except requests.RequestException as error:
            print(
                f"Could not connect to keyword filter service: {error}"
            )

    for entry in entries:
        add_formatted_date_time(
            entry
        )

    try:
        favorites = get_favorites()

        favorite_ids = {
            favorite.get("mood_id")
            for favorite in favorites
        }

        for entry in entries:
            entry["is_favorite"] = (
                entry["id"]
                in favorite_ids
            )

    except requests.RequestException as error:
        print(
            f"Could not connect to favorites service: {error}"
        )

        for entry in entries:
            entry["is_favorite"] = False

    return render_template(
        "history.html",
        entries=entries,
        search=search,
        entry_saved=(
            request.args.get("saved")
            == "true"
        )
    )

@app.route("/entry/<entry_id>")
def details(entry_id):
    entry = find_entry(
        entry_id
    )

    if entry is None:
        abort(404)

    add_formatted_date_time(
        entry
    )

    try:
        favorites = get_favorites()

        entry["is_favorite"] = any(
            favorite.get("mood_id") == entry_id
            for favorite in favorites
        )

    except requests.RequestException as error:
        print(
            f"Could not connect to favorites service: {error}"
        )

        entry["is_favorite"] = False

    analysis = request.args.get(
        "analysis"
    )

    confidence = request.args.get(
        "confidence"
    )

    suggestion = request.args.get(
        "suggestion"
    )

    return render_template(
        "details.html",
        entry=entry,
        analysis=analysis,
        confidence=confidence,
        suggestion=suggestion
    )

    # return render_template(
    #     "details.html",
    #     entry=entry
    # )


@app.route(
    "/entry/<entry_id>/favorite",
    methods=["POST"]
)
def add_favorite(entry_id):
    entry = find_entry(entry_id)

    if entry is None:
        abort(404)

    try:
        result = favorite_entry(
            entry
        )

        print(
            "Favorite response:",
            result
        )

    except requests.RequestException as error:
        print(
            f"Could not favorite entry: {error}"
        )

    return redirect(
        url_for(
            "details",
            entry_id=entry_id
        )
    )

def format_entry_date(date):
    response = requests.post(
        f"{DATE_TIME_SERVICE_URL}/format-date",
        json={
            "date": date
        }
    )

    response.raise_for_status()

    data = response.json()

    return data["formattedDate"]


def format_entry_time(time):
    response = requests.post(
        f"{DATE_TIME_SERVICE_URL}/format-time",
        json={
            "time": time
        }
    )

    response.raise_for_status()

    data = response.json()

    return data["formattedTime"]

def add_formatted_date_time(entry):
    try:
        entry["formatted_date"] = format_entry_date(
            entry["date"]
        )

        entry["formatted_time"] = format_entry_time(
            entry["time"]
        )

    except requests.RequestException as error:
        print(
            f"Could not connect to date/time service: {error}"
        )

        entry["formatted_date"] = entry["date"]
        entry["formatted_time"] = entry["time"]

    return entry

@app.route("/entry/<entry_id>/unfavorite", methods=["POST"])
def remove_favorite(entry_id):
    entry = find_entry(entry_id)

    if entry is None:
        abort(404)

    try:
        unfavorite_entry(entry_id)

    except requests.RequestException as error:
        print(f"Could not remove favorite: {error}")

    return redirect(
        url_for("details", entry_id=entry_id)
    )



def analyze_sentiment(score):

    if score < -0.5:
        return "stress"

    elif score > 0.5:
        return "happy"

    else:
        return "neutral"


if __name__ == "__main__":
    initialize_data_file()
    app.run(debug=True)
