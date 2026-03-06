import os
import sys
import asyncio
import asyncpg
from dotenv import load_dotenv

# Load environment variables
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')
dotenv_path = os.path.join(backend_dir, '.env')
load_dotenv(dotenv_path=dotenv_path)

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_NAME = os.environ.get("DB_NAME", "search")

async def apply_sql_file(conn, filepath):
    print(f"Applying {filepath}...")
    with open(filepath, 'r') as f:
        sql = f.read()
    
    # Split by semicolon to execute statements individually if needed, 
    # but asyncpg.execute can handle multiple statements usually.
    # However, for large files or specific commands, splitting might be safer or required.
    # alloydb_setup.sql has some specific commands.
    # Let's try executing the whole block first.
    try:
        await conn.execute(sql)
        print(f"Successfully applied {filepath}")
    except Exception as e:
        print(f"Error applying {filepath}: {e}")
        # If it fails, maybe try splitting?
        # But for now let's just report error.
        raise e

async def create_database_if_not_exists():
    print(f"Connecting to {DB_HOST} as {DB_USER} to check database '{DB_NAME}'...")
    try:
        # Connect to default 'postgres' database to create new database
        conn = await asyncpg.connect(user=DB_USER, password=DB_PASSWORD, database='postgres', host=DB_HOST)
        
        # Check if database exists
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", DB_NAME)
        if not exists:
            print(f"Database '{DB_NAME}' does not exist. Creating it...")
            # Close connection to allow CREATE DATABASE (cannot run in transaction)
            await conn.close()
            
            # Reconnect with autocommit for CREATE DATABASE
            # asyncpg doesn't support autocommit in the same way as psycopg2, 
            # but we can execute it if we are not in a transaction block.
            # Actually asyncpg connection is not in transaction by default unless .transaction() is used.
            # But CREATE DATABASE cannot run inside a transaction block.
            # asyncpg.connect returns a connection.
            
            # We need to use a separate connection for CREATE DATABASE
            sys_conn = await asyncpg.connect(user=DB_USER, password=DB_PASSWORD, database='postgres', host=DB_HOST)
            try:
                await sys_conn.execute(f'CREATE DATABASE "{DB_NAME}"')
                print(f"Database '{DB_NAME}' created successfully.")
                await sys_conn.execute(f'GRANT ALL PRIVILEGES ON DATABASE "{DB_NAME}" TO "{DB_USER}"')
            except Exception as e:
                print(f"Failed to create database: {e}")
            finally:
                await sys_conn.close()
        else:
            print(f"Database '{DB_NAME}' already exists.")
            # Ensure permissions even if it exists
            sys_conn = await asyncpg.connect(user=DB_USER, password=DB_PASSWORD, database='postgres', host=DB_HOST)
            try:
                await sys_conn.execute(f'GRANT ALL PRIVILEGES ON DATABASE "{DB_NAME}" TO "{DB_USER}"')
                print(f"Granted permissions on '{DB_NAME}' to '{DB_USER}'.")
            except Exception as e:
                print(f"Failed to grant permissions: {e}")
            finally:
                await sys_conn.close()
            await conn.close()
            
    except Exception as e:
        print(f"Error checking/creating database: {e}")

async def main():
    if not DB_PASSWORD:
        print("Error: DB_PASSWORD not found in environment.")
        sys.exit(1)

    # Ensure target database exists
    await create_database_if_not_exists()

    print(f"Connecting to {DB_HOST}/{DB_NAME} as {DB_USER}...")
    try:
        conn = await asyncpg.connect(user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST)
    except Exception as e:
        print(f"Failed to connect to database '{DB_NAME}': {e}")
        print("Please ensure the AlloyDB Auth Proxy is running and the database exists.")
        return

    try:
        # 1. Apply Schema
        setup_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'alloydb artefacts', 'alloydb_setup.sql')
        await apply_sql_file(conn, setup_file)

        # 2. Apply Data
        data_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'alloydb artefacts', '100 _sample records.sql')
        await apply_sql_file(conn, data_file)
        
        # 3. Apply Indexes
        index_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'alloydb artefacts', 'create_indexes.sql')
        await apply_sql_file(conn, index_file)
        
        # 4. Verify
        count = await conn.fetchval("SELECT count(*) FROM property_listings")
        print(f"Total records in property_listings: {count}")
        
        sample = await conn.fetchrow("SELECT city, canton, country FROM property_listings LIMIT 1")
        print(f"Sample record: {sample}")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
