import { api } from './api/client';

// State management
let currentFolderId: number | undefined = undefined;
let folders: FolderData[] = [];
let images: ImageMetadata[] = [];

// Initialize image upload functionality
export function initializeImageUpload(): void {
  // Toggle upload panel
  const toggleButton = document.getElementById('toggle-image-upload');
  const uploadPanel = document.getElementById('image-upload-panel');

  if (toggleButton && uploadPanel) {
    toggleButton.addEventListener('click', () => {
      const isVisible = uploadPanel.style.display !== 'none';
      uploadPanel.style.display = isVisible ? 'none' : 'block';
      toggleButton.textContent = isVisible ? 'Upload Images' : 'Hide Upload';
    });
  }

  // Initialize folder dropdown
  initializeFolderDropdown();

  // Setup drag and drop
  setupDragAndDrop();

  // Setup browse button
  const browseButton = document.getElementById('browse-images-button');
  const fileInput = document.getElementById('image-file-input') as HTMLInputElement;

  if (browseButton && fileInput) {
    browseButton.addEventListener('click', () => {
      fileInput.click();
    });

    fileInput.addEventListener('change', async (e) => {
      const target = e.target as HTMLInputElement;
      if (target.files && target.files.length > 0) {
        await handleMultipleImageSelection(Array.from(target.files));
        target.value = ''; // Reset input
      }
    });
  }

  // Folder management buttons
  const newFolderButton = document.getElementById('new-folder-button');
  const renameFolderButton = document.getElementById('rename-folder-button');
  const deleteFolderButton = document.getElementById('delete-folder-button');

  if (newFolderButton) {
    newFolderButton.addEventListener('click', handleNewFolder);
  }

  if (renameFolderButton) {
    renameFolderButton.addEventListener('click', handleRenameFolder);
  }

  if (deleteFolderButton) {
    deleteFolderButton.addEventListener('click', handleDeleteFolder);
  }

  // Folder selection change
  const folderSelect = document.getElementById('folder-select') as HTMLSelectElement;
  if (folderSelect) {
    folderSelect.addEventListener('change', (e) => {
      const target = e.target as HTMLSelectElement;
      currentFolderId = target.value ? parseInt(target.value) : undefined;
      refreshImageList();
    });
  }

  // Initial load
  refreshImageList();
}

// Setup drag and drop functionality
function setupDragAndDrop(): void {
  const dropZone = document.getElementById('image-drop-zone');

  if (!dropZone) return;

  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
  });

  dropZone.addEventListener('drop', async (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');

    const files = Array.from(e.dataTransfer?.files || []);
    const imageFiles = files.filter(file => file.type.startsWith('image/'));

    if (imageFiles.length > 0) {
      await handleMultipleImageSelection(imageFiles);
    } else {
      showError('Please drop image files only (PNG, JPG, GIF, BMP, WebP)');
    }
  });
}

// Handle multiple image selection
async function handleMultipleImageSelection(files: File[]): Promise<void> {
  if (files.length === 0) return;

  showUploadProgress(true);

  let successCount = 0;
  let errorCount = 0;

  for (const file of files) {
    try {
      await uploadSingleImage(file);
      successCount++;
    } catch (error) {
      errorCount++;
      console.error(`Failed to upload ${file.name}:`, error);
    }
  }

  showUploadProgress(false);

  if (successCount > 0) {
    showSuccess(`Successfully uploaded ${successCount} image(s)`);
    await refreshImageList();
  }

  if (errorCount > 0) {
    showError(`Failed to upload ${errorCount} image(s)`);
  }
}

// Upload single image
async function uploadSingleImage(file: File): Promise<void> {
  const response = await api.uploadImage(file, currentFolderId);

  if (response.error) {
    throw new Error(response.error);
  }
}

// Refresh image list
async function refreshImageList(): Promise<void> {
  try {
    const response = await api.listImages(currentFolderId);

    if (response.error) {
      showError(response.error);
      return;
    }

    images = response.images;
    displayImageGallery(images);
  } catch (error) {
    console.error('Failed to refresh image list:', error);
    showError('Failed to load images');
  }
}

// Display image gallery
function displayImageGallery(imageList: ImageMetadata[]): void {
  const gallery = document.getElementById('image-gallery');

  if (!gallery) return;

  if (imageList.length === 0) {
    gallery.innerHTML = '<p class="no-images">No images in this folder. Upload images to get started.</p>';
    return;
  }

  gallery.innerHTML = imageList.map(image => `
    <div class="image-card" data-image-id="${image.id}">
      <img src="${api.getImageUrl(image.id)}" alt="${image.original_name}" loading="lazy">
      <div class="image-info">
        <p class="image-name" title="${image.original_name}">${image.original_name}</p>
        <p class="image-meta">${formatFileSize(image.file_size)} • ${image.file_type.toUpperCase()}</p>
        ${image.folder_name ? `<p class="image-folder">${image.folder_name}</p>` : ''}
      </div>
      <button class="delete-image-button" data-image-id="${image.id}" title="Delete image">×</button>
    </div>
  `).join('');

  // Add delete handlers
  gallery.querySelectorAll('.delete-image-button').forEach(button => {
    button.addEventListener('click', async (e) => {
      e.stopPropagation();
      const imageId = parseInt((button as HTMLElement).dataset.imageId || '0');
      if (confirm('Are you sure you want to delete this image?')) {
        await handleDeleteImage(imageId);
      }
    });
  });
}

// Delete image handler
async function handleDeleteImage(imageId: number): Promise<void> {
  try {
    await api.deleteImage(imageId);
    showSuccess('Image deleted successfully');
    await refreshImageList();
  } catch (error) {
    console.error('Failed to delete image:', error);
    showError('Failed to delete image');
  }
}

// Initialize folder dropdown
async function initializeFolderDropdown(): Promise<void> {
  try {
    const response = await api.listFolders();

    if (response.error) {
      console.error('Failed to load folders:', response.error);
      return;
    }

    folders = response.folders;
    updateFolderDropdown();
  } catch (error) {
    console.error('Failed to initialize folders:', error);
  }
}

// Update folder dropdown
function updateFolderDropdown(): void {
  const folderSelect = document.getElementById('folder-select') as HTMLSelectElement;

  if (!folderSelect) return;

  const currentValue = folderSelect.value;

  folderSelect.innerHTML = '<option value="">All Images</option>' +
    folders.map(folder =>
      `<option value="${folder.id}">${folder.folder_name} (${folder.image_count})</option>`
    ).join('');

  // Restore selection if still valid
  if (currentValue && folders.some(f => f.id === parseInt(currentValue))) {
    folderSelect.value = currentValue;
  }
}

// Handle new folder
async function handleNewFolder(): Promise<void> {
  const folderName = prompt('Enter folder name:');

  if (!folderName || folderName.trim() === '') {
    return;
  }

  // Validate folder name
  if (!/^[a-zA-Z0-9_\s-]+$/.test(folderName)) {
    showError('Folder name can only contain letters, numbers, spaces, hyphens, and underscores');
    return;
  }

  try {
    await api.createFolder(folderName.trim());
    showSuccess(`Folder "${folderName}" created successfully`);
    await initializeFolderDropdown();
  } catch (error) {
    console.error('Failed to create folder:', error);
    showError('Failed to create folder');
  }
}

// Handle rename folder
async function handleRenameFolder(): Promise<void> {
  const folderSelect = document.getElementById('folder-select') as HTMLSelectElement;

  if (!folderSelect || !folderSelect.value) {
    showError('Please select a folder to rename');
    return;
  }

  const folderId = parseInt(folderSelect.value);
  const currentFolder = folders.find(f => f.id === folderId);

  if (!currentFolder) return;

  const newName = prompt('Enter new folder name:', currentFolder.folder_name);

  if (!newName || newName.trim() === '' || newName === currentFolder.folder_name) {
    return;
  }

  // Validate folder name
  if (!/^[a-zA-Z0-9_\s-]+$/.test(newName)) {
    showError('Folder name can only contain letters, numbers, spaces, hyphens, and underscores');
    return;
  }

  try {
    await api.renameFolder(folderId, newName.trim());
    showSuccess(`Folder renamed to "${newName}"`);
    await initializeFolderDropdown();
  } catch (error) {
    console.error('Failed to rename folder:', error);
    showError('Failed to rename folder');
  }
}

// Handle delete folder
async function handleDeleteFolder(): Promise<void> {
  const folderSelect = document.getElementById('folder-select') as HTMLSelectElement;

  if (!folderSelect || !folderSelect.value) {
    showError('Please select a folder to delete');
    return;
  }

  const folderId = parseInt(folderSelect.value);
  const currentFolder = folders.find(f => f.id === folderId);

  if (!currentFolder) return;

  if (currentFolder.image_count > 0) {
    showError(`Cannot delete folder "${currentFolder.folder_name}" because it contains ${currentFolder.image_count} image(s)`);
    return;
  }

  if (!confirm(`Are you sure you want to delete the folder "${currentFolder.folder_name}"?`)) {
    return;
  }

  try {
    await api.deleteFolder(folderId);
    showSuccess(`Folder "${currentFolder.folder_name}" deleted successfully`);
    currentFolderId = undefined;
    await initializeFolderDropdown();
    await refreshImageList();
  } catch (error) {
    console.error('Failed to delete folder:', error);
    showError('Failed to delete folder');
  }
}

// Show upload progress
function showUploadProgress(show: boolean): void {
  const progressDiv = document.getElementById('upload-progress');

  if (progressDiv) {
    progressDiv.style.display = show ? 'block' : 'none';
  }
}

// Show success message
function showSuccess(message: string): void {
  // For now, use alert. In production, use a toast/notification system
  console.log('SUCCESS:', message);
  alert(message);
}

// Show error message
function showError(message: string): void {
  // For now, use alert. In production, use a toast/notification system
  console.error('ERROR:', message);
  alert(`Error: ${message}`);
}

// Format file size
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}
