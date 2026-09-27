import json
import os
import urllib.parse
import urllib.request
import uuid
from typing import Any, Dict, List, Optional
from google.cloud import firestore

# Hardcoded Project ID string per requirement
PROJECT_ID = "qwiklabs-gcp-03-89266242dbeb"


def _get_firestore_client() -> firestore.Client:
    return firestore.Client(project=PROJECT_ID)


def get_recent_workouts(athlete_id: str = "user1", limit: int = 10) -> List[Dict]:
    """Retrieve recent logged workouts for an athlete from Firestore.

    Args:
        athlete_id: The ID of the athlete (defaults to 'user1').
        limit: Maximum number of workouts to return.

    Returns:
        List of dictionaries containing workout details.
    """
    db = _get_firestore_client()
    query = (
        db.collection("workouts")
        .where("athlete_id", "==", athlete_id)
        .limit(limit)
    )
    docs = query.stream()
    results = []
    for doc in docs:
        results.append(doc.to_dict())
    return results


def log_workout(
    activity_type: str,
    title: str,
    duration_minutes: int,
    distance_km: float = 0.0,
    avg_heart_rate: Optional[int] = None,
    perceived_exertion: Optional[int] = None,
    notes: str = "",
    athlete_id: str = "user1",
) -> str:
    """Log a new workout entry into Firestore.

    Args:
        activity_type: The type of workout ('swim', 'bike', 'run', or 'strength').
        title: Descriptive title for the workout session.
        duration_minutes: Duration of the workout in minutes.
        distance_km: Distance covered in kilometers (optional, defaults to 0.0).
        avg_heart_rate: Average heart rate during the workout in bpm (optional).
        perceived_exertion: Rating of perceived exertion on a scale of 1 to 10 (optional).
        notes: Additional notes or feedback on the session.
        athlete_id: ID of the athlete (defaults to 'user1').

    Returns:
        A confirmation message with the generated workout_id.
    """
    db = _get_firestore_client()
    workout_id = f"workout_{uuid.uuid4().hex[:8]}"
    doc_data = {
        "workout_id": workout_id,
        "athlete_id": athlete_id,
        "activity_type": activity_type.lower(),
        "title": title,
        "duration_minutes": duration_minutes,
        "distance_km": distance_km,
        "avg_heart_rate": avg_heart_rate,
        "perceived_exertion": perceived_exertion,
        "notes": notes,
    }
    db.collection("workouts").document(workout_id).set(doc_data)
    return f"Successfully logged workout '{title}' (ID: {workout_id}) for {activity_type}."


def calculate_training_zones(
    age: int,
    resting_hr: int = 60,
    max_hr: Optional[int] = None,
) -> Dict[str, Any]:
    """Calculate Karvonen Heart Rate Training Zones (Zone 1 to Zone 5) for an athlete.

    Args:
        age: Athlete's age in years.
        resting_hr: Resting heart rate in bpm (defaults to 60 bpm).
        max_hr: Maximum heart rate in bpm (optional; if omitted, estimated as 220 - age).

    Returns:
        Dictionary containing max_hr, heart rate reserve (hrr), and target bpm ranges for Zones 1-5.
    """
    if max_hr is None or max_hr <= 0:
        max_hr = 220 - age

    hrr = max_hr - resting_hr

    def zone_bpm(pct: float) -> int:
        return int(round(resting_hr + (hrr * pct)))

    return {
        "max_heart_rate": max_hr,
        "resting_heart_rate": resting_hr,
        "heart_rate_reserve": hrr,
        "zones": {
            "Zone 1 (Active Recovery)": f"{zone_bpm(0.50)} - {zone_bpm(0.60)} bpm",
            "Zone 2 (Aerobic Base)": f"{zone_bpm(0.60)} - {zone_bpm(0.70)} bpm",
            "Zone 3 (Tempo / Aerobic Endurance)": f"{zone_bpm(0.70)} - {zone_bpm(0.80)} bpm",
            "Zone 4 (Lactate Threshold)": f"{zone_bpm(0.80)} - {zone_bpm(0.90)} bpm",
            "Zone 5 (Anaerobic / Max Effort)": f"{zone_bpm(0.90)} - {zone_bpm(1.00)} bpm",
        },
    }


def calculate_weekly_tss_and_recovery(
    athlete_id: str = "user1",
    days: int = 7,
) -> Dict[str, Any]:
    """Analyze recent logged workouts in Firestore to calculate cumulative Training Stress Score (TSS) and recovery status.

    Args:
        athlete_id: ID of the athlete (defaults to 'user1').
        days: Number of recent days of workouts to analyze (defaults to 7).

    Returns:
        Dictionary containing total workouts, hours trained, total distance, calculated TSS, and recovery recommendation.
    """
    db = _get_firestore_client()
    query = (
        db.collection("workouts")
        .where("athlete_id", "==", athlete_id)
        .limit(20)
    )
    docs = query.stream()
    
    total_workouts = 0
    total_duration_minutes = 0
    total_distance_km = 0.0
    total_tss = 0.0
    sport_breakdown = {"swim": 0.0, "bike": 0.0, "run": 0.0, "strength": 0.0}

    for doc in docs:
        w = doc.to_dict()
        total_workouts += 1
        dur = w.get("duration_minutes", 0) or 0
        dist = w.get("distance_km", 0.0) or 0.0
        rpe = w.get("perceived_exertion", 6) or 6
        activity = (w.get("activity_type", "other") or "other").lower()

        total_duration_minutes += dur
        total_distance_km += dist
        if activity in sport_breakdown:
            sport_breakdown[activity] += dist

        # Estimated TSS per workout: (duration in hours) * (RPE * 10)
        workout_tss = (dur / 60.0) * (rpe * 10)
        total_tss += workout_tss

    total_hours = round(total_duration_minutes / 60.0, 1)
    round_tss = round(total_tss, 1)

    if round_tss < 150:
        recovery_status = "Fresh (Low Fatigue). Ready for high-intensity intervals or long endurance training."
    elif round_tss <= 350:
        recovery_status = "Optimal Training Load. Fitness is building well; maintain current recovery protocols."
    else:
        recovery_status = "High Training Load / Fatigue. Prioritize active recovery, sleep, and hydration before hard efforts."

    return {
        "athlete_id": athlete_id,
        "total_workouts_logged": total_workouts,
        "total_training_hours": total_hours,
        "total_distance_km": round(total_distance_km, 1),
        "sport_distance_breakdown_km": {k: round(v, 1) for k, v in sport_breakdown.items()},
        "cumulative_tss": round_tss,
        "recovery_status": recovery_status,
    }


def calculate_ftp_power_zones(ftp_watts: int) -> Dict[str, Any]:
    """Calculate cycling power training zones (Zone 1 to Zone 7) based on Functional Threshold Power (FTP) in Watts.

    Args:
        ftp_watts: Athlete's Functional Threshold Power in Watts (e.g., 250).

    Returns:
        Dictionary containing FTP watts and power target ranges for Zones 1-7 in Watts.
    """
    return {
        "ftp_watts": ftp_watts,
        "power_zones": {
            "Zone 1 (Active Recovery)": f"< {int(round(ftp_watts * 0.55))} W (< 55% FTP)",
            "Zone 2 (Endurance)": f"{int(round(ftp_watts * 0.55))} - {int(round(ftp_watts * 0.75))} W (55-75% FTP)",
            "Zone 3 (Tempo)": f"{int(round(ftp_watts * 0.76))} - {int(round(ftp_watts * 0.90))} W (76-90% FTP)",
            "Zone 4 (Lactate Threshold)": f"{int(round(ftp_watts * 0.91))} - {int(round(ftp_watts * 1.05))} W (91-105% FTP)",
            "Zone 5 (VO2 Max)": f"{int(round(ftp_watts * 1.06))} - {int(round(ftp_watts * 1.20))} W (106-120% FTP)",
            "Zone 6 (Anaerobic Capacity)": f"{int(round(ftp_watts * 1.21))} - {int(round(ftp_watts * 1.50))} W (121-150% FTP)",
            "Zone 7 (Neuromuscular Power)": f"> {int(round(ftp_watts * 1.50))} W (> 150% FTP)",
        },
    }


def get_outdoor_training_weather(location: str = "Boulder") -> Dict[str, Any]:
    """Fetch current real-time outdoor weather conditions (temperature, wind, humidity) for a training location using the free Open-Meteo API.

    Args:
        location: City or location name (e.g. 'Boulder', 'Kona', 'San Francisco', 'Austin').

    Returns:
        Dictionary containing location, temperature, wind speed, humidity, and outdoor training recommendation.
    """
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(location)}&count=1&language=en&format=json"
        geo_req = urllib.request.Request(geo_url, headers={"User-Agent": "TriCoachAI/1.0"})
        with urllib.request.urlopen(geo_req, timeout=5) as resp:
            geo_data = json.loads(resp.read().decode("utf-8"))
            results = geo_data.get("results", [])

        if not results:
            return {"error": f"Location '{location}' not found."}

        loc_info = results[0]
        lat, lon = loc_info["latitude"], loc_info["longitude"]
        city_name = loc_info.get("name", location)
        country = loc_info.get("country", "")

        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
        w_req = urllib.request.Request(weather_url, headers={"User-Agent": "TriCoachAI/1.0"})
        with urllib.request.urlopen(w_req, timeout=5) as w_resp:
            w_data = json.loads(w_resp.read().decode("utf-8"))
            current = w_data.get("current", {})

        temp_c = current.get("temperature_2m", 0.0)
        temp_f = round((temp_c * 9 / 5) + 32, 1)
        wind_kmh = current.get("wind_speed_10m", 0.0)
        humidity = current.get("relative_humidity_2m", 0)

        if wind_kmh > 35:
            recommendation = "High wind speeds! Exercise caution on outdoor bike rides; consider indoor trainer or run."
        elif temp_f > 85:
            recommendation = "Hot conditions! Stay hydrated, wear sunscreen, or schedule early morning training."
        elif temp_f < 40:
            recommendation = "Cold weather! Layer up appropriately for outdoor run/bike or train indoors."
        else:
            recommendation = "Great conditions for outdoor swim, bike, or run training!"

        return {
            "location": f"{city_name}, {country}".strip(", "),
            "latitude": lat,
            "longitude": lon,
            "temperature_celsius": temp_c,
            "temperature_fahrenheit": temp_f,
            "wind_speed_kmh": wind_kmh,
            "humidity_percent": humidity,
            "outdoor_recommendation": recommendation,
        }
    except Exception as e:
        return {"error": f"Failed to fetch weather data: {str(e)}"}


def geocode_address(address: str) -> Dict[str, Any]:
    """Geocode a street address or location name into latitude and longitude coordinates using Google Maps Geocoding API.

    Args:
        address: Street address, city, or landmark (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        Dictionary containing formatted address, latitude, longitude, and place_id.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}

    try:
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={urllib.parse.quote(address)}&key={api_key}"
        req = urllib.request.Request(url, headers={"User-Agent": "TriCoachAI/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if data.get("status") != "OK" or not data.get("results"):
            return {"error": f"Failed to geocode address '{address}': {data.get('status')}"}

        result = data["results"][0]
        location = result["geometry"]["location"]
        return {
            "formatted_address": result.get("formatted_address"),
            "latitude": location.get("lat"),
            "longitude": location.get("lng"),
            "place_id": result.get("place_id"),
        }
    except Exception as e:
        return {"error": f"Geocoding request failed: {str(e)}"}


def find_nearby_training_places(
    latitude: float,
    longitude: float,
    place_type: str = "gym",
    radius_meters: int = 3000,
) -> Dict[str, Any]:
    """Find nearby athletic facilities (gym, park, swimming pool, sports complex) using Google Places API (New).

    Args:
        latitude: Center latitude coordinate.
        longitude: Center longitude coordinate.
        place_type: Type of facility to search for (e.g. 'gym', 'park', 'swimming_pool', 'sports_complex').
        radius_meters: Search radius in meters (defaults to 3000m / 3 km).

    Returns:
        Dictionary containing search center, place_type, and list of matching places with name, formatted address, location, and types.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}

    try:
        url = "https://places.googleapis.com/v1/places:searchNearby"
        body = {
            "includedTypes": [place_type],
            "maxResultCount": 5,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": latitude, "longitude": longitude},
                    "radius": float(radius_meters),
                }
            },
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.types",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        places_data = []
        for p in data.get("places", []):
            places_data.append({
                "name": p.get("displayName", {}).get("text"),
                "formatted_address": p.get("formattedAddress"),
                "location": p.get("location"),
                "types": p.get("types", []),
            })

        return {
            "search_center": {"latitude": latitude, "longitude": longitude},
            "place_type": place_type,
            "radius_meters": radius_meters,
            "places": places_data,
        }
    except Exception as e:
        return {"error": f"Places API search failed: {str(e)}"}
