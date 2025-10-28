# Feature: Host Image Database with Upload Interface

## Feature Description
A comprehensive image management system that allows users to upload, organize, and store image files in a database. The feature includes a dedicated upload interface embedded in the application with support for multiple image file formats, drag-and-drop functionality, folder organization, and visual feedback on supported file types. Users can create, rename, and delete folders to organize their image uploads into logical groupings. The system will use only standard libraries already available in the project (FastAPI, SQLite, TypeScript) without introducing new dependencies.

## User Story
As a user
I want to upload and organize image files into folders
So that I can manage my image assets in a structured way and easily retrieve them when needed

## Problem Statement
Currently, the application focuses on data table management (CSV/JSON files) but lacks functionality for managing image assets. Users need the ability to store image files alongside their data, organize them into logical groupings (folders), and have visibility into what file types are supported. Without a dedicated image database and upload interface, users cannot leverage the application for projects that require both data and image asset management.

## Solution Statement
Implement a complete image upload and management system with:
1. A SQLite database schema to store image metadata and binary data with folder organization
2. An intuitive upload interface embedded in the page with drag-and-drop support and multi-file selection
3. Clear UI indicators showing supported image file types (PNG, JPG, JPEG, GIF, BMP, WebP)
4. Folder management with dropdown selection, creation, renaming, and deletion capabilities
5. Backend API endpoints for image upload, retrieval, folder management, and file validation
6. Secure file handling with validation, size limits, and SQL injection protection
7. Test assets including sample images in different formats for comprehensive testing

## Relevant Files
Use these files to implement the feature:

**Server-side files:**
- `app/server/server.py` - Main FastAPI server file. Add new API endpoints for image upload, retrieval, folder management, and image listing. Follows existing patterns for `/api/upload`, `/api/query`, etc.
- `app/server/core/data_models.py` - Pydantic models for request/response validation. Add models for image upload requests/responses, folder operations, and image metadata.
- `app/server/core/sql_security.py` - SQL security utilities. Use existing functions like `validate_identifier()`, `execute_query_safely()` to ensure secure database operations for image metadata and folder names.
- `app/server/core/file_processor.py` - File processing utilities. Add image validation functions, binary data handling, and image metadata extraction using existing patterns from CSV/JSON processing.
- `app/server/pyproject.toml` - Project dependencies. Verify that existing libraries (fastapi, sqlite3, python-multipart) are sufficient; no new dependencies should be needed.

**Client-side files:**
- `app/client/index.html` - Main HTML structure. Add new section for "Image Upload" with upload panel, drag-and-drop zone, folder dropdown, and file type indicators. Follow existing modal pattern.
- `app/client/src/main.ts` - Main TypeScript file. Add image upload functionality, folder management UI logic, drag-and-drop handlers, and API integration following existing patterns from file upload.
- `app/client/src/api/client.ts` - API client wrapper. Add methods for image upload, folder operations, and image retrieval following existing API method patterns.
- `app/client/src/types.d.ts` - TypeScript type definitions. Add interfaces for image upload responses, folder data, and image metadata matching Pydantic models.
- `app/client/src/style.css` - Styling. Add CSS for image upload panel, drag-and-drop visual states, folder dropdown, and file type badges following existing design system.

**Test files:**
- `app/server/tests/core/test_image_processor.py` - New test file for image processing functions, validation, and metadata extraction
- `app/server/tests/test_image_upload.py` - New test file for image upload API endpoints and security validation
- `app/server/tests/assets/` - Test assets directory. Add sample images in different formats (PNG, JPG, GIF, BMP, WebP) for upload testing

### New Files
- `app/server/core/image_processor.py` - New module for image-specific processing: validation, binary storage, metadata extraction, thumbnail generation (optional), and folder management
- `app/server/core/image_security.py` - New module for image-specific security: file type validation, magic number verification, size limits, and malicious file detection
- `app/client/src/imageUpload.ts` - New module for image upload UI management: drag-and-drop, multi-file handling, progress indicators, and folder selection UI

## Implementation Plan
### Phase 1: Foundation
Create the database schema for storing image metadata and binary data with folder organization. Implement core data models and security validations for image handling. Set up the basic backend infrastructure for image storage using SQLite BLOB fields. Establish file validation patterns and size limit constraints.

### Phase 2: Core Implementation
Develop the backend API endpoints for image upload, retrieval, and folder management. Implement image processing functions for validation, storage, and metadata extraction. Build the frontend upload interface with drag-and-drop support, multi-file selection, and folder management UI. Create comprehensive validation for supported file types.

### Phase 3: Integration
Connect frontend and backend components. Integrate folder management with the upload flow. Add visual feedback for upload progress, success, and errors. Implement test assets and comprehensive test coverage. Ensure security validations are properly integrated throughout the system.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### Create Database Schema and Migration
- Design SQLite schema with two tables: `image_files` (id, filename, original_name, file_type, file_size, folder_id, upload_date, binary_data) and `image_folders` (id, folder_name, created_at, updated_at)
- Add migration logic in `server.py` startup to create tables if they don't exist (similar to existing database initialization)
- Create indexes on folder_id for efficient folder-based queries
- Add NOT NULL constraints on required fields and UNIQUE constraint on folder_name
- Write SQL using `execute_query_safely()` with `allow_ddl=True` to ensure secure table creation

### Create Data Models
- Add `ImageUploadRequest` Pydantic model in `data_models.py` with fields: folder_id (optional), allowed_types validation
- Add `ImageUploadResponse` model with fields: image_id, filename, file_type, file_size, folder_name, thumbnail_url (optional), error (optional)
- Add `FolderCreateRequest` model with field: folder_name (with validation)
- Add `FolderListResponse` model with fields: folders (list of folder objects with id, name, image_count), error (optional)
- Add `FolderUpdateRequest` model with fields: folder_id, new_folder_name
- Add `ImageListResponse` model with fields: images (list of image metadata), total_count, error (optional)
- Add validation for folder names using regex pattern similar to table name validation

### Create Image Security Module
- Create `app/server/core/image_security.py` with function `validate_image_file()` that checks file extension and magic numbers
- Implement `ALLOWED_EXTENSIONS` constant: png, jpg, jpeg, gif, bmp, webp
- Implement `MAGIC_NUMBERS` dictionary mapping file types to their magic number signatures
- Add `check_file_size()` function with configurable limit (default 10MB)
- Add `sanitize_filename()` function to prevent path traversal and malicious filenames
- Implement `detect_malicious_content()` basic checks (e.g., embedded scripts in SVG - though SVG won't be supported initially)
- Write unit tests for all validation functions with valid and invalid inputs

### Create Image Processor Module
- Create `app/server/core/image_processor.py` with function `process_image_upload()` to handle binary data storage
- Implement `extract_metadata()` function to get dimensions, format, and file info using Python's built-in `imghdr` module
- Add `save_image_to_db()` function that inserts image binary data and metadata into SQLite using `execute_query_safely()`
- Implement `get_image_by_id()` function to retrieve image binary data from database
- Add `list_images_by_folder()` function with optional folder_id parameter
- Implement folder management functions: `create_folder()`, `rename_folder()`, `delete_folder()`, `get_folder_by_id()`, `list_all_folders()`
- Ensure all database operations use `validate_identifier()` and `execute_query_safely()` from sql_security module
- Add comprehensive error handling and logging following existing patterns

### Add Image Upload API Endpoint
- Add `POST /api/images/upload` endpoint in `server.py` accepting multipart/form-data with file and optional folder_id
- Validate uploaded file using `validate_image_file()` from image_security module
- Process image and extract metadata using `process_image_upload()` from image_processor module
- Save to database with folder association
- Return `ImageUploadResponse` with metadata and success/error status
- Add proper error handling for invalid files, oversized files, and database errors
- Log all operations following existing logging patterns

### Add Folder Management API Endpoints
- Add `POST /api/images/folders` endpoint to create new folders with validation
- Add `GET /api/images/folders` endpoint to list all folders with image counts
- Add `PUT /api/images/folders/{folder_id}` endpoint to rename folders
- Add `DELETE /api/images/folders/{folder_id}` endpoint to delete folders (with check for existing images)
- Add proper SQL injection protection using `validate_identifier()` for folder names
- Implement proper error responses for duplicate folder names, non-existent folders, etc.
- Add logging for all folder operations

### Add Image Retrieval API Endpoints
- Add `GET /api/images` endpoint to list images with optional folder_id query parameter
- Add `GET /api/images/{image_id}` endpoint to retrieve specific image binary data with proper Content-Type header
- Add `DELETE /api/images/{image_id}` endpoint to delete images
- Implement pagination for image listing (limit, offset parameters)
- Add proper CORS headers for image serving
- Ensure secure retrieval with validation of image_id to prevent SQL injection

### Create TypeScript Types
- Add interfaces in `types.d.ts`: `ImageUploadResponse`, `ImageMetadata`, `FolderData`, `FolderListResponse`, `ImageListResponse`
- Ensure interfaces exactly match Pydantic models on backend
- Add type definitions for form data structures
- Include error field in all response types

### Create API Client Methods
- Add methods to `api/client.ts`: `uploadImage(file: File, folderId?: number)`, `listImages(folderId?: number)`, `getImage(imageId: number)`, `deleteImage(imageId: number)`
- Add folder methods: `createFolder(name: string)`, `listFolders()`, `renameFolder(folderId: number, newName: string)`, `deleteFolder(folderId: number)`
- Follow existing API patterns with proper error handling
- Use FormData for file uploads similar to existing file upload implementation

### Create Image Upload HTML Structure
- Add "Image Upload" section in `index.html` after the "Upload Data" button or as a new dedicated page section
- Create upload panel with drag-and-drop zone similar to existing file upload modal
- Add folder dropdown with options for selecting folder, creating new folder, renaming, and deleting
- Add file type indicator showing supported formats: "Supported: PNG, JPG, JPEG, GIF, BMP, WebP"
- Include multi-file input with `multiple` attribute
- Add "Browse Images" button and drag-and-drop area
- Create image gallery section to display uploaded images with thumbnails
- Follow existing modal and section styling patterns

### Create Image Upload TypeScript Module
- Create `app/client/src/imageUpload.ts` with function `initializeImageUpload()` to set up event listeners
- Implement `handleImageDragDrop()` for drag-and-drop functionality
- Add `handleMultipleImageSelection()` for multi-file browse and upload
- Implement `uploadSingleImage()` and `uploadMultipleImages()` functions
- Add `displayImageGallery()` to show uploaded images
- Implement `refreshImageList()` to reload images when folder changes
- Add visual feedback for upload progress, success, and errors
- Follow existing patterns from file upload in `main.ts`

### Create Folder Management UI
- Add dropdown component in image upload section for folder selection
- Implement `initializeFolderDropdown()` to populate folder list
- Add "+ New Folder" option that opens a prompt for folder name input
- Add "Rename Folder" option with prompt for new name
- Add "Delete Folder" option with confirmation dialog
- Update folder dropdown when folders are created, renamed, or deleted
- Store selected folder_id in component state
- Add visual indicators for active folder

### Style Image Upload Components
- Add CSS classes for image upload panel following existing design system
- Style drag-and-drop zone with hover effects and "dragover" state
- Create styles for folder dropdown with custom select styling
- Add file type badge styles with color coding for different formats
- Style image gallery grid with responsive columns
- Add upload progress indicators with loading animations
- Style folder management buttons and prompts
- Ensure mobile responsiveness for upload interface

### Integrate Upload with Main Application
- Import and initialize image upload module in `main.ts`
- Add navigation or toggle to show/hide image upload section
- Ensure state management doesn't conflict with existing data upload
- Connect folder selection changes to image list updates
- Add error handling that integrates with existing error display patterns
- Ensure upload success messages follow existing success message patterns

### Create Test Assets
- Add `app/server/tests/assets/test-image.png` (small valid PNG image)
- Add `app/server/tests/assets/test-image.jpg` (small valid JPG image)
- Add `app/server/tests/assets/test-image.gif` (small valid GIF image)
- Add `app/server/tests/assets/test-image.bmp` (small valid BMP image)
- Add `app/server/tests/assets/test-image.webp` (small valid WebP image)
- Add `app/server/tests/assets/invalid-image.txt` (text file with .txt extension for negative testing)
- Add `app/server/tests/assets/fake-image.jpg` (text file with .jpg extension for magic number validation)
- Ensure all test images are small (< 50KB) to keep repository size manageable

### Write Image Security Tests
- Create `app/server/tests/core/test_image_security.py`
- Test `validate_image_file()` with valid image types
- Test rejection of invalid file extensions
- Test magic number validation catches files with wrong extensions
- Test file size limits with oversized mock files
- Test filename sanitization prevents path traversal
- Test malicious content detection
- Ensure all tests pass with proper error messages

### Write Image Processor Tests
- Create `app/server/tests/core/test_image_processor.py`
- Test `process_image_upload()` with valid images
- Test `extract_metadata()` returns correct dimensions and format
- Test `save_image_to_db()` and `get_image_by_id()` round-trip
- Test folder CRUD operations: create, list, rename, delete
- Test folder deletion prevents deletion when images exist
- Test `list_images_by_folder()` filtering
- Test SQL injection protection in folder names
- Mock database operations where appropriate

### Write Image API Tests
- Create `app/server/tests/test_image_upload.py`
- Test POST `/api/images/upload` with valid images
- Test upload rejection for invalid file types
- Test upload with folder_id association
- Test folder creation, listing, renaming, deletion endpoints
- Test image listing with and without folder filter
- Test image retrieval returns proper binary data and Content-Type
- Test image deletion
- Test SQL injection attempts in folder names and image IDs
- Test concurrent uploads
- Ensure all security validations are tested

### Write Frontend Integration Tests
- Test drag-and-drop file selection updates file input
- Test multi-file selection triggers multiple uploads
- Test folder dropdown populates correctly
- Test folder creation, rename, delete UI flows
- Test image upload success updates gallery
- Test error messages display for invalid files
- Test upload progress indicators appear and disappear correctly
- Test folder selection changes update image list

### Add Documentation
- Update README.md with new image upload feature description
- Document supported image file types and size limits
- Add usage instructions for folder management
- Document API endpoints for image upload and management
- Add examples of programmatic image upload
- Include security considerations for image uploads

### Final Integration Testing
- Test complete upload flow: create folder, select folder, upload images, view gallery
- Test folder management: rename folder, verify images still associated, delete empty folder
- Test edge cases: upload same image twice, upload to non-existent folder, upload without folder
- Test with different image formats simultaneously
- Test error recovery: failed upload doesn't break UI state
- Verify drag-and-drop visual feedback works correctly
- Test responsive design on different screen sizes

### Run Validation Commands
- Execute `cd app/server && uv run pytest` to run all server tests
- Execute `cd app/server && uv run pytest tests/core/test_image_security.py -v` for image security tests
- Execute `cd app/server && uv run pytest tests/core/test_image_processor.py -v` for image processor tests
- Execute `cd app/server && uv run pytest tests/test_image_upload.py -v` for API tests
- Execute `cd app/server && uv run pytest tests/test_sql_injection.py -v` to ensure existing security still works
- Execute `cd app/client && npm run build` to verify frontend builds successfully
- Execute `cd scripts && ./start.sh` for manual end-to-end testing

## Testing Strategy
### Unit Tests
- Image validation tests: test each file type validation, magic number checks, size limits
- Filename sanitization tests: path traversal attempts, special characters, long names
- Database operation tests: CRUD for images and folders with mocked database
- Metadata extraction tests: verify correct extraction from different image formats
- SQL injection tests: attempt injection through folder names, image IDs, filenames

### Integration Tests
- Full upload flow: frontend → API → database → retrieval
- Folder management flow: create → upload to folder → rename folder → verify images → delete folder
- Multi-file upload: upload multiple images simultaneously and verify all succeed
- Error handling: test network failures, database errors, invalid files
- Concurrent operations: multiple users uploading to same folder

### Edge Cases
- Empty file upload (0 bytes)
- Maximum size file upload (boundary testing)
- File with correct extension but wrong magic number
- File with no extension
- Special characters in filename: spaces, unicode, symbols
- Very long filenames (> 255 characters)
- Duplicate filenames in same folder
- Folder name conflicts with SQL keywords
- Uploading while folder is being deleted
- Browser refresh during upload
- Drag-and-drop of non-image files mixed with image files

## Acceptance Criteria
- Users can upload image files via browse button or drag-and-drop
- Multi-file selection allows uploading multiple images at once
- Supported file types (PNG, JPG, JPEG, GIF, BMP, WebP) are clearly displayed in UI
- Users can create new folders with custom names
- Folder dropdown shows all available folders with image counts
- Users can rename existing folders without losing image associations
- Users can delete empty folders (folders with images cannot be deleted)
- Uploaded images are stored in SQLite database with binary data and metadata
- Image gallery displays uploaded images organized by folder
- Users can switch between folders to view different image sets
- File type validation rejects unsupported formats with clear error messages
- File size limit (10MB) is enforced with appropriate error message
- All file uploads are validated for security (magic numbers, size, filename)
- SQL injection attempts are prevented in folder names and image IDs
- All existing application functionality continues to work without regression
- Upload progress indicators show during file upload
- Success and error messages follow existing UI patterns
- Mobile responsive design works correctly for upload interface

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest` - Run all server tests to validate the feature works with zero regressions
- `cd app/server && uv run pytest tests/core/test_image_security.py -v` - Run image security tests
- `cd app/server && uv run pytest tests/core/test_image_processor.py -v` - Run image processor tests
- `cd app/server && uv run pytest tests/test_image_upload.py -v` - Run image upload API tests
- `cd app/server && uv run pytest tests/test_sql_injection.py -v` - Ensure SQL injection protection still works
- `cd app/client && npm run build` - Ensure client builds without errors
- `cd scripts && ./start.sh` - Start the application and manually test:
  - Create multiple folders with different names
  - Upload images to different folders using both browse and drag-and-drop
  - Upload multiple images at once
  - Verify supported file types display correctly
  - Test renaming folders and verify images are still accessible
  - Test deleting empty folders succeeds and folders with images are protected
  - Test upload of invalid file types shows appropriate error
  - Test upload of oversized file shows appropriate error
  - Switch between folders and verify image gallery updates correctly
  - Refresh browser and verify state persists correctly

## Notes
- Using SQLite BLOB fields for image storage keeps implementation simple and doesn't require external file storage or dependencies
- The 10MB file size limit is configurable via constant in `image_security.py` and can be adjusted based on use case
- Consider implementing thumbnail generation in future iteration for better performance with large images
- Folder deletion protection (preventing deletion of folders with images) can be made configurable if users want cascade delete
- WebP format support uses built-in Python capabilities without additional libraries
- Magic number validation provides additional security beyond file extension checking
- Image metadata extraction using Python's `imghdr` module is part of standard library (no new dependencies)
- Consider adding image compression in future iteration to optimize storage
- Pagination for image listing will be important as users upload many images
- Consider adding image search/filter functionality in future iteration
- The current implementation stores full image binary data in database; for very large scale applications, consider external blob storage
- No external image processing libraries (PIL/Pillow) are used to maintain "std libraries only" requirement; basic metadata is sufficient for v1
