/* pytarjas/static/js/tasks/list.js */

document.addEventListener('DOMContentLoaded', function() {
    
    // --- 1. TABLE TOGGLE LOGIC (Event Delegation) ---
    const tableBody = document.querySelector('.tasks-table tbody');
    if (tableBody) {
        tableBody.addEventListener('click', function(e) {
            // Check if clicked element is a toggle icon
            if (e.target.classList.contains('toggle-icon')) {
                const taskId = e.target.dataset.taskId;
                toggleDetail(taskId, e.target);
            }
        });
    }

    function toggleDetail(taskId, iconElement) {
        const detailRow = document.getElementById(`detail-${taskId}`);
        if (!detailRow) return;

        const isClosed = detailRow.style.display === 'none' || detailRow.style.display === '';

        if (isClosed) {
            // Optional: Close others
            document.querySelectorAll('.collapsible-row').forEach(row => {
                if (row.id !== `detail-${taskId}`) row.style.display = 'none';
            });
            document.querySelectorAll('.toggle-icon.open').forEach(icon => {
                if (icon !== iconElement) icon.classList.remove('open');
            });
            
            detailRow.style.display = 'table-row';
            iconElement.classList.add('open');
        } else {
            detailRow.style.display = 'none';
            iconElement.classList.remove('open');
        }
    }


    // --- 2. DYNAMIC FILTERING LOGIC ---
    const filterForm = document.getElementById('filterForm');
    const formIdSelect = document.getElementById('form_id_filter');
    const dynamicFilterContainer = document.getElementById('dynamic-question-filters');
    const allFormsDataTextarea = document.getElementById('allFormsData');
    
    let allFormsData = {};

    // Parse form definitions
    if (allFormsDataTextarea) {
        try {
            allFormsData = JSON.parse(allFormsDataTextarea.value.trim());
        } catch (e) {
            console.error("Error parsing allFormsData:", e);
        }
    }

    function updateDynamicFilters() {
        if(!formIdSelect) return;
        const selectedFormId = formIdSelect.value;
        const currentFilters = new URLSearchParams(window.location.search);
        
        // Clear old
        document.querySelectorAll('.dynamic-filter-group').forEach(el => el.remove());
        
        if (!selectedFormId || !allFormsData[selectedFormId]) return;

        const form = allFormsData[selectedFormId];
        
        form.questions.forEach(q => {
            const type = q.type ? q.type.trim().toLowerCase() : '';
            if (['text', 'textarea', 'number', 'select', 'client_select'].includes(type)) {
                
                const nameKey = q.name_key; 
                const currentValue = currentFilters.get(nameKey) || '';
                
                const filterGroup = document.createElement('div');
                filterGroup.className = 'filter-group dynamic-filter-group';
                filterGroup.dataset.filterKey = nameKey;
                filterGroup.style.minWidth = '180px';

                let labelText = q.text.replace(/[\*\?]/g, '').trim(); 
                if (type === 'client_select') labelText = 'Cliente Asignado';
                if (q.text.toLowerCase().includes('contenedor')) labelText = 'N° Contenedor';

                let inputHtml = `
                    <label for="${nameKey}">${labelText}</label>
                    <input type="${type === 'number' ? 'number' : 'text'}" 
                           name="${nameKey}" id="${nameKey}" 
                           value="${currentValue}" class="form-control filter-input" 
                           placeholder="${type === 'number' ? 'Buscar número' : 'Buscar texto...'}">
                `;

                filterGroup.innerHTML = inputHtml;
                dynamicFilterContainer.appendChild(filterGroup);
            }
        });
        
        // Attach listeners to new inputs
        document.querySelectorAll('.dynamic-filter-group .filter-input').forEach(input => {
            input.addEventListener('input', triggerFilter);
            input.addEventListener('change', triggerFilter);
        });
    }

    // Initialize dynamic filters
    if(formIdSelect) {
        updateDynamicFilters();
        formIdSelect.addEventListener('change', () => {
            document.querySelectorAll('.dynamic-filter-group').forEach(el => el.remove());
            updateDynamicFilters();
            triggerFilter();
        });
    }


    // --- 3. CUSTOM DROPDOWN LOGIC ---
    
    // Toggle Menu (Attached via event listeners now)
    document.querySelectorAll('.custom-filter-display').forEach(display => {
        display.addEventListener('click', function() {
            const container = this.closest('.custom-filter-container');
            const menu = container.querySelector('.custom-filter-menu');
            const searchInput = menu.querySelector('.filter-search-input');
            const type = container.id.replace('-filter-container', ''); // 'created-by' or 'assigned-to'

            // Close others
            document.querySelectorAll('.custom-filter-menu.active').forEach(m => {
                if(m !== menu) m.classList.remove('active');
            });

            menu.classList.toggle('active');
            if (menu.classList.contains('active')) {
                 if(searchInput) {
                     searchInput.focus();
                     searchInput.value = '';
                     filterUsers(searchInput, menu.querySelector('.filter-role-group'));
                 }
            }
            // Reset collapse state
            menu.querySelectorAll('.filter-user-list').forEach(l => l.style.display = 'none');
            menu.querySelectorAll('.filter-role-category').forEach(h => h.classList.remove('expanded'));
        });
    });

    // Toggle Groups inside Menu
    document.querySelectorAll('.filter-role-category').forEach(category => {
        category.addEventListener('click', function() {
            const userList = this.nextElementSibling;
            if (userList && userList.classList.contains('filter-user-list')) {
                userList.style.display = userList.style.display === 'block' ? 'none' : 'block';
                this.classList.toggle('expanded');
            }
        });
    });

    // Select User
    document.querySelectorAll('.filter-user-list-item, .filter-user-list li').forEach(item => {
        item.addEventListener('click', function(e) {
            e.stopPropagation(); // Prevent menu toggle
            
            const id = this.dataset.id;
            const username = this.dataset.username;
            
            // Navigate up to find the container
            const container = this.closest('.custom-filter-container');
            const display = container.querySelector('.custom-filter-display');
            const hiddenInput = container.querySelector('input[type="hidden"]');
            const menu = container.querySelector('.custom-filter-menu');

            // Update UI
            // Keep the arrow span if possible, simpler to just replace text node
            display.childNodes[0].textContent = username + " "; 
            hiddenInput.value = id;
            menu.classList.remove('active');
            
            triggerFilter();
        });
    });

    // Search Users
    function filterUsers(input, list) {
        const filter = input.value.toUpperCase();
        
        list.querySelectorAll('.filter-role-category').forEach(categoryHeader => {
            const userList = categoryHeader.nextElementSibling;
            const categoryText = categoryHeader.textContent.toUpperCase();
            let hasVisibleUsers = false;
            
            if (userList) {
                userList.querySelectorAll('li').forEach(userItem => {
                    const match = userItem.dataset.username.toUpperCase().indexOf(filter) > -1;
                    userItem.style.display = match ? "" : "none";
                    if (match) hasVisibleUsers = true;
                });
            }
            
            if (categoryText.indexOf(filter) > -1 || hasVisibleUsers) {
                categoryHeader.style.display = "";
                if (filter.length > 0) {
                     if (userList) userList.style.display = 'block';
                     categoryHeader.classList.add('expanded');
                } else {
                    if (userList) userList.style.display = 'none';
                    categoryHeader.classList.remove('expanded');
                }
            } else {
                categoryHeader.style.display = "none";
                if (userList) userList.style.display = 'none';
            }
        });

        // Handle 'All' option
        list.querySelectorAll('.all-option').forEach(item => {
             item.style.display = item.textContent.toUpperCase().indexOf(filter) > -1 ? "" : "none";
        });
    }

    document.querySelectorAll('.filter-search-input').forEach(input => {
        input.addEventListener('input', function() {
            const list = this.nextElementSibling; // The UL
            filterUsers(this, list);
        });
    });


    // --- 4. DEBOUNCED TRIGGER & URL CLEANUP ---
    let debounceTimer;

    function triggerFilter() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            const data = new FormData(filterForm);
            const newParams = new URLSearchParams();
            
            for (const [key, value] of data.entries()) {
                const val = value.trim();
                const isDefault = (key === 'status' && val === 'all') || 
                                  (key.includes('_id') && val === '') || 
                                  val === '';
                
                if (!isDefault) newParams.set(key, val);
                else if (key === 'status' && val === 'all') newParams.set(key, val);
            }
            
            window.location.href = `${window.location.pathname}?${newParams.toString()}`;

        }, 400); 
    }

    // Attach listeners to standard inputs
    document.querySelectorAll('.filter-input').forEach(input => {
        const eventType = (input.tagName === 'SELECT' || input.type === 'date' || input.type === 'hidden') 
                          ? 'change' : 'input';
        input.addEventListener(eventType, triggerFilter);
    });


    // --- 5. SCROLL RESTORATION ---
    const urlParams = new URLSearchParams(window.location.search);
    const savedScrollY = urlParams.get('scroll_pos');
    if (savedScrollY) {
        window.scrollTo(0, parseInt(savedScrollY));
        if (window.history.replaceState) {
            const cleanUrl = window.location.href.replace(/&?scroll_pos=[^&]*/, "");
            window.history.replaceState(null, document.title, cleanUrl);
        }
    }
    
    // Save scroll on unload (optional enhancement, often handled by browser, but good for explicit refreshes)
    window.addEventListener('beforeunload', () => {
        // You could append scroll_pos here if you were doing form submission
    });

    // --- 6. AUTO REFRESH ---
    const AUTO_REFRESH_INTERVAL = 30000;
    let autoRefreshTimer = null;
    function startAutoRefresh() {
      if (navigator.onLine && !autoRefreshTimer) {
        autoRefreshTimer = setTimeout(() => window.location.reload(), AUTO_REFRESH_INTERVAL);
      }
    }
    function stopAutoRefresh() {
      if (autoRefreshTimer) { clearTimeout(autoRefreshTimer); autoRefreshTimer = null; }
    }
    
    startAutoRefresh();
    window.addEventListener('offline', stopAutoRefresh);
    window.addEventListener('online', startAutoRefresh);
    // Stop if user interacts with filters to prevent reload while typing
    filterForm.addEventListener('input', stopAutoRefresh);
    filterForm.addEventListener('click', stopAutoRefresh);

});