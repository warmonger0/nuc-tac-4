from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Query as QueryParam
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from datetime import datetime
import os
import sqlite3
import traceback
from typing import Optional
from dotenv import load_dotenv
import logging
import sys

# Load .env file from server directory
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Create logger for this module
logger = logging.getLogger(__name__)

from core.data_models import (
    FileUploadResponse,
    QueryRequest,
    QueryResponse,
    DatabaseSchemaResponse,
    InsightsRequest,
    InsightsResponse,
    HealthCheckResponse,
    TableSchema,
    ColumnInfo,
    ImageUploadResponse,
    ImageMetadata,
    ImageListResponse,
    FolderCreateRequest,
    FolderData,
    FolderListResponse,
    FolderUpdateRequest
)

# Import core modules (to be implemented)
from core.file_processor import convert_csv_to_sqlite, convert_json_to_sqlite
from core.llm_processor import generate_sql
from core.sql_processor import execute_sql_safely, get_database_schema
from core.insights import generate_insights
from core.sql_security import (
    execute_query_safely,
    validate_identifier,
    check_table_exists,
    SQLSecurityError
)
from core.image_processor import (
    process_image_upload,
    save_image_to_db,
    get_image_by_id,
    list_images_by_folder,
    delete_image,
    create_folder,
    list_all_folders,
    rename_folder,
    delete_folder,
    get_folder_by_id,
    ImageProcessorError
)
from core.image_security import ImageSecurityError

