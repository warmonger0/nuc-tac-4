import './style.css';
import { api } from './api/client';

// State management
let currentFolder = 'default';
let folderModalMode: 'create' | 'rename' = 'create';
let selectedNavFolder: string | null = 'all';  // 'all' or folder name
let folderStats: FolderStats[] = [];

// DOM Elements
const folderSelect = document.getElementById('folder-select') as HTMLSelectElement;
const createFolderButton = document.getElementById('create-folder-button') as HTMLButtonElement;
const renameFolderButton = document.getElementById('rename-folder-button') as HTMLButtonElement;
const deleteFolderButton = document.getElementById('delete-folder-button') as HTMLButtonElement;
const dropZone = document.getElementById('drop-zone') as HTMLDivElement;
const fileInput = document.getElementById('file-input') as HTMLInputElement;
const browseButton = document.getElementById('browse-button') as HTMLButtonElement;
const uploadProgress = document.getElementById('upload-progress') as HTMLDivElement;
const progressFill = document.getElementById('progress-fill') as HTMLDivElement;
const uploadStatus = document.getElementById('upload-status') as HTMLParagraphElement;
const imageGallery = document.getElementById('image-gallery') as HTMLDivElement;
const folderModal = document.getElementById('folder-modal') as HTMLDivElement;
const folderModalTitle = document.getElementById('folder-modal-title') as HTMLHeadingElement;
const closeFolderModal = document.getElementById('close-folder-modal') as HTMLButtonElement;
const folderNameInput = document.getElementById('folder-name-input') as HTMLInputElement;
const cancelFolderButton = document.getElementById('cancel-folder-button') as HTMLButtonElement;
const confirmFolderButton = document.getElementById('confirm-folder-button') as HTMLButtonElement;

// New DOM elements for folder navigation
const folderList = document.getElementById('folder-list') as HTMLDivElement;
const galleryTitle = document.getElementById('gallery-title') as HTMLHeadingElement;

// Duplicate modal elements (for future implementation)
const duplicateModal = document.getElementById('duplicate-modal') as HTMLDivElement;
const closeDuplicateModal = document.getElementById('close-duplicate-modal') as HTMLButtonElement;
const skipDuplicateButton = document.getElementById('skip-duplicate-button') as HTMLButtonElement;
const uploadAnywayButton = document.getElementById('upload-anyway-button') as HTMLButtonElement;

// Initialize the page
async function init() {
  await loadFolders();
  await loadImages();
  setupEventListeners();
}

// Setup event listeners
function setupEventListeners() {
  // Browse button
  browseButton.addEventListener('click', () => {
    fileInput.click();
  });

  // File input change
  fileInput.addEventListener('change', (e) => {
    const target = e.target as HTMLInputElement;
    if (target.files && target.files.length > 0) {
      handleFiles(target.files);
    }
  });

  // Drag and drop events
  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
  });

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');

    if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  });

  // Folder selection
  folderSelect.addEventListener('change', (e) => {
    const target = e.target as HTMLSelectElement;
    currentFolder = target.value;
    updateFolderButtons();
    loadImages();
  });

  // Folder management buttons
  createFolderButton.addEventListener('click', () => {
    showFolderModal('create');
  });

  renameFolderButton.addEventListener('click', () => {
    showFolderModal('rename');
  });

  deleteFolderButton.addEventListener('click', () => {
    handleDeleteFolder();
  });

  // Modal events
  closeFolderModal.addEventListener('click', () => {
    hideFolderModal();
  });

  cancelFolderButton.addEventListener('click', () => {
    hideFolderModal();
  });

  confirmFolderButton.addEventListener('click', () => {
    handleFolderModalConfirm();
  });

  // Close modal on outside click
  folderModal.addEventListener('click', (e) => {
    if (e.target === folderModal) {
      hideFolderModal();
    }
  });

  // Enter key in folder input
  folderNameInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      handleFolderModalConfirm();
    }
  });

  // Duplicate modal events
  closeDuplicateModal?.addEventListener('click', () => {
    hideDuplicateModal();
  });

  skipDuplicateButton?.addEventListener('click', () => {
    hideDuplicateModal();
  });

  uploadAnywayButton?.addEventListener('click', () => {
    proceedWithUpload();
  });

  duplicateModal?.addEventListener('click', (e) => {
    if (e.target === duplicateModal) {
      hideDuplicateModal();
    }
  });
}

