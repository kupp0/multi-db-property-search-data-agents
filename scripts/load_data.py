import os
import json
import psycopg2
import pymysql
from google.cloud import spanner
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
dotenv_path = os.path.join(project_root, 'backend', '.env')
load_dotenv(dotenv_path=dotenv_path)

# Load data
data_file = os.path.join(project_root, "database_artefacts", "enriched_property_data.json")
with open(data_file, 'r', encoding='utf-8') as f:
    properties = json.load(f)

print(f"Loaded {len(properties)} records from JSON.")

# --- ALLOYDB & CLOUD SQL PG ---
def load_postgres(host, port, dbname, user, password, name):
    print(f"\nLoading data into {name} ({host}:{port})...")
    try:
        conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
        cursor = conn.cursor()
        
        # Clear existing data
        cursor.execute("TRUNCATE TABLE property_listings RESTART IDENTITY CASCADE;")
        
        for p in properties:
            cursor.execute("""
                INSERT INTO property_listings 
                (id, title, description, price, bedrooms, city, country, canton, description_embedding, image_embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                p['id'], p['title'], p['description'], p['price'], p['bedrooms'], 
                p['city'], p['country'], p['canton'], 
                str(p['description_embedding']), str(p['image_embedding'])
            ))
            
        conn.commit()
        cursor.close()
        conn.close()
        print(f"✅ Successfully loaded {len(properties)} records into {name}.")
    except Exception as e:
        print(f"❌ Failed to load into {name}: {e}")

# --- CLOUD SQL MYSQL ---
def load_mysql(host, port, dbname, user, password, name):
    print(f"\nLoading data into {name} ({host}:{port})...")
    try:
        conn = pymysql.connect(host=host, port=port, database=dbname, user=user, password=password)
        cursor = conn.cursor()
        
        # Clear existing data
        cursor.execute("TRUNCATE TABLE property_listings;")
        
        for p in properties:
            # MySQL uses string_to_vector('[1,2,3]')
            desc_emb_str = str(p['description_embedding'])
            img_emb_str = str(p['image_embedding'])
            
            cursor.execute(f"""
                INSERT INTO property_listings 
                (id, title, description, price, bedrooms, city, country, canton, description_embedding, image_embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, string_to_vector(%s), string_to_vector(%s))
            """, (
                p['id'], p['title'], p['description'], p['price'], p['bedrooms'], 
                p['city'], p['country'], p['canton'], 
                desc_emb_str, img_emb_str
            ))
            
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
            # Clear existing data (Spanner doesn't have TRUNCATE, so we delete all)
            transaction.execute_update("DELETE FROM property_listings WHERE true")
            
            for p in properties:
                # Spanner PG dialect accepts string representations of vectors
                transaction.execute_update(
                    """
                    INSERT INTO property_listings 
                    (id, title, description, price, bedrooms, city, country, canton, description_embedding, image_embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    params=(
                        p['id'], p['title'], p['description'], p['price'], p['bedrooms'], 
                        p['city'], p['country'], p['canton'], 
                        str(p['description_embedding']), str(p['image_embedding'])
                    )
                )
                
        database.run_in_transaction(insert_properties)
        print(f"✅ Successfully loaded {len(properties)} records into Spanner.")
    except Exception as e:
        print(f"❌ Failed to load into Spanner: {e}")

def main():
    # In a real scenario, these would be read from .env or passed as args.
    # For the demo, we assume the Auth Proxy is running on different local ports
    # e.g., AlloyDB: 5432, Cloud SQL PG: 5433, Cloud SQL MySQL: 3306
    
    # Example usage (commented out to prevent accidental execution without setup):
    '''
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
        user=os.getenv("CLOUDSQL_PG_USER", "postgres"), 
        password=os.getenv("CLOUDSQL_PG_PASSWORD"), 
        name="Cloud SQL PG"
    )
    
    load_mysql(
        host="127.0.0.1", port=3306, 
        dbname=os.getenv("CLOUDSQL_MYSQL_DB_NAME", "search"), 
        user=os.getenv("CLOUDSQL_MYSQL_USER", "root"), 
        password=os.getenv("CLOUDSQL_MYSQL_PASSWORD"), 
        name="Cloud SQL MySQL"
    )
    
    load_spanner(
        instance_id=os.getenv("SPANNER_INSTANCE_ID", "search-instance"),
        database_id=os.getenv("SPANNER_DATABASE_ID", "search-db"),
        project_id=os.getenv("GCP_PROJECT_ID")
    )
    '''
    print("Load script ready. Edit main() to execute against your running databases.")

if __name__ == "__main__":
    main()