app = FastAPI(
    title="Natural Language SQL Interface",
    description="Convert natural language to SQL queries",
    version="1.0.0"
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global app state
app_start_time = datetime.now()

# Ensure database directory exists
os.makedirs("db", exist_ok=True)

# Initialize image database tables on startup
def initialize_image_tables():
    """Create image tables if they don't exist"""
    try:
        conn = sqlite3.connect("db/database.db")

        # Create image_folders table
        execute_query_safely(
            conn,
            """
            CREATE TABLE IF NOT EXISTS image_folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            allow_ddl=True
        )

        # Create image_files table with foreign key to folders
        execute_query_safely(
            conn,
            """
            CREATE TABLE IF NOT EXISTS image_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                original_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                folder_id INTEGER,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                binary_data BLOB NOT NULL,
                FOREIGN KEY (folder_id) REFERENCES image_folders(id)
            )
            """,
            allow_ddl=True
        )

        # Create index on folder_id for efficient queries
        execute_query_safely(
            conn,
            """
            CREATE INDEX IF NOT EXISTS idx_image_files_folder_id
            ON image_files(folder_id)
            """,
            allow_ddl=True
        )

        conn.commit()
        conn.close()
        logger.info("[SUCCESS] Image database tables initialized")
    except Exception as e:
        logger.error(f"[ERROR] Failed to initialize image tables: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")

# Initialize image tables on startup
initialize_image_tables()

@app.post("/api/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)) -> FileUploadResponse:
    """Upload and convert .json or .csv file to SQLite table"""
    try:
        # Validate file type
        if not file.filename.endswith(('.csv', '.json')):
            raise HTTPException(400, "Only .csv and .json files are supported")
        
        # Generate table name from filename
        table_name = file.filename.rsplit('.', 1)[0].lower().replace(' ', '_')
        
        # Read file content
        content = await file.read()
        
        # Convert to SQLite based on file type
        if file.filename.endswith('.csv'):
            result = convert_csv_to_sqlite(content, table_name)
        else:
            result = convert_json_to_sqlite(content, table_name)
        
        response = FileUploadResponse(
            table_name=result['table_name'],
            table_schema=result['schema'],
            row_count=result['row_count'],
            sample_data=result['sample_data']
        )
        logger.info(f"[SUCCESS] File upload: {response}")
        return response
    except Exception as e:
        logger.error(f"[ERROR] File upload failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        return FileUploadResponse(
            table_name="",
            table_schema={},
            row_count=0,
            sample_data=[],
            error=str(e)
        )

@app.post("/api/query", response_model=QueryResponse)
async def process_natural_language_query(request: QueryRequest) -> QueryResponse:
    """Process natural language query and return SQL results"""
    try:
        # Get database schema
        schema_info = get_database_schema()
        
        # Generate SQL using routing logic
        sql = generate_sql(request, schema_info)
        
        # Execute SQL query
        start_time = datetime.now()
        result = execute_sql_safely(sql)
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        if result['error']:
            raise Exception(result['error'])
        
        response = QueryResponse(
            sql=sql,
            results=result['results'],
            columns=result['columns'],
            row_count=len(result['results']),
            execution_time_ms=execution_time
        )
        logger.info(f"[SUCCESS] Query processed: SQL={sql}, rows={len(result['results'])}, time={execution_time}ms")
        return response
    except Exception as e:
        logger.error(f"[ERROR] Query processing failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        return QueryResponse(
            sql="",
            results=[],
            columns=[],
            row_count=0,
            execution_time_ms=0,
            error=str(e)
        )

@app.get("/api/schema", response_model=DatabaseSchemaResponse)
async def get_database_schema_endpoint() -> DatabaseSchemaResponse:
    """Get current database schema and table information"""
    try:
        schema = get_database_schema()
        tables = []
        
        for table_name, table_info in schema['tables'].items():
            columns = []
            for col_name, col_type in table_info['columns'].items():
                columns.append(ColumnInfo(
                    name=col_name,
                    type=col_type,
                    nullable=True,
                    primary_key=False
                ))
            
            tables.append(TableSchema(
                name=table_name,
                columns=columns,
                row_count=table_info.get('row_count', 0),
                created_at=datetime.now()  # Simplified for v1
            ))
        
        response = DatabaseSchemaResponse(
            tables=tables,
            total_tables=len(tables)
        )
        logger.info(f"[SUCCESS] Schema retrieved: {len(tables)} tables")
        return response
    except Exception as e:
        logger.error(f"[ERROR] Schema retrieval failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        return DatabaseSchemaResponse(
            tables=[],
            total_tables=0,
            error=str(e)
        )

@app.post("/api/insights", response_model=InsightsResponse)
async def generate_insights_endpoint(request: InsightsRequest) -> InsightsResponse:
    """Generate statistical insights for table columns"""
    try:
        insights = generate_insights(request.table_name, request.column_names)
        response = InsightsResponse(
            table_name=request.table_name,
            insights=insights,
            generated_at=datetime.now()
        )
        logger.info(f"[SUCCESS] Insights generated for table: {request.table_name}, insights count: {len(insights)}")
        return response
    except Exception as e:
        logger.error(f"[ERROR] Insights generation failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        return InsightsResponse(
            table_name=request.table_name,
            insights=[],
            generated_at=datetime.now(),
            error=str(e)
        )

@app.get("/api/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """Health check endpoint with database status"""
    try:
        # Check database connection
        conn = sqlite3.connect("db/database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        conn.close()
        
        uptime = (datetime.now() - app_start_time).total_seconds()
        
        response = HealthCheckResponse(
            status="ok",
            database_connected=True,
            tables_count=len(tables),
            uptime_seconds=uptime
        )
        logger.info(f"[SUCCESS] Health check: OK, {len(tables)} tables, uptime: {uptime}s")
        return response
    except Exception as e:
        logger.error(f"[ERROR] Health check failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        return HealthCheckResponse(
            status="error",
            database_connected=False,
            tables_count=0,
            uptime_seconds=0
        )

@app.delete("/api/table/{table_name}")
async def delete_table(table_name: str):
    """Delete a table from the database"""
    try:
        # Validate table name using security module
        try:
            validate_identifier(table_name, "table")
        except SQLSecurityError as e:
            raise HTTPException(400, str(e))
        
        conn = sqlite3.connect("db/database.db")
        
        # Check if table exists using secure method
        if not check_table_exists(conn, table_name):
            conn.close()
            raise HTTPException(404, f"Table '{table_name}' not found")
        
        # Drop the table using safe query execution with DDL permission
        execute_query_safely(
            conn,
            "DROP TABLE IF EXISTS {table}",
            identifier_params={'table': table_name},
            allow_ddl=True
        )
        conn.commit()
        conn.close()
        
        response = {"message": f"Table '{table_name}' deleted successfully"}
        logger.info(f"[SUCCESS] Table deleted: {table_name}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Table deletion failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(500, f"Error deleting table: {str(e)}")

# Image Upload Endpoints

@app.post("/api/images/upload", response_model=ImageUploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    folder_id: Optional[int] = Form(None)
) -> ImageUploadResponse:
    """Upload an image file to the database"""
    try:
        # Read file content
        content = await file.read()

        # Process image
        processed_image = process_image_upload(
            content,
            file.filename,
            folder_id
        )

        # Save to database
        conn = sqlite3.connect("db/database.db")
        image_id = save_image_to_db(conn, processed_image)
        conn.close()

        # Get folder name if folder_id provided
        folder_name = None
        if folder_id:
            conn = sqlite3.connect("db/database.db")
            folder = get_folder_by_id(conn, folder_id)
            conn.close()
            if folder:
                folder_name = folder['folder_name']

        response = ImageUploadResponse(
            image_id=image_id,
            filename=processed_image['filename'],
            file_type=processed_image['file_type'],
            file_size=processed_image['file_size'],
            folder_name=folder_name
        )
        logger.info(f"[SUCCESS] Image uploaded: {response}")
        return response

    except (ImageSecurityError, ImageProcessorError) as e:
        logger.error(f"[ERROR] Image upload failed: {str(e)}")
        return ImageUploadResponse(error=str(e))
    except Exception as e:
        logger.error(f"[ERROR] Image upload failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        return ImageUploadResponse(error=f"Unexpected error: {str(e)}")


@app.get("/api/images", response_model=ImageListResponse)
async def list_images(
    folder_id: Optional[int] = QueryParam(None),
    limit: int = QueryParam(100),
    offset: int = QueryParam(0)
) -> ImageListResponse:
    """List images, optionally filtered by folder"""
    try:
        conn = sqlite3.connect("db/database.db")
        images = list_images_by_folder(conn, folder_id, limit, offset)

        # Get total count
        if folder_id is not None:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM image_files WHERE folder_id = ?",
                (folder_id,)
            )
            total_count = cursor.fetchone()[0]
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM image_files")
            total_count = cursor.fetchone()[0]

        conn.close()

        # Convert to ImageMetadata objects
        image_metadata = [
            ImageMetadata(
                id=img['id'],
                filename=img['filename'],
                original_name=img['original_name'],
                file_type=img['file_type'],
                file_size=img['file_size'],
                folder_id=img['folder_id'],
                folder_name=img.get('folder_name'),
                upload_date=img['upload_date']
            )
            for img in images
        ]

        response = ImageListResponse(
            images=image_metadata,
            total_count=total_count
        )
        logger.info(f"[SUCCESS] Listed {len(images)} images")
        return response

    except Exception as e:
        logger.error(f"[ERROR] Image listing failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        return ImageListResponse(images=[], total_count=0, error=str(e))


@app.get("/api/images/{image_id}")
async def get_image(image_id: int):
    """Retrieve image binary data"""
    try:
        conn = sqlite3.connect("db/database.db")
        image_data = get_image_by_id(conn, image_id)
        conn.close()

        if not image_data:
            raise HTTPException(404, f"Image with ID {image_id} not found")

        # Determine content type
        content_type_map = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'bmp': 'image/bmp',
            'webp': 'image/webp'
        }

        content_type = content_type_map.get(
            image_data['file_type'],
            'application/octet-stream'
        )

        logger.info(f"[SUCCESS] Image retrieved: ID={image_id}")
        return Response(
            content=image_data['binary_data'],
            media_type=content_type,
            headers={
                'Content-Disposition': f'inline; filename="{image_data["original_name"]}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Image retrieval failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(500, f"Error retrieving image: {str(e)}")


@app.delete("/api/images/{image_id}")
async def delete_image_endpoint(image_id: int):
    """Delete an image"""
    try:
        conn = sqlite3.connect("db/database.db")
        success = delete_image(conn, image_id)
        conn.close()

        if not success:
            raise HTTPException(404, f"Image with ID {image_id} not found")

        response = {"message": f"Image {image_id} deleted successfully"}
        logger.info(f"[SUCCESS] Image deleted: ID={image_id}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Image deletion failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(500, f"Error deleting image: {str(e)}")


# Folder Management Endpoints

@app.post("/api/images/folders", response_model=FolderData)
async def create_folder_endpoint(request: FolderCreateRequest):
    """Create a new folder"""
    try:
        conn = sqlite3.connect("db/database.db")
        folder_id = create_folder(conn, request.folder_name)

        # Get the created folder
        folder = get_folder_by_id(conn, folder_id)
        conn.close()

        if not folder:
            raise HTTPException(500, "Folder created but could not be retrieved")

        response = FolderData(
            id=folder['id'],
            folder_name=folder['folder_name'],
            image_count=0,
            created_at=folder['created_at'],
            updated_at=folder['updated_at']
        )
        logger.info(f"[SUCCESS] Folder created: {response}")
        return response

    except ImageProcessorError as e:
        logger.error(f"[ERROR] Folder creation failed: {str(e)}")
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"[ERROR] Folder creation failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(500, f"Error creating folder: {str(e)}")


@app.get("/api/images/folders", response_model=FolderListResponse)
async def list_folders_endpoint() -> FolderListResponse:
    """List all folders with image counts"""
    try:
        conn = sqlite3.connect("db/database.db")
        folders = list_all_folders(conn)
        conn.close()

        folder_data = [
            FolderData(
                id=f['id'],
                folder_name=f['folder_name'],
                image_count=f['image_count'],
                created_at=f['created_at'],
                updated_at=f['updated_at']
            )
            for f in folders
        ]

        response = FolderListResponse(folders=folder_data)
        logger.info(f"[SUCCESS] Listed {len(folders)} folders")
        return response

    except Exception as e:
        logger.error(f"[ERROR] Folder listing failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        return FolderListResponse(folders=[], error=str(e))


@app.put("/api/images/folders/{folder_id}")
async def rename_folder_endpoint(folder_id: int, request: FolderUpdateRequest):
    """Rename a folder"""
    try:
        conn = sqlite3.connect("db/database.db")
        success = rename_folder(conn, folder_id, request.new_folder_name)
        conn.close()

        if not success:
            raise HTTPException(404, f"Folder with ID {folder_id} not found")

        response = {"message": f"Folder {folder_id} renamed to '{request.new_folder_name}'"}
        logger.info(f"[SUCCESS] Folder renamed: ID={folder_id}")
        return response

    except ImageProcessorError as e:
        logger.error(f"[ERROR] Folder rename failed: {str(e)}")
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"[ERROR] Folder rename failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(500, f"Error renaming folder: {str(e)}")


@app.delete("/api/images/folders/{folder_id}")
async def delete_folder_endpoint(folder_id: int):
    """Delete a folder (only if it contains no images)"""
    try:
        conn = sqlite3.connect("db/database.db")
        success = delete_folder(conn, folder_id)
        conn.close()

        if not success:
            raise HTTPException(404, f"Folder with ID {folder_id} not found")

        response = {"message": f"Folder {folder_id} deleted successfully"}
        logger.info(f"[SUCCESS] Folder deleted: ID={folder_id}")
        return response

    except ImageProcessorError as e:
        logger.error(f"[ERROR] Folder deletion failed: {str(e)}")
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"[ERROR] Folder deletion failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(500, f"Error deleting folder: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)