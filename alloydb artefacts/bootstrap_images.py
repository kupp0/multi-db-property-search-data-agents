import os
import psycopg2
import vertexai
from vertexai.vision_models import ImageGenerationModel
from vertexai.vision_models import MultiModalEmbeddingModel, Image as VertexImage
from google.cloud import storage
from PIL import Image as PilImage
from dotenv import load_dotenv

# Find and load the .env file from the backend directory
# Script is in "alloydb artefacts/", .env is in "backend/" (sibling directories)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
dotenv_path = os.path.join(project_root, 'backend', '.env')
print(f"Loading environment from: {dotenv_path}")
load_dotenv(dotenv_path=dotenv_path)

# --- CONFIGURATION ---
PROJECT_ID = os.getenv("GCP_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GCP_LOCATION", "europe-west1")
BUCKET_NAME = f"property-images-{PROJECT_ID}" # Matches the bucket you just created

print(f"🚀 Starting Image Bootstrap for Project: {PROJECT_ID}")
print(f"📂 Target Bucket: {BUCKET_NAME}")

# --- INITIALIZE CLIENTS ---
vertexai.init(project=PROJECT_ID, location=LOCATION)
gen_model = ImageGenerationModel.from_pretrained("gemini-3.1-flash-image-preview")
embed_model = MultiModalEmbeddingModel.from_pretrained("multimodalembedding@001")
storage_client = storage.Client()

def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME", "search"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
        host="127.0.0.1", # Uses your running Auth Proxy
        port="5432"
    )

def generate_and_upload(listing_id, description):
    try:
        print(f"\n[ID: {listing_id}] Generating image for: {description[:50]}...")
        
        # 1. Generate Image with Imagen
        prompt = f"A professional architectural photograph of {description}. High quality, realistic, 4k, sunny day."
        response = gen_model.generate_images(prompt=prompt, number_of_images=1)
        generated_image = response[0]
        
        # 2. Save locally temporarily
        temp_png = f"temp_{listing_id}.png"
        temp_jpg = f"temp_{listing_id}.jpg"
        generated_image.save(temp_png)
        
        # 3. Compress to JPEG
        with PilImage.open(temp_png) as img:
            img = img.convert("RGB") # Ensure no alpha channel
            img.save(temp_jpg, "JPEG", quality=85, optimize=True)
        
        # 4. Upload to GCS
        destination_blob_name = f"listings/{listing_id}.jpg"
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(temp_jpg)
        
        # Public URL (if bucket is public) or gs:// URI
        gcs_uri = f"gs://{BUCKET_NAME}/{destination_blob_name}"
        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{destination_blob_name}"
        
        # 4. Generate Multi-Modal Embedding (The "Visual Vector")
        # We use the compressed JPEG for consistency
        print(f"[ID: {listing_id}] Calculating visual embeddings...")
        v_image = VertexImage.load_from_file(temp_jpg)
        embeddings = embed_model.get_embeddings(image=v_image, dimension=1408)
        vector_data = embeddings.image_embedding
        
        # Cleanup local files
        if os.path.exists(temp_png): os.remove(temp_png)
        if os.path.exists(temp_jpg): os.remove(temp_jpg)
        
        return public_url, vector_data

    except Exception as e:
        print(f"❌ Error processing ID {listing_id}: {e}")
        if os.path.exists(f"temp_{listing_id}.png"): os.remove(f"temp_{listing_id}.png")
        if os.path.exists(f"temp_{listing_id}.jpg"): os.remove(f"temp_{listing_id}.jpg")
        return None, None

def main():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Find listings that don't have an image yet
    print("🔍 Querying AlloyDB for listings without images...")
    cursor.execute("""
        SELECT id, description 
        FROM property_listings 
        WHERE image_gcs_uri IS NULL
        ORDER BY id ASC
    """)
    rows = cursor.fetchall()
    print(f"Found {len(rows)} listings to process.")

    for row in rows:
        listing_id, description = row
        
        # Generate Image & Vector
        image_url, vector = generate_and_upload(listing_id, description)
        
        if image_url and vector:
            # 2. Update Database
            try:
                cursor.execute("""
                    UPDATE property_listings
                    SET image_gcs_uri = %s,
                        image_embedding = %s
                    WHERE id = %s
                """, (image_url, str(vector), listing_id))
                conn.commit()
                print(f"✅ [ID: {listing_id}] Database updated successfully.")
            except Exception as db_err:
                print(f"❌ DB Write Error: {db_err}")
                conn.rollback()
        else:
            print(f"⚠️ Skipping DB update for ID {listing_id} due to generation failure.")

    cursor.close()
    conn.close()
    print("\n🎉 Bootstrapping Complete!")

if __name__ == "__main__":
    main()
    