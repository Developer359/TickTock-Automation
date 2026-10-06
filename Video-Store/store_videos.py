import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_final_videos(folder_path: str = "Final-Video", bucket_name: str = "tiktok-videos"):
    """
    Uploads all videos from Final-Video folder into the 'tiktok-videos' Supabase bucket.
    """
    if not os.path.exists(folder_path):
        print(f"❌ Error: Local folder '{folder_path}' not found!")
        return

    # Find all mp4 files in Final-Video
    files = [f for f in os.listdir(folder_path) if f.endswith(".mp4")]

    if not files:
        print(f"⚠️ No MP4 videos found in '{folder_path}'.")
        return

    print(f"📁 Found {len(files)} video(s). Uploading to bucket: '{bucket_name}'...\n")

    for file_name in files:
        local_file_path = os.path.join(folder_path, file_name)
        storage_path = f"uploads/{file_name}"

        print(f"🚀 Uploading: {file_name}...")

        try:
            with open(local_file_path, "rb") as f:
                response = supabase.storage.from_(bucket_name).upload(
                    path=storage_path,
                    file=f,
                    file_options={"cache-control": "3600", "upsert": "true"}
                )

            # Get public URL from the bucket
            public_url = supabase.storage.from_(bucket_name).get_public_url(storage_path)
            print(f"✅ Successfully uploaded!\n   🔗 URL: {public_url}\n")

        except Exception as e:
            print(f"❌ Failed to upload {file_name}: {e}\n")

if __name__ == "__main__":
    upload_final_videos()