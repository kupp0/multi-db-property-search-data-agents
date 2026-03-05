import os
import json
import time
import vertexai
from vertexai.vision_models import ImageGenerationModel
from vertexai.vision_models import MultiModalEmbeddingModel, Image as VertexImage
from google.cloud import storage
from PIL import Image as PilImage
from dotenv import load_dotenv

# Find and load the .env file from the backend directory
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
dotenv_path = os.path.join(project_root, 'backend', '.env')
print(f"Loading environment from: {dotenv_path}")
load_dotenv(dotenv_path=dotenv_path)

# --- CONFIGURATION ---
PROJECT_ID = os.getenv("GCP_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GCP_LOCATION", "europe-west1")
BUCKET_NAME = f"property-images-data-agent-{PROJECT_ID}" # Matches the bucket created by Terraform

print(f"🚀 Starting Image Bootstrap for Project: {PROJECT_ID}")
print(f"📂 Target Bucket: {BUCKET_NAME}")

# --- INITIALIZE CLIENTS ---
vertexai.init(project=PROJECT_ID, location=LOCATION)
gen_model = ImageGenerationModel.from_pretrained("imagen-4.0-fast-generate-001")
embed_model = MultiModalEmbeddingModel.from_pretrained("multimodalembedding@001")
storage_client = storage.Client()

def generate_and_upload(listing_id, description):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"\n[ID: {listing_id}] Generating image for: {description[:50]}... (Attempt {attempt + 1}/{max_retries})")
            
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
            
            # 5. Generate Multi-Modal Embedding (The "Visual Vector")
            # We use the compressed JPEG for consistency
            print(f"[ID: {listing_id}] Calculating visual embeddings...")
            v_image = VertexImage.load_from_file(temp_jpg)
            embeddings = embed_model.get_embeddings(image=v_image, dimension=1408)
            vector_data = embeddings.image_embedding
            
            # Cleanup local files
            if os.path.exists(temp_png): os.remove(temp_png)
            if os.path.exists(temp_jpg): os.remove(temp_jpg)
            
            # Add a small delay to avoid hitting quota limits
            time.sleep(2)
            
            return public_url, vector_data

        except Exception as e:
            print(f"❌ Error processing ID {listing_id}: {e}")
            if os.path.exists(f"temp_{listing_id}.png"): os.remove(f"temp_{listing_id}.png")
            if os.path.exists(f"temp_{listing_id}.jpg"): os.remove(f"temp_{listing_id}.jpg")
            if attempt < max_retries - 1:
                sleep_time = (attempt + 1) * 5
                print(f"⏳ Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                return None, None

def main():
    data_file = os.path.join(current_dir, "enriched_property_data.json")
    
    print(f"🔍 Loading data from {data_file}...")
    with open(data_file, 'r', encoding='utf-8') as f:
        properties = json.load(f)
        
    print(f"Loaded {len(properties)} listings.")
    
    updated_count = 0
    for p in properties:
        if not p.get("image_gcs_uri"):
            listing_id = p["id"]
            description = p["description"]
            
            # Generate Image & Vector
            image_url, vector = generate_and_upload(listing_id, description)
            
            if image_url and vector:
                p["image_gcs_uri"] = image_url
                p["image_embedding"] = vector
                updated_count += 1
                print(f"✅ [ID: {listing_id}] JSON object updated successfully.")
            else:
                print(f"⚠️ Skipping update for ID {listing_id} due to generation failure.")
                
    if updated_count > 0:
        print(f"\n💾 Saving {updated_count} updated records back to {data_file}...")
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(properties, f, indent=2)
        print("✅ File saved successfully!")
    else:
        print("\nℹ️ No new images were generated. File was not updated.")

    print("\n🎉 Bootstrapping Complete!")

if __name__ == "__main__":
    main()
    