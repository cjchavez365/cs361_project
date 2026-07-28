import uuid
from datetime import datetime

from flask import Flask, abort, redirect, render_template, request, url_for

from storage import add_entry, find_entry, initialize_data_file, load_entries


app = Flask(__name__)


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

        return redirect(url_for("history", saved="true"))

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
        key=lambda entry: entry.get("created_at", "")
    )

    return render_template(
        "history.html",
        entries=entries,
        entry_saved=request.args.get("saved") == "true"
    )


@app.route("/entry/<entry_id>")
def details(entry_id):
    entry = find_entry(entry_id)

    if entry is None:
        abort(404)

    return render_template(
        "details.html",
        entry=entry
    )


if __name__ == "__main__":
    initialize_data_file()
    app.run(debug=True)