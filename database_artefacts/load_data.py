import os
import json
import psycopg2
import psycopg2.extras
from google.cloud import spanner
from dotenv import load_dotenv
import decimal

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
dotenv_path = os.path.join(project_root, 'backend', '.env')
load_dotenv(dotenv_path=dotenv_path)

# Disable Spanner built-in metrics to prevent OpenTelemetry export errors
os.environ["SPANNER_DISABLE_BUILTIN_METRICS"] = "true"

# Load data
data_file = os.path.join(current_dir, "enriched_property_data.json")
with open(data_file, 'r', encoding='utf-8') as f:
    properties = json.load(f)

print(f"Loaded {len(properties)} records from JSON.")

# --- ALLOYDB & CLOUD SQL PG ---
def load_postgres(host, port, dbname, user, password, name):
    print(f"\nLoading data into {name} ({host}:{port})...")
    try:
        conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
        cursor = conn.cursor()
        
        # Drop existing ScaNN indexes if they exist (to avoid empty table index creation error)
        cursor.execute("DROP INDEX IF EXISTS property_listings_desc_idx;")
        cursor.execute("DROP INDEX IF EXISTS property_listings_img_idx;")
        
        # Clear existing data
        cursor.execute("TRUNCATE TABLE property_listings RESTART IDENTITY CASCADE;")
        
        # Prepare data for batched insert
        # PostgreSQL vector type accepts string representation of arrays e.g. '[1.0, 2.0]'
        values = [
            (
                p['id'], p['title'], p.get('description', ''), p['price'], p['bedrooms'], 
                p.get('city', ''), p.get('country', 'Switzerland'), p.get('canton', ''), 
                p.get('image_gcs_uri'),
                str(p['description_embedding']) if p.get('description_embedding') else None, 
                str(p['image_embedding']) if p.get('image_embedding') else None
            )
            for p in properties
        ]
        
        insert_query = """
            INSERT INTO property_listings 
            (id, title, description, price, bedrooms, city, country, canton, image_gcs_uri, description_embedding, image_embedding)
            VALUES %s
        """
        
        # Use execute_values for fast batched insert
        psycopg2.extras.execute_values(cursor, insert_query, values, page_size=100)
            
        conn.commit()
        cursor.close()
        conn.close()
        print(f"✅ Successfully loaded {len(properties)} records into {name}.")
    except Exception as e:
        print(f"❌ Failed to load into {name}: {e}")

# --- CLOUD SPANNER ---
def load_spanner(instance_id, database_id, project_id):
    print(f"\nLoading data into Spanner ({instance_id}/{database_id})...")
    try:
        spanner_client = spanner.Client(project=project_id)
        instance = spanner_client.instance(instance_id)
        database = instance.database(database_id)
        
        def insert_properties(transaction):
            # Clear existing data
            transaction.execute_update("DELETE FROM property_listings WHERE true")
            
            # Prepare data for batched insert (Mutations)
            # Spanner Google Standard SQL dialect accepts Python lists for ARRAY<FLOAT64>
            columns = (
                "id", "title", "description", "price", "bedrooms", 
                "city", "country", "canton", "image_gcs_uri",
                "description_embedding", "image_embedding"
            )
            
            values = [
                (
                    p['id'], p['title'], p.get('description', ''), decimal.Decimal(str(p['price'])), int(p['bedrooms']), 
                    p.get('city', ''), p.get('country', 'Switzerland'), p.get('canton', ''), 
                    p.get('image_gcs_uri'),
                    p.get('description_embedding'), # Pass list directly
                    p.get('image_embedding')        # Pass list directly
                )
                for p in properties
            ]
            
            # Use transaction.insert for fast batched ingest via Mutations
            transaction.insert(
                table="property_listings",
                columns=columns,
                values=values
            )
                
        database.run_in_transaction(insert_properties)
        print(f"✅ Successfully loaded {len(properties)} records into Spanner.")
    except Exception as e:
        print(f"❌ Failed to load into Spanner: {e}")

def main():
    # In a real scenario, these would be read from .env or passed as args.
    # For the demo, we assume the Auth Proxy is running on different local ports
    # e.g., AlloyDB: 5432, Cloud SQL PG: 5433
    
    load_postgres(
        host="127.0.0.1", port=5432, 
        dbname=os.getenv("DB_NAME", "search"), 
        user=os.getenv("DB_USER", "postgres"), 
        password=os.getenv("DB_PASSWORD"), 
        name="AlloyDB"
    )
    
    load_postgres(
        host="127.0.0.1", port=5433, 
        dbname=os.getenv("CLOUDSQL_PG_DB_NAME", "search"), 
        user=os.getenv("DB_USER", "postgres"), 
        password=os.getenv("DB_PASSWORD"), 
        name="Cloud SQL PG"
    )
    
    load_spanner(
        instance_id=os.getenv("SPANNER_INSTANCE_ID", "search-instance"),
        database_id=os.getenv("SPANNER_DATABASE_ID", "search-db"),
        project_id=os.getenv("GCP_PROJECT_ID")
    )

if __name__ == "__main__":
    main()
