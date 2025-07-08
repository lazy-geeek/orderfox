import firebase_admin
from firebase_admin import credentials, firestore
import json
from typing import Optional, Dict, Any, List

# Assuming your config.py has a 'settings' object
from app.core.config import settings

# Global variable to hold the Firestore client
db: Optional[firestore.Client] = None


def initialize_firebase():
    """
    Initializes the Firebase Admin SDK using credentials from environment variables.
    Sets the global 'db' variable to the Firestore client.
    """
    global db
    try:
        firebase_config_json_str = settings.FIREBASE_CONFIG_JSON
        if firebase_config_json_str:
            firebase_config_dict = json.loads(firebase_config_json_str)

            # Check if the app is already initialized to prevent
            # re-initialization error
            if not firebase_admin._apps:
                cred = credentials.Certificate(firebase_config_dict)
                firebase_admin.initialize_app(cred)
                db = firestore.client()
                print("Firebase Admin SDK initialized successfully.")
            else:
                # App is already initialized, just get the default app's
                # firestore client
                db = firestore.client(firebase_admin.get_app())
                print(
                    "Firebase Admin SDK was already initialized. Using existing instance."
                )
        else:
            print(
                "FIREBASE_CONFIG_JSON not found in environment variables. Firebase not initialized."
            )
            db = None
    except json.JSONDecodeError:
        print("Error: FIREBASE_CONFIG_JSON is not a valid JSON string.")
        db = None
    except ValueError as e:  # Handles issues with credentials.Certificate()
        print(f"Error initializing Firebase Admin SDK: {e}")
        print(
            "Ensure your Firebase service account key JSON is correctly formatted and valid."
        )
        db = None
    except Exception as e:
        print(
            f"An unexpected error occurred during Firebase initialization: {e}")
        db = None


# Call initialization at module load time.
# Alternatively, you could have an explicit init function called from
# main.py startup.
initialize_firebase()


def get_db() -> Optional[firestore.Client]:
    """
    Returns the Firestore client.
    Ensures Firebase is initialized before returning the client.
    """
    if db is None and settings.FIREBASE_CONFIG_JSON:
        # Attempt to re-initialize if db is None but config exists
        # This might happen if initial load failed but config was later set,
        # or if used in a context where module load order is tricky.
        print("Attempting to re-initialize Firebase as db client was None.")
        initialize_firebase()
    return db


# --- Placeholder Helper Functions ---


async def save_settings(user_id: str, user_settings: Dict[str, Any]) -> bool:
    """
    Placeholder: Saves user-specific settings to Firestore.
    """
    firestore_db = get_db()
    if not firestore_db:
        print("Firestore not initialized. Cannot save settings.")
        return False
    try:
        # Example: /users/{user_id}/settings/{doc_id_or_fixed_name}
        # Using a fixed document name 'config' under user's settings collection
        doc_ref = (
            firestore_db.collection("user_settings")
            .document(user_id)
            .collection("settings")
            .document("config")
        )
        await doc_ref.set(
            user_settings, merge=True
        )  # Use merge=True to update existing fields
        print(f"Settings saved for user {user_id}.")
        return True
    except Exception as e:
        print(f"Error saving settings for user {user_id}: {e}")
        return False


async def load_settings(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Placeholder: Loads user-specific settings from Firestore.
    """
    firestore_db = get_db()
    if not firestore_db:
        print("Firestore not initialized. Cannot load settings.")
        return None
    try:
        doc_ref = (
            firestore_db.collection("user_settings")
            .document(user_id)
            .collection("settings")
            .document("config")
        )
        doc = await doc_ref.get()
        if doc.exists:
            print(f"Settings loaded for user {user_id}.")
            return doc.to_dict()
        else:
            print(f"No settings found for user {user_id}.")
            return None
    except Exception as e:
        print(f"Error loading settings for user {user_id}: {e}")
        return None


async def save_paper_trade(
        user_id: str, trade_data: Dict[str, Any]) -> Optional[str]:
    """
    Placeholder: Saves a paper trade to Firestore.
    Returns the ID of the saved trade document or None on failure.
    """
    firestore_db = get_db()
    if not firestore_db:
        print("Firestore not initialized. Cannot save paper trade.")
        return None
    try:
        # Example: /users/{user_id}/paper_trades/{trade_id}
        # Add a server timestamp for when the trade was recorded
        trade_data_with_timestamp = {
            **trade_data,
            "timestamp": firestore.SERVER_TIMESTAMP,
        }
        doc_ref = (
            await firestore_db.collection("user_paper_trades")
            .document(user_id)
            .collection("trades")
            .add(trade_data_with_timestamp)
        )
        print(f"Paper trade saved for user {user_id} with ID: {doc_ref.id}")
        return doc_ref.id
    except Exception as e:
        print(f"Error saving paper trade for user {user_id}: {e}")
        return None


async def load_paper_trade_history(
    user_id: str, limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Placeholder: Loads paper trade history for a user from Firestore, ordered by time.
    """
    firestore_db = get_db()
    if not firestore_db:
        print("Firestore not initialized. Cannot load paper trade history.")
        return []
    try:
        trades_ref = (
            firestore_db.collection("user_paper_trades")
            .document(user_id)
            .collection("trades")
        )
        query = trades_ref.order_by(
            "timestamp", direction=firestore.Query.DESCENDING
        ).limit(limit)
        docs = await query.stream()  # Use stream() for async iteration

        history = []
        async for doc in docs:  # Iterate asynchronously
            trade_entry = doc.to_dict()
            trade_entry["id"] = doc.id  # Add document ID to the trade data
            history.append(trade_entry)

        print(f"Loaded {len(history)} paper trades for user {user_id}.")
        return history
    except Exception as e:
        print(f"Error loading paper trade history for user {user_id}: {e}")
        return []


# Example of how you might call this from your main app startup if not at module load:
# initialize_firebase() can be called explicitly from main.py startup