// Load folders from API
async function loadFolders() {
  try {
    const response = await api.getFolders();

    if (response.error) {
      showError('Failed to load folders: ' + response.error);
      return;
    }

    // Store folder stats
    folderStats = response.folders;

    // Clear existing options except the first one
    folderSelect.innerHTML = '<option value="">Select a folder...</option>';

    // Add folders
    response.folders.forEach(folder => {
      const option = document.createElement('option');
      option.value = folder.name;
      option.textContent = folder.name;
      folderSelect.appendChild(option);
    });

    // Set default folder if available
    const defaultFolder = response.folders.find(f => f.name === 'default');
    if (defaultFolder) {
      folderSelect.value = 'default';
      currentFolder = 'default';
      updateFolderButtons();
    }

    // Render folder navigation
    renderFolderNavigation();
  } catch (error) {
    showError('Failed to load folders: ' + (error as Error).message);
  }
}

// Update folder button states
function updateFolderButtons() {
  const hasFolder = currentFolder !== '';
  const isDefault = currentFolder === 'default';

  renameFolderButton.disabled = !hasFolder || isDefault;
  deleteFolderButton.disabled = !hasFolder || isDefault;
}

// Show folder modal
function showFolderModal(mode: 'create' | 'rename') {
  folderModalMode = mode;

  if (mode === 'create') {
    folderModalTitle.textContent = 'Create Folder';
    folderNameInput.placeholder = 'Enter folder name';
    folderNameInput.value = '';
  } else {
    folderModalTitle.textContent = 'Rename Folder';
    folderNameInput.placeholder = 'Enter new folder name';
    folderNameInput.value = currentFolder;
  }

  folderModal.style.display = 'flex';
  folderNameInput.focus();
}

// Hide folder modal
function hideFolderModal() {
  folderModal.style.display = 'none';
  folderNameInput.value = '';
}

// Handle folder modal confirm
async function handleFolderModalConfirm() {
  const folderName = folderNameInput.value.trim();

  if (!folderName) {
    showError('Folder name cannot be empty');
    return;
  }

  if (folderModalMode === 'create') {
    await handleCreateFolder(folderName);
  } else {
    await handleRenameFolder(folderName);
  }
}

// Create folder
async function handleCreateFolder(folderName: string) {
  try {
    const response = await api.createFolder(folderName);

    if (response.success) {
      hideFolderModal();
      await loadFolders();
      folderSelect.value = folderName;
      currentFolder = folderName;
      updateFolderButtons();
      showSuccess(response.message);
    } else {
      showError(response.error || response.message);
    }
  } catch (error) {
    showError('Failed to create folder: ' + (error as Error).message);
  }
}

// Rename folder
async function handleRenameFolder(newName: string) {
  try {
    const response = await api.renameFolder(currentFolder, newName);

    if (response.success) {
      hideFolderModal();
      await loadFolders();
      folderSelect.value = newName;
      currentFolder = newName;
      updateFolderButtons();
      await loadImages();
      showSuccess(response.message);
    } else {
      showError(response.error || response.message);
    }
  } catch (error) {
    showError('Failed to rename folder: ' + (error as Error).message);
  }
}

// Delete folder
async function handleDeleteFolder() {
  if (!currentFolder || currentFolder === 'default') {
    return;
  }

  if (!confirm(`Are you sure you want to delete the folder "${currentFolder}"? Images will be moved to the default folder.`)) {
    return;
  }

  try {
    const response = await api.deleteFolder(currentFolder);

    if (response.success) {
      await loadFolders();
      folderSelect.value = 'default';
      currentFolder = 'default';
      updateFolderButtons();
      await loadImages();
      showSuccess(response.message);
    } else {
      showError(response.error || response.message);
    }
  } catch (error) {
    showError('Failed to delete folder: ' + (error as Error).message);
  }
}

