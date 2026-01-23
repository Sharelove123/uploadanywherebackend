import os
import django
from django.db import connection

import dotenv
dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def list_schemas_and_tables():
    with connection.cursor() as cursor:
        # 1. List all schemas
        cursor.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')")
        schemas = [row[0] for row in cursor.fetchall()]
        
        print(f"\nFound {len(schemas)} Schemas:")
        print("-" * 50)
        
        for schema in schemas:
            print(f"\n[SCHEMA]: {schema}")
            
            # 2. List tables in this schema
            cursor.execute(f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema}'")
            tables = [row[0] for row in cursor.fetchall()]
            
            if not tables:
                 print("   (No tables)")
            else:
                # Group by app prefix for readability
                print(f"   found {len(tables)} tables, including:")
                for table in sorted(tables)[:10]: # Just show first 10
                    print(f"   - {table}")
                if len(tables) > 10:
                    print(f"   ... and {len(tables)-10} more")

if __name__ == '__main__':
    list_schemas_and_tables()
