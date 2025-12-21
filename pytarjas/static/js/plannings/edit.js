/**
 * pytarjas/static/js/plannings/edit.js
 * Handles interactivity for the Planning Detail/Edit view.
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log("Planning edit/detail view initialized.");
    
    // Initialize any tooltips or UI components if necessary
    initTaskTableActions();
});

/**
 * Initializes listeners for actions within the tasks table.
 */
function initTaskTableActions() {
    const actionButtons = document.querySelectorAll('.btn-icon');
    
    actionButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Logic for clicking task actions can be added here
            const taskId = this.getAttribute('href').split('/').pop();
            console.log("Viewing task:", taskId);
        });
    });
}

/**
 * Example function for future use: 
 * Could be used to update a task's worker via Fetch API directly from this view.
 */
async function updateTaskWorker(taskId, workerId) {
    try {
        const response = await fetch(`/tasks/${taskId}/update`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                worker_id: workerId
            })
        });

        const result = await response.json();

        if (result.success) {
            console.log("Worker updated successfully");
            // Optionally refresh part of the UI
        } else {
            console.error("Error updating worker:", result.error);
        }
    } catch (error) {
        console.error("Fetch error:", error);
    }
}