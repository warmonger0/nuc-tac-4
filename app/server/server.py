from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
    ImageListResponse,
    FolderRequest,
    FolderRenameRequest,
    FolderResponse,
    FolderOperationResponse,
    DuplicateCheckResponse,
    DuplicateMatch,
    FolderListResponse,
    FolderStats
)

# Import core modules (to be implemented)
from core.file_processor import convert_csv_to_sqlite, convert_json_to_sqlite, convert_jsonl_to_sqlite
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
    initialize_image_database,
    validate_image_format,
    save_image_to_disk,
    save_image_metadata,
    get_images,
    get_image_by_id,
    delete_image,
    create_folder,
    get_folders,
    rename_folder,
    delete_folder,
    sanitize_folder_name,
    check_for_duplicates,
    get_folder_statistics
)
from core import image_hasher
from core.data_models import ImageMetadata
import uuid
from pathlib import Path
from fastapi.responses import FileResponse
from typing import List

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

@app.post("/api/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)) -> FileUploadResponse:
    """Upload and convert .json, .jsonl, or .csv file to SQLite table"""
    try:
        # Validate file type
        if not file.filename.endswith(('.csv', '.json', '.jsonl')):
            raise HTTPException(400, "Only .csv, .json, and .jsonl files are supported")

        # Generate table name from filename
        table_name = file.filename.rsplit('.', 1)[0].lower().replace(' ', '_')

        # Read file content
        content = await file.read()

        # Convert to SQLite based on file type
        if file.filename.endswith('.csv'):
            result = convert_csv_to_sqlite(content, table_name)
        elif file.filename.endswith('.jsonl'):
            result = convert_jsonl_to_sqlite(content, table_name)
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

# ============================================
# Image Upload Endpoints
# ============================================

@app.on_event("startup")
async def startup_event():
    """Initialize image database on startup"""
    try:
        conn = sqlite3.connect("db/database.db")
        initialize_image_database(conn)
        conn.close()
        logger.info("[SUCCESS] Image database initialized")
    except Exception as e:
        logger.error(f"[ERROR] Failed to initialize image database: {str(e)}")

@app.post("/api/images/upload", response_model=List[ImageUploadResponse])
async def upload_images(
    files: List[UploadFile] = File(...),
    folder: str = "default"
) -> List[ImageUploadResponse]:
    """Upload multiple images to a folder"""
    responses = []

    for file in files:
        try:
            # Validate image format
            if not validate_image_format(file.filename):
                responses.append(ImageUploadResponse(
                    image_id="",
                    filename=file.filename,
                    folder=folder,
                    size=0,
                    format="",
                    url="",
                    error=f"Unsupported file format. Supported formats: PNG, JPG, JPEG, GIF, WebP, BMP"
                ))
                continue

            # Read file data
            file_data = await file.read()
            file_size = len(file_data)

            # Sanitize folder name
            folder_sanitized = sanitize_folder_name(folder)

            # Save to disk
            file_path = save_image_to_disk(file_data, folder_sanitized, file.filename)

            # Generate image metadata
            image_id = str(uuid.uuid4())
            file_ext = Path(file.filename).suffix.lower().lstrip('.')

            metadata = ImageMetadata(
                image_id=image_id,
                filename=file.filename,
                folder=folder_sanitized,
                size=file_size,
                format=file_ext,
                created_at=datetime.now(),
                file_path=file_path
            )

            # Compute perceptual hash
            phash = None
            try:
                phash = image_hasher.compute_phash(file_data)
            except Exception as e:
                logger.warning(f"[WARNING] Failed to compute hash for {file.filename}: {str(e)}")

            # Save metadata to database with hash
            conn = sqlite3.connect("db/database.db")
            save_image_metadata(conn, metadata, phash)
            conn.close()

            # Create response
            responses.append(ImageUploadResponse(
                image_id=image_id,
                filename=file.filename,
                folder=folder_sanitized,
                size=file_size,
                format=file_ext,
                url=f"/api/images/{image_id}"
            ))

            logger.info(f"[SUCCESS] Image uploaded: {file.filename} to folder '{folder_sanitized}'")

        except Exception as e:
            logger.error(f"[ERROR] Image upload failed for {file.filename}: {str(e)}")
            responses.append(ImageUploadResponse(
                image_id="",
                filename=file.filename,
                folder=folder,
                size=0,
                format="",
                url="",
                error=str(e)
            ))

    return responses

@app.get("/api/images", response_model=ImageListResponse)
async def list_images(folder: Optional[str] = None) -> ImageListResponse:
    """Get list of all images, optionally filtered by folder"""
    try:
        conn = sqlite3.connect("db/database.db")
        images = get_images(conn, folder)
        conn.close()

        response = ImageListResponse(
            images=images,
            total_count=len(images)
        )
        logger.info(f"[SUCCESS] Images retrieved: {len(images)} images")
        return response
    except Exception as e:
        logger.error(f"[ERROR] Failed to retrieve images: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        return ImageListResponse(
            images=[],
            total_count=0,
            error=str(e)
        )

@app.get("/api/images/{image_id}")
async def get_image(image_id: str):
    """Get a specific image file"""
    try:
        conn = sqlite3.connect("db/database.db")
        image = get_image_by_id(conn, image_id)
        conn.close()

        if not image:
            raise HTTPException(404, f"Image with ID '{image_id}' not found")

        file_path = Path(image.file_path)
        if not file_path.exists():
            raise HTTPException(404, f"Image file not found on disk")

        logger.info(f"[SUCCESS] Image retrieved: {image_id}")
        return FileResponse(
            path=str(file_path),
            media_type=f"image/{image.format}",
            filename=image.filename
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to retrieve image {image_id}: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(500, f"Error retrieving image: {str(e)}")

@app.delete("/api/images/{image_id}")
async def delete_image_endpoint(image_id: str):
    """Delete an image"""
    try:
        conn = sqlite3.connect("db/database.db")
        success = delete_image(conn, image_id)
        conn.close()

        if not success:
            raise HTTPException(404, f"Image with ID '{image_id}' not found")

        response = {"message": f"Image '{image_id}' deleted successfully"}
        logger.info(f"[SUCCESS] Image deleted: {image_id}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to delete image {image_id}: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(500, f"Error deleting image: {str(e)}")

@app.post("/api/images/check-duplicate", response_model=DuplicateCheckResponse)
async def check_duplicate(
    file: UploadFile = File(...),
    folder: str = "default"
) -> DuplicateCheckResponse:
    """Check if an image is a duplicate before uploading"""
    try:
        # Validate image format
        if not validate_image_format(file.filename):
            return DuplicateCheckResponse(
                is_duplicate=False,
                matches=[],
                error=f"Unsupported file format. Supported formats: PNG, JPG, JPEG, GIF, WebP, BMP"
            )

        # Read file data
        file_data = await file.read()

        # Sanitize folder name
        folder_sanitized = sanitize_folder_name(folder)

        # Check for duplicates
        conn = sqlite3.connect("db/database.db")
        duplicates = check_for_duplicates(conn, file_data, folder_sanitized, file.filename)
        conn.close()

        # Convert to response format
        matches = [
            DuplicateMatch(
                image_id=d['image_id'],
                filename=d['filename'],
                folder=d['folder'],
                similarity=d['similarity'],
                phash=d.get('phash'),
                match_type=d['match_type']
            )
            for d in duplicates
        ]

        response = DuplicateCheckResponse(
            is_duplicate=len(matches) > 0,
            matches=matches
        )

        logger.info(f"[SUCCESS] Duplicate check for {file.filename}: {len(matches)} matches found")
        return response

    except Exception as e:
        logger.error(f"[ERROR] Duplicate check failed for {file.filename}: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        return DuplicateCheckResponse(
            is_duplicate=False,
            matches=[],
            error=str(e)
        )

# ============================================
# Folder Management Endpoints
# ============================================

@app.get("/api/folders", response_model=FolderListResponse)
async def list_folders() -> FolderListResponse:
    """Get list of all folders with statistics"""
    try:
        conn = sqlite3.connect("db/database.db")
        folder_stats = get_folder_statistics(conn)
        conn.close()

        # Convert to response format
        folders = [
            FolderStats(
                name=stat['name'],
                image_count=stat['image_count'],
                total_size=stat['total_size'],
                created_at=stat['created_at']
            )
            for stat in folder_stats
        ]

        response = FolderListResponse(
            folders=folders,
            total_folders=len(folders)
        )
        logger.info(f"[SUCCESS] Folders retrieved: {len(folders)} folders")
        return response
    except Exception as e:
        logger.error(f"[ERROR] Failed to retrieve folders: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        return FolderListResponse(
            folders=[],
            total_folders=0,
            error=str(e)
        )

@app.post("/api/folders", response_model=FolderOperationResponse)
async def create_folder_endpoint(request: FolderRequest) -> FolderOperationResponse:
    """Create a new folder"""
    try:
        conn = sqlite3.connect("db/database.db")
        success, message = create_folder(conn, request.folder_name)
        conn.close()

        if success:
            logger.info(f"[SUCCESS] Folder created: {request.folder_name}")
        else:
            logger.warning(f"[WARNING] Folder creation failed: {message}")

        return FolderOperationResponse(
            success=success,
            message=message,
            error=None if success else message
        )
    except Exception as e:
        logger.error(f"[ERROR] Failed to create folder: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        return FolderOperationResponse(
            success=False,
            message="",
            error=str(e)
        )

@app.put("/api/folders/{folder_name}", response_model=FolderOperationResponse)
async def rename_folder_endpoint(
    folder_name: str,
    request: FolderRenameRequest
) -> FolderOperationResponse:
    """Rename a folder"""
    try:
        conn = sqlite3.connect("db/database.db")
        success, message = rename_folder(conn, request.old_name, request.new_name)
        conn.close()

        if success:
            logger.info(f"[SUCCESS] Folder renamed: {request.old_name} -> {request.new_name}")
        else:
            logger.warning(f"[WARNING] Folder rename failed: {message}")

        return FolderOperationResponse(
            success=success,
            message=message,
            error=None if success else message
        )
    except Exception as e:
        logger.error(f"[ERROR] Failed to rename folder: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        return FolderOperationResponse(
            success=False,
            message="",
            error=str(e)
        )

@app.delete("/api/folders/{folder_name}", response_model=FolderOperationResponse)
async def delete_folder_endpoint(folder_name: str) -> FolderOperationResponse:
    """Delete a folder"""
    try:
        conn = sqlite3.connect("db/database.db")
        success, message = delete_folder(conn, folder_name)
        conn.close()

        if success:
            logger.info(f"[SUCCESS] Folder deleted: {folder_name}")
        else:
            logger.warning(f"[WARNING] Folder deletion failed: {message}")

        return FolderOperationResponse(
            success=success,
            message=message,
            error=None if success else message
        )
    except Exception as e:
        logger.error(f"[ERROR] Failed to delete folder: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        return FolderOperationResponse(
            success=False,
            message="",
            error=str(e)
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)