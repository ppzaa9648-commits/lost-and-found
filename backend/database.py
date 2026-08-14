import os
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv

dotenv_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=dotenv_path)

# Use the explicitly provided keys if env vars are missing
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://edtqnpooywmwxjcgcnqj.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_ezQWhPN-sMXxNc6KqPnmng_wIu6VBi2")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def get_supabase() -> Client:
    # Use Service Key (Admin) if available to bypass RLS
    is_placeholder = not SUPABASE_SERVICE_KEY or SUPABASE_SERVICE_KEY.upper() in ("YOUR_SUPABASE_SERVICE_KEY", "YOUR_SUPABASE_SERVICE_ROLE_KEY")
    key = SUPABASE_KEY if is_placeholder else SUPABASE_SERVICE_KEY
    if not SUPABASE_URL or not key:
        raise Exception("Supabase credentials not found.")
    return create_client(SUPABASE_URL, key)

