import os
import json
import re
from dotenv import load_dotenv
import vertexai
from vertexai.language_models import TextEmbeddingModel
from vertexai.vision_models import MultiModalEmbeddingModel

# Load environment variables
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
dotenv_path = os.path.join(project_root, 'backend', '.env')
load_dotenv(dotenv_path=dotenv_path)

PROJECT_ID = os.getenv("GCP_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GCP_LOCATION", "europe-west1")

print(f"Initializing Vertex AI in {PROJECT_ID} ({LOCATION})...")
vertexai.init(project=PROJECT_ID, location=LOCATION)

# Initialize models
TEXT_EMBEDDING_MODEL = os.getenv("TEXT_EMBEDDING_MODEL", "gemini-embedding-001")
IMAGE_EMBEDDING_MODEL = os.getenv("IMAGE_EMBEDDING_MODEL", "multimodalembedding@001")

text_model = TextEmbeddingModel.from_pretrained(TEXT_EMBEDDING_MODEL)
mm_model = MultiModalEmbeddingModel.from_pretrained(IMAGE_EMBEDDING_MODEL)

def parse_sql_values(sql_file_path):
    """Parses the DML SQL file to extract the values."""
    with open(sql_file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the INSERT INTO statement
    match = re.search(r"INSERT INTO property_listings.*?VALUES\s*(.*);", content, re.DOTALL | re.IGNORECASE)
    if not match:
        raise ValueError("Could not find INSERT statement in SQL file.")
    
    values_str = match.group(1)
    
    # Split into individual tuples. This is a simple parser and assumes no complex nested parentheses in strings.
    # A more robust way is to split by "),\n("
    raw_tuples = re.findall(r"\((.*?)\)", values_str, re.DOTALL)
    
    parsed_data = []
    for i, raw_tuple in enumerate(raw_tuples):
        # Split by comma, but respect single quotes
        # This regex splits by comma only if it's not inside single quotes
        parts = re.split(r",(?=(?:[^']*'[^']*')*[^']*$)", raw_tuple)
        
        if len(parts) >= 7:
            title = parts[0].strip().strip("'")
            description = parts[1].strip().strip("'")
            price = float(parts[2].strip())
            bedrooms = float(parts[3].strip())
            city = parts[4].strip().strip("'")
            country = parts[5].strip().strip("'")
            canton = parts[6].strip().strip("'")
            
            parsed_data.append({
                "id": i + 1,
                "title": title,
                "description": description,
                "price": price,
                "bedrooms": bedrooms,
                "city": city,
                "country": country,
                "canton": canton,
                "image_gcs_uri": None # Placeholder, can be updated later if images are generated
            })
            
    return parsed_data

def generate_embeddings(data):
    """Generates text and multimodal embeddings for the data."""
    print(f"Generating embeddings for {len(data)} records...")
    
    # Process in batches to avoid API limits
    batch_size = 10
    for i in range(0, len(data), batch_size):
        batch = data[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(data)+batch_size-1)//batch_size}...")
        
        descriptions = [item["description"] for item in batch]
        
        # Generate Text Embeddings (3072 dims)
        text_embeddings = text_model.get_embeddings(descriptions)
        
        for j, item in enumerate(batch):
            item["description_embedding"] = text_embeddings[j].values
            
            # Generate Multimodal Embedding (1408 dims)
            # To save time/cost of generating 300+ images, we embed the text description 
            # using the multimodal model. The Data Agent context compares text to this embedding.
            import time
            time.sleep(1) # Rate limiting to avoid QuotaExceeded
            mm_embedding = mm_model.get_embeddings(contextual_text=item["description"], dimension=1408)
            item["image_embedding"] = mm_embedding.text_embedding
            
    return data

def main():
    sql_file = os.path.join(project_root, "alloydb artefacts", "DML_sample records.sql")
    output_file = os.path.join(project_root, "database_artefacts", "enriched_property_data.json")
    
    print("Parsing SQL data...")
    raw_data = parse_sql_values(sql_file)
    print(f"Parsed {len(raw_data)} records.")
    
    # For testing/speed, let's limit to 50 records if it's too large, or process all.
    # Processing 320 records takes a minute or two. Let's process all.
    enriched_data = generate_embeddings(raw_data)
    
    print(f"Saving enriched data to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(enriched_data, f, indent=2)
        
    print("Data generation complete!")

if __name__ == "__main__":
    main()
