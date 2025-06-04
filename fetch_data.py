import requests
import pandas as pd
import os

FIREBASE_BASE_URL = "https://iotcaproject-6422d-default-rtdb.europe-west1.firebasedatabase.app/air_quality_data"

def get_all_sessions():
    try:
        response = requests.get(f"{FIREBASE_BASE_URL}.json")
        response.raise_for_status()
        data = response.json()
        if data is None:
            print("(x) no sessions found in Firebase.")
            return []
        return list(data.keys())
    except Exception as e:
        print("(x) error fetching session list:", e)
        return []

def fetch_session_data(session_id):
    try:
        url = f"{FIREBASE_BASE_URL}/{session_id}.json"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if not data:
            print(f"(x) no data for session {session_id}")
            return pd.DataFrame()
        df = pd.DataFrame.from_dict(data, orient='index')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values(by='timestamp')
        return df
    except Exception as e:
        print(f"(x) error fetching data for session {session_id}:", e)
        return pd.DataFrame()

def user_select_sessions(all_sessions):
    print(f"\nThere are {len(all_sessions)} sessions available:")
    for i, sess in enumerate(all_sessions):
        print(f"{i+1}. {sess}")

    while True:
        selection = input(
            "\nRetrieve sessions (by number separated by ' ' | all): "
        ).strip().lower()

        if selection == 'all':
            return all_sessions

        if not selection:
            print("(x) no input detected!")
            continue

        try:
            indices = [int(x) - 1 for x in selection.split()]
            if any(i < 0 or i >= len(all_sessions) for i in indices):
                print("(x) invalid session number(s)!")
                continue
            selected_sessions = [all_sessions[i] for i in indices]
            return selected_sessions
        except ValueError:
            print("(x) invalid input!")

if __name__ == "__main__":
    sessions = get_all_sessions()
    if not sessions:
        print("(x) no sessions to fetch.")
        exit()

    # Sort sessions descending (most recent first)
    sessions.sort(reverse=True)

    selected_sessions = user_select_sessions(sessions)

    output_folder = "pandas"
    os.makedirs(output_folder, exist_ok=True)

    for session_id in selected_sessions:
        print(f"\nFetching data for {session_id} ...")
        df = fetch_session_data(session_id)
        if not df.empty:
            filename = os.path.join(output_folder, f"air_quality_{session_id}.csv")
            df.to_csv(filename, index=False)
            print(f"Saved session '{session_id}' data to {filename}")
        else:
            print(f"(x) no data to save for session {session_id}")
