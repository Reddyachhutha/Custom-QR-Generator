document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('qr-form');
    
    const logoSizeSlider = document.getElementById('logo-size');
    const logoSizeVal = document.getElementById('logo-size-val');
    if (logoSizeSlider && logoSizeVal) {
        logoSizeSlider.addEventListener('input', (e) => {
            logoSizeVal.textContent = e.target.value + '%';
        });
    }
    
    // Modal Logic
    const bgUploadInput = document.getElementById('bg-upload');
    const limitationsModal = document.getElementById('limitations-modal');
    const closeModalBtn = document.getElementById('close-modal-btn');
    let hasShownModal = false;

    if (bgUploadInput && limitationsModal && closeModalBtn) {
        bgUploadInput.addEventListener('click', (e) => {
            if (!hasShownModal) {
                e.preventDefault(); // Stop file picker from opening the first time
                limitationsModal.classList.remove('hidden');
                hasShownModal = true;
            }
        });
        
        closeModalBtn.addEventListener('click', (e) => {
            e.preventDefault();
            limitationsModal.classList.add('hidden');
        });
    }
    
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const url = document.getElementById('qr-url').value;
            const shape = document.getElementById('qr-shape').value;
            const fillColor = document.getElementById('fill-color').value;
            const backColor = document.getElementById('back-color').value;
            const logoUpload = document.getElementById('logo-upload').files[0];
            
            const logoShape = document.getElementById('logo-shape') ? document.getElementById('logo-shape').value : 'square';
            const logoPosition = document.getElementById('logo-position') ? document.getElementById('logo-position').value : 'center';
            const logoSize = document.getElementById('logo-size') ? (document.getElementById('logo-size').value / 100.0) : 0.28;
            
            const bgUpload = document.getElementById('bg-upload').files[0];
            
            const resultDiv = document.getElementById('qr-result');
            const loadingDiv = document.getElementById('loading');
            const emptyState = document.getElementById('empty-state');
            const qrImage = document.getElementById('qr-image');
            const downloadBtn = document.getElementById('download-btn');
            
            // UI state transition
            resultDiv.classList.add('hidden');
            emptyState.classList.add('hidden');
            loadingDiv.classList.remove('hidden');
            
            try {
                // Use FormData for file uploads
                const formData = new FormData();
                formData.append('url', url);
                formData.append('shape', shape);
                formData.append('fill_color', fillColor);
                formData.append('back_color', backColor);
                
                if (logoUpload) {
                    formData.append('logo', logoUpload);
                    formData.append('logo_shape', logoShape);
                    formData.append('logo_position', logoPosition);
                    formData.append('logo_size_factor', logoSize);
                }
                
                if (bgUpload) {
                    formData.append('bg_image', bgUpload);
                }
                
                const response = await fetch('/generate', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error('Failed to generate QR code');
                }
                
                const blob = await response.blob();
                const imageUrl = URL.createObjectURL(blob);
                
                qrImage.src = imageUrl;
                downloadBtn.href = imageUrl;
                
                // Show result
                loadingDiv.classList.add('hidden');
                resultDiv.classList.remove('hidden');
                
            } catch (error) {
                console.error('Error:', error);
                alert('An error occurred. Make sure your FastAPI backend is running on port 8000.');
                loadingDiv.classList.add('hidden');
                emptyState.classList.remove('hidden');
            }
        });
    }
    
    // Make the QR block draggable
    const resultSection = document.querySelector('.result-section');
    let isDragging = false;
    let currentX;
    let currentY;
    let initialX;
    let initialY;
    let xOffset = 0;
    let yOffset = 0;

    if (resultSection) {
        resultSection.style.cursor = 'grab';
        
        resultSection.addEventListener('mousedown', dragStart);
        document.addEventListener('mouseup', dragEnd);
        document.addEventListener('mousemove', drag);
        
        // Touch support for mobile
        resultSection.addEventListener('touchstart', dragStart, { passive: false });
        document.addEventListener('touchend', dragEnd);
        document.addEventListener('touchmove', drag, { passive: false });
    }

    function dragStart(e) {
        // Prevent dragging if they are clicking a button or link
        if (e.target.tagName.toLowerCase() === 'button' || e.target.tagName.toLowerCase() === 'a' || e.target.closest('a')) return;
        
        if (e.type === "touchstart") {
            initialX = e.touches[0].clientX - xOffset;
            initialY = e.touches[0].clientY - yOffset;
        } else {
            if (e.button !== 0) return; // Only left click
            initialX = e.clientX - xOffset;
            initialY = e.clientY - yOffset;
        }

        isDragging = true;
        resultSection.style.cursor = 'grabbing';
        resultSection.style.zIndex = '100'; // Keep it on top
    }

    function dragEnd() {
        if (!isDragging) return;
        initialX = currentX;
        initialY = currentY;
        isDragging = false;
        resultSection.style.cursor = 'grab';
    }

    function drag(e) {
        if (isDragging) {
            e.preventDefault();
            
            if (e.type === "touchmove") {
                currentX = e.touches[0].clientX - initialX;
                currentY = e.touches[0].clientY - initialY;
            } else {
                currentX = e.clientX - initialX;
                currentY = e.clientY - initialY;
            }

            xOffset = currentX;
            yOffset = currentY;
            
            resultSection.style.transform = `translate3d(${currentX}px, ${currentY}px, 0)`;
        }
    }
});
