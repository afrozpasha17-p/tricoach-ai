from google.cloud import firestore

# Hardcoded Project ID per requirement
PROJECT_ID = "qwiklabs-gcp-03-89266242dbeb"

def seed_database():
    print(f"Connecting to Firestore for project: {PROJECT_ID}")
    db = firestore.Client(project=PROJECT_ID)
    
    seed_workouts = [
        {
            "workout_id": "workout_101",
            "athlete_id": "user1",
            "activity_type": "run",
            "title": "Morning Tempo Run",
            "date": "2026-09-25",
            "duration_minutes": 45,
            "distance_km": 8.5,
            "avg_heart_rate": 152,
            "perceived_exertion": 7,
            "notes": "Felt strong on the hills, steady pace throughout.",
        },
        {
            "workout_id": "workout_102",
            "athlete_id": "user1",
            "activity_type": "bike",
            "title": "Endurance Bike Ride",
            "date": "2026-09-26",
            "duration_minutes": 90,
            "distance_km": 38.0,
            "avg_heart_rate": 138,
            "perceived_exertion": 6,
            "notes": "Smooth cadence, focused on Zone 2 aerobic efficiency.",
        },
        {
            "workout_id": "workout_103",
            "athlete_id": "user1",
            "activity_type": "swim",
            "title": "Technique & Drills Swim",
            "date": "2026-09-27",
            "duration_minutes": 35,
            "distance_km": 1.8,
            "avg_heart_rate": 128,
            "perceived_exertion": 5,
            "notes": "Worked on catch-and-pull mechanics and bilateral breathing.",
        },
    ]

    collection_ref = db.collection("workouts")
    for workout in seed_workouts:
        doc_ref = collection_ref.document(workout["workout_id"])
        doc_ref.set(workout)
        print(f"Seeded workout: {workout['workout_id']} - {workout['title']}")

    print("Firestore seeding complete! ✅")

if __name__ == "__main__":
    seed_database()
