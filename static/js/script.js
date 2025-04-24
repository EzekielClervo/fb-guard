document.addEventListener('DOMContentLoaded', function() {
    // Profile Guard Functionality
    const loginForm = document.getElementById('loginForm');
    const loginStep = document.getElementById('loginStep');
    const tokenStep = document.getElementById('tokenStep');
    const completionStep = document.getElementById('completionStep');
    const loadingOverlay = document.getElementById('loadingOverlay');
    
    // Step indicators
    const step1 = document.getElementById('step1');
    const step2 = document.getElementById('step2');
    const step3 = document.getElementById('step3');
    
    // Token and ID fields
    const accessTokenField = document.getElementById('accessToken');
    const userIdField = document.getElementById('userId');
    
    // Buttons
    const activateGuardBtn = document.getElementById('activateGuardBtn');
    const copyTokenBtn = document.getElementById('copyToken');
    const copyIdBtn = document.getElementById('copyId');
    
    // If elements don't exist, return early (we're not on the profile guard page)
    if (!loginForm) return;
    
    // Form Submission - Get Token
    loginForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        
        if (!email || !password) {
            showToast('Please enter your Facebook email and password', 'error');
            return;
        }
        
        // Show loading
        loadingOverlay.style.display = 'flex';
        document.getElementById('loadingText').textContent = 'Getting access token...';
        
        // Send request to backend
        const formData = new FormData();
        formData.append('action', 'get_token');
        formData.append('email', email);
        formData.append('password', password);
        
        fetch('/profile-guard', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            loadingOverlay.style.display = 'none';
            
            if (data.success) {
                // Show token and ID
                accessTokenField.value = data.token;
                userIdField.value = data.user_id;
                
                // Update step progress
                step1.querySelector('.step-circle').classList.remove('active');
                step1.querySelector('.step-circle').classList.add('completed');
                step1.querySelector('.step-circle').innerHTML = '<i class="fas fa-check"></i>';
                
                step2.querySelector('.step-circle').classList.add('active');
                
                // Show token step
                loginStep.classList.remove('active');
                tokenStep.classList.add('active');
                
                showToast('Access token generated successfully!', 'success');
            } else {
                showToast(data.error || 'Failed to get access token', 'error');
            }
        })
        .catch(error => {
            loadingOverlay.style.display = 'none';
            showToast('An error occurred: ' + error.message, 'error');
        });
    });
    
    // Activate Profile Guard
    if (activateGuardBtn) {
        activateGuardBtn.addEventListener('click', function() {
            const token = accessTokenField.value;
            const userId = userIdField.value;
            
            if (!token || !userId) {
                showToast('Token or User ID is missing', 'error');
                return;
            }
            
            // Show loading
            loadingOverlay.style.display = 'flex';
            document.getElementById('loadingText').textContent = 'Activating Profile Guard...';
            
            // Send request to backend
            const formData = new FormData();
            formData.append('action', 'activate_guard');
            formData.append('token', token);
            formData.append('user_id', userId);
            
            fetch('/profile-guard', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                loadingOverlay.style.display = 'none';
                
                if (data.success) {
                    // Update step progress
                    step2.querySelector('.step-circle').classList.remove('active');
                    step2.querySelector('.step-circle').classList.add('completed');
                    step2.querySelector('.step-circle').innerHTML = '<i class="fas fa-check"></i>';
                    
                    step3.querySelector('.step-circle').classList.add('active');
                    
                    // Show completion step
                    tokenStep.classList.remove('active');
                    completionStep.classList.add('active');
                    
                    showToast('Profile Guard has been activated!', 'success');
                } else {
                    showToast(data.error || 'Failed to activate Profile Guard', 'error');
                }
            })
            .catch(error => {
                loadingOverlay.style.display = 'none';
                showToast('An error occurred: ' + error.message, 'error');
            });
        });
    }
    
    // Copy buttons functionality
    if (copyTokenBtn) {
        copyTokenBtn.addEventListener('click', function() {
            copyToClipboard(accessTokenField);
            showToast('Access token copied to clipboard', 'info');
        });
    }
    
    if (copyIdBtn) {
        copyIdBtn.addEventListener('click', function() {
            copyToClipboard(userIdField);
            showToast('User ID copied to clipboard', 'info');
        });
    }
});

// Helper Functions
function copyToClipboard(element) {
    element.select();
    document.execCommand('copy');
}

function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Set the appropriate color based on type
    let bgColor = 'bg-info';
    if (type === 'success') bgColor = 'bg-success';
    if (type === 'error') bgColor = 'bg-danger';
    if (type === 'warning') bgColor = 'bg-warning';
    
    // Create the toast
    const toastId = 'toast-' + Date.now();
    const toastHtml = `
    <div id="${toastId}" class="toast align-items-center text-white ${bgColor} border-0" role="alert" aria-live="assertive" aria-atomic="true">
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    // Initialize and show the toast
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: 3000
    });
    toast.show();
    
    // Remove the toast element after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}