// Handle file upload
async function handleFiles(files: FileList) {
  if (!currentFolder) {
    showError('Please select a folder first');
    return;
  }

  // Show progress
  uploadProgress.style.display = 'block';
  progressFill.style.width = '0%';
  uploadStatus.textContent = `Uploading ${files.length} file(s)...`;

  try {
    // Simulate progress (since we don't have real progress tracking)
    progressFill.style.width = '50%';

    const responses = await api.uploadImages(files, currentFolder);

    // Check for errors
    const errors = responses.filter(r => r.error);
    const successes = responses.filter(r => !r.error);

    progressFill.style.width = '100%';

    if (successes.length > 0) {
      uploadStatus.textContent = `Successfully uploaded ${successes.length} image(s)`;
      await loadImages();
    }

    if (errors.length > 0) {
      const errorMessages = errors.map(e => `${e.filename}: ${e.error}`).join('\n');
      showError(`Some uploads failed:\n${errorMessages}`);
    } else if (successes.length > 0) {
      showSuccess(`Successfully uploaded ${successes.length} image(s)`);
    }

    // Hide progress after a delay
    setTimeout(() => {
      uploadProgress.style.display = 'none';
    }, 2000);

    // Reset file input
    fileInput.value = '';
  } catch (error) {
    uploadProgress.style.display = 'none';
    showError('Upload failed: ' + (error as Error).message);
  }
}

// Load images from API
async function loadImages(folder?: string) {
  try {
    const folderToLoad = folder !== undefined ? (folder || undefined) : (currentFolder || undefined);
    const response = await api.getImages(folderToLoad);

    if (response.error) {
      showError('Failed to load images: ' + response.error);
      return;
    }

    displayImages(response.images);
  } catch (error) {
    showError('Failed to load images: ' + (error as Error).message);
  }
}

// Display images in gallery
function displayImages(images: ImageMetadata[]) {
  if (images.length === 0) {
    imageGallery.innerHTML = '<p class="no-tables">No images uploaded yet. Upload images to get started.</p>';
    return;
  }

  imageGallery.innerHTML = '';

  images.forEach(image => {
    const card = createImageCard(image);
    imageGallery.appendChild(card);
  });
}

// Create image card
function createImageCard(image: ImageMetadata): HTMLDivElement {
  const card = document.createElement('div');
  card.className = 'image-card';

  const img = document.createElement('img');
  img.className = 'image-thumbnail';
  img.src = api.getImageUrl(image.image_id);
  img.alt = image.filename;
  img.loading = 'lazy';

  // Click to view full image
  img.addEventListener('click', () => {
    showImageModal(image);
  });

  const info = document.createElement('div');
  info.className = 'image-info';

  const filename = document.createElement('div');
  filename.className = 'image-filename';
  filename.textContent = image.filename;
  filename.title = image.filename;

  const meta = document.createElement('div');
  meta.className = 'image-meta';

  const size = document.createElement('span');
  size.textContent = formatFileSize(image.size);

  const date = document.createElement('span');
  date.textContent = formatDate(image.created_at);

  meta.appendChild(size);
  meta.appendChild(date);

  const actions = document.createElement('div');
  actions.className = 'image-actions';

  const deleteButton = document.createElement('button');
  deleteButton.className = 'delete-image-button';
  deleteButton.textContent = 'Delete';
  deleteButton.addEventListener('click', (e) => {
    e.stopPropagation();
    handleDeleteImage(image.image_id, image.filename);
  });

  actions.appendChild(deleteButton);

  info.appendChild(filename);
  info.appendChild(meta);
  info.appendChild(actions);

  card.appendChild(img);
  card.appendChild(info);

  return card;
}

// Show image in modal/lightbox
function showImageModal(image: ImageMetadata) {
  const modal = document.createElement('div');
  modal.className = 'image-modal';

  const img = document.createElement('img');
  img.src = api.getImageUrl(image.image_id);
  img.alt = image.filename;

  const closeButton = document.createElement('button');
  closeButton.className = 'close-image-modal';
  closeButton.textContent = '×';
  closeButton.addEventListener('click', () => {
    document.body.removeChild(modal);
  });

  modal.appendChild(img);
  modal.appendChild(closeButton);

  // Close on background click
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      document.body.removeChild(modal);
    }
  });

  // Close on Escape key
  const handleEscape = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      document.body.removeChild(modal);
      document.removeEventListener('keydown', handleEscape);
    }
  };
  document.addEventListener('keydown', handleEscape);

  document.body.appendChild(modal);
}

