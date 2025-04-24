document.addEventListener('DOMContentLoaded', function() {
    // Tab navigation
    const userTab = document.getElementById('users-tab');
    const statsTab = document.getElementById('stats-tab');
    const settingsTab = document.getElementById('settings-tab');
    
    const usersSection = document.getElementById('users-section');
    const statisticsSection = document.getElementById('statistics-section');
    const settingsSection = document.getElementById('settings-section');
    
    const sectionTitle = document.getElementById('section-title');
    
    // Password reveal functionality
    const passwordCells = document.querySelectorAll('.password-cell');
    
    // Search functionality
    const searchInput = document.getElementById('userSearch');
    const searchBtn = document.getElementById('searchBtn');
    
    // Delete user functionality
    const deleteButtons = document.querySelectorAll('.delete-user');
    const deleteModal = document.getElementById('deleteUserModal');
    const confirmDeleteBtn = document.getElementById('confirmDelete');
    
    let userIdToDelete = null;
    
    // If elements don't exist, return early (we're not on the admin page)
    if (!userTab) return;
    
    // Tab Navigation
    userTab.addEventListener('click', function(e) {
        e.preventDefault();
        setActiveTab(userTab, usersSection, '<i class="fas fa-users"></i> User Management');
    });
    
    statsTab.addEventListener('click', function(e) {
        e.preventDefault();
        setActiveTab(statsTab, statisticsSection, '<i class="fas fa-chart-bar"></i> Statistics');
        initializeCharts();
    });
    
    settingsTab.addEventListener('click', function(e) {
        e.preventDefault();
        setActiveTab(settingsTab, settingsSection, '<i class="fas fa-cogs"></i> Settings');
    });
    
    // Password reveal functionality
    passwordCells.forEach(cell => {
        cell.addEventListener('click', function() {
            this.classList.toggle('revealed');
        });
    });
    
    // Search functionality
    if (searchBtn) {
        searchBtn.addEventListener('click', performSearch);
    }
    
    if (searchInput) {
        searchInput.addEventListener('keyup', function(e) {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
    }
    
    // Delete user functionality
    deleteButtons.forEach(button => {
        button.addEventListener('click', function() {
            userIdToDelete = this.getAttribute('data-user-id');
            const deleteModal = new bootstrap.Modal(document.getElementById('deleteUserModal'));
            deleteModal.show();
        });
    });
    
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', function() {
            if (!userIdToDelete) return;
            
            fetch(`/api/delete-user/${userIdToDelete}`, {
                method: 'DELETE'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Hide the modal
                    const modalInstance = bootstrap.Modal.getInstance(document.getElementById('deleteUserModal'));
                    modalInstance.hide();
                    
                    // Remove the user row
                    const userRow = document.querySelector(`tr[data-user-id="${userIdToDelete}"]`);
                    if (userRow) {
                        userRow.remove();
                    }
                    
                    showToast('User deleted successfully', 'success');
                    
                    // Reset the user ID
                    userIdToDelete = null;
                } else {
                    showToast(data.error || 'Failed to delete user', 'error');
                }
            })
            .catch(error => {
                showToast('An error occurred: ' + error.message, 'error');
            });
        });
    }
    
    // Initialize Charts
    initializeCharts();
});

// Helper Functions
function setActiveTab(tab, section, title) {
    // Update the active tab
    document.querySelectorAll('.list-group-item').forEach(item => {
        item.classList.remove('active');
    });
    tab.classList.add('active');
    
    // Update the visible section
    document.querySelectorAll('.admin-section').forEach(section => {
        section.style.display = 'none';
    });
    section.style.display = 'block';
    
    // Update the section title
    document.getElementById('section-title').innerHTML = title;
}

function performSearch() {
    const searchTerm = document.getElementById('userSearch').value.toLowerCase();
    const tableRows = document.getElementById('userTableBody').querySelectorAll('tr');
    
    tableRows.forEach(row => {
        const text = row.textContent.toLowerCase();
        if (text.includes(searchTerm)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

function initializeCharts() {
    const chartElement = document.getElementById('userActivityChart');
    if (!chartElement) return;
    
    // Check if chart already initialized
    if (chartElement.chart) {
        chartElement.chart.destroy();
    }
    
    // Get user data
    const users = Array.from(document.querySelectorAll('tbody tr')).map(row => {
        const cells = row.querySelectorAll('td');
        if (cells.length >= 6) {
            return {
                id: row.getAttribute('data-user-id'),
                date: cells[5].textContent.trim(),
                status: cells[4].textContent.trim().includes('Active')
            };
        }
        return null;
    }).filter(Boolean);
    
    // Process data for chart
    const dates = users.map(user => {
        // Extract just the date part (not time)
        return user.date.split(' ')[0];
    });
    
    // Get unique dates and count users per date
    const uniqueDates = [...new Set(dates)].sort();
    const usersPerDay = uniqueDates.map(date => {
        return {
            date: date,
            count: dates.filter(d => d === date).length,
            active: users.filter(u => u.date.includes(date) && u.status).length,
            inactive: users.filter(u => u.date.includes(date) && !u.status).length
        };
    });
    
    // Create chart
    const ctx = chartElement.getContext('2d');
    chartElement.chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: uniqueDates,
            datasets: [
                {
                    label: 'Total Users',
                    data: usersPerDay.map(d => d.count),
                    backgroundColor: '#3b5998',
                    borderColor: '#2d4373',
                    borderWidth: 1
                },
                {
                    label: 'Active Guards',
                    data: usersPerDay.map(d => d.active),
                    backgroundColor: '#4cb944',
                    borderColor: '#3a9835',
                    borderWidth: 1
                },
                {
                    label: 'Inactive Guards',
                    data: usersPerDay.map(d => d.inactive),
                    backgroundColor: '#f7b928',
                    borderColor: '#e3a612',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#e4e6eb'
                    }
                },
                title: {
                    display: true,
                    text: 'User Registrations by Date',
                    color: '#e4e6eb'
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: '#b0b3b8'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#b0b3b8'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            }
        }
    });
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