// Delete image
async function handleDeleteImage(imageId: string, filename: string) {
  if (!confirm(`Are you sure you want to delete "${filename}"?`)) {
    return;
  }

  try {
    await api.deleteImage(imageId);
    showSuccess('Image deleted successfully');
    await loadImages();
  } catch (error) {
    showError('Failed to delete image: ' + (error as Error).message);
  }
}

// Utility functions
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString();
}

function showError(message: string) {
  // Create error toast
  const toast = document.createElement('div');
  toast.className = 'error-message';
  toast.textContent = message;
  toast.style.position = 'fixed';
  toast.style.top = '2rem';
  toast.style.right = '2rem';
  toast.style.zIndex = '3000';
  toast.style.maxWidth = '400px';

  document.body.appendChild(toast);

  setTimeout(() => {
    document.body.removeChild(toast);
  }, 5000);
}

function showSuccess(message: string) {
  // Create success toast
  const toast = document.createElement('div');
  toast.className = 'error-message';
  toast.style.background = 'rgba(40, 167, 69, 0.1)';
  toast.style.borderColor = 'var(--success-color)';
  toast.style.color = 'var(--success-color)';
  toast.textContent = message;
  toast.style.position = 'fixed';
  toast.style.top = '2rem';
  toast.style.right = '2rem';
  toast.style.zIndex = '3000';
  toast.style.maxWidth = '400px';

  document.body.appendChild(toast);

  setTimeout(() => {
    document.body.removeChild(toast);
  }, 3000);
}

// Folder navigation rendering
function renderFolderNavigation() {
  if (!folderList) return;

  // Calculate total images across all folders
  const totalImages = folderStats.reduce((sum, folder) => sum + folder.image_count, 0);

  // Clear existing folder list (except "All Images")
  folderList.innerHTML = `
    <div class="folder-item ${selectedNavFolder === 'all' ? 'folder-item-active' : ''}" data-folder="all">
      <span class="folder-name">All Images</span>
      <span class="folder-badge" id="badge-all">${totalImages}</span>
    </div>
  `;

  // Add folder items
  folderStats.forEach(folder => {
    const folderItem = document.createElement('div');
    folderItem.className = `folder-item ${selectedNavFolder === folder.name ? 'folder-item-active' : ''}`;
    folderItem.dataset.folder = folder.name;
    folderItem.innerHTML = `
      <span class="folder-name">${folder.name}</span>
      <span class="folder-badge" id="badge-${folder.name}">${folder.image_count}</span>
    `;
    folderItem.addEventListener('click', () => handleFolderNavClick(folder.name));
    folderList.appendChild(folderItem);
  });

  // Add click handler for "All Images"
  const allImagesItem = folderList.querySelector('[data-folder="all"]');
  allImagesItem?.addEventListener('click', () => handleFolderNavClick('all'));
}

// Handle folder navigation click
async function handleFolderNavClick(folderName: string) {
  selectedNavFolder = folderName;

  // Update active states
  document.querySelectorAll('.folder-item').forEach(item => {
    item.classList.remove('folder-item-active');
  });
  document.querySelector(`[data-folder="${folderName}"]`)?.classList.add('folder-item-active');

  // Update gallery title
  if (galleryTitle) {
    galleryTitle.textContent = folderName === 'all' ? 'Image Gallery' : `Image Gallery - ${folderName}`;
  }

  // Load images for the selected folder
  await loadImages(folderName === 'all' ? undefined : folderName);
}

// Duplicate detection modal functions (simplified - full implementation would integrate with handleFiles)
function hideDuplicateModal() {
  if (duplicateModal) {
    duplicateModal.style.display = 'none';
  }
}

function proceedWithUpload() {
  hideDuplicateModal();
}

// Initialize on page load
init();
