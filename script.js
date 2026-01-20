document.addEventListener('DOMContentLoaded', () => {
    const buildingSelect = document.getElementById('building');
    const daySelect = document.getElementById('day');
    const hourSelect = document.getElementById('hour');
    const findBtn = document.getElementById('findBtn');
    const resultsDiv = document.getElementById('results');

    let roomData = {};

    // Helper function for 12-hour format
    function formatHour(hour24) {
        const suffix = hour24 >= 12 ? 'PM' : 'AM';
        const hour12 = hour24 % 12 || 12;
        return `${hour12} ${suffix}`;
    }

    // Populate hours (1 to 11, where 1=8am, 11=6pm)
    // Hour 1: 8-9 AM, Hour 2: 9-10 AM, ..., Hour 11: 6-7 PM
    for (let i = 1; i <= 11; i++) {
        const option = document.createElement('option');
        option.value = i;
        const startHour24 = 7 + i; // i=1 -> 8, i=11 -> 18
        const endHour24 = startHour24 + 1;
        option.textContent = `Hour ${i} (${formatHour(startHour24)} - ${formatHour(endHour24)})`;
        hourSelect.appendChild(option);
    }

    // Set default day to today
    const days = ['Su', 'M', 'T', 'W', 'Th', 'F', 'S'];
    const today = new Date().getDay();
    if (today > 0 && today < 7) {
        daySelect.value = days[today];
    } else {
        daySelect.value = 'M'; // Sunday default to Monday
    }

    // Set default hour to current time
    const currentHour = new Date().getHours();
    // 8am = hour 1, 6pm = hour 11
    // If current time is 8:30, we're in hour 1 (8-9 slot)
    if (currentHour >= 8 && currentHour <= 18) {
        const h = currentHour - 7;
        hourSelect.value = h;
    } else if (currentHour < 8) {
        hourSelect.value = 1; // Before 8am, default to first hour
    } else {
        hourSelect.value = 11; // After 7pm, default to last hour
    }

    // Configuration
    const CACHE_VERSION = 'v1';
    const CACHE_TTL = 24 * 60 * 60 * 1000; // 24 hours

    // Optimization: Cache & Parallel Loading
    async function fetchWithCache(url, key) {
        const cacheKey = `${key}_${CACHE_VERSION}`;
        const timestampKey = `${key}_ts`;

        const cached = localStorage.getItem(cacheKey);
        const timestamp = localStorage.getItem(timestampKey);
        const now = Date.now();

        if (cached && timestamp && (now - parseInt(timestamp) < CACHE_TTL)) {
            try {
                return JSON.parse(cached);
            } catch (e) {
                console.warn('Cache parse error', e);
            }
        }

        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`Failed to load ${url}`);
            const data = await response.json();

            try {
                localStorage.setItem(cacheKey, JSON.stringify(data));
                localStorage.setItem(timestampKey, now.toString());
            } catch (e) {
                console.warn('Cache write failed (likely quota exceeded)', e);
            }
            return data;
        } catch (err) {
            console.error(err);
            return null;
        }
    }

    // Parallel Loading
    Promise.all([
        fetchWithCache('room_availability.json', 'roomData'),
        fetchWithCache('courses.json', 'coursesData')
    ]).then(([rooms, courses]) => {
        if (rooms) {
            roomData = rooms;
            // findAvailableRooms(); // Disabled auto-search
        } else {
            resultsDiv.innerHTML = '<p>Error loading room data.</p>';
        }

        if (courses) {
            coursesData = courses;
        } else {
            console.error('Error loading courses data');
        }
    });

    findBtn.addEventListener('click', findAvailableRooms);

    function findAvailableRooms() {
        if (!roomData || Object.keys(roomData).length === 0) {
            resultsDiv.innerHTML = '<p>Data loading...</p>';
            return;
        }

        const selectedBuilding = buildingSelect.value;
        const selectedDay = daySelect.value;
        const selectedHour = parseInt(hourSelect.value);

        resultsDiv.innerHTML = '';

        let availableRooms = [];

        for (const [room, schedule] of Object.entries(roomData)) {
            // Filter by building
            if (selectedBuilding !== 'all') {
                const firstDigit = room.charAt(0);
                if (firstDigit !== selectedBuilding) continue;
            }

            // Check availability
            const busyHours = schedule[selectedDay] || [];
            if (!busyHours.includes(selectedHour)) {
                availableRooms.push(room);
            }
        }

        if (availableRooms.length === 0) {
            resultsDiv.innerHTML = '<p style="grid-column: 1/-1; text-align: center;">No rooms available.</p>';
            return;
        }

        // Building name mapping based on first digit
        const buildingNames = {
            '1': 'FD 1',
            '2': 'FD 2',
            '3': 'FD 3',
            '5': 'LTC',
            '6': 'NAB'
        };

        availableRooms.sort().forEach(room => {
            const firstDigit = room.charAt(0);
            const buildingName = buildingNames[firstDigit] || 'Unknown';
            const card = document.createElement('div');
            card.className = 'room-card';
            card.innerHTML = `
                <div class="room-number">${room}</div>
                <div class="status">${buildingName}</div>
            `;
            resultsDiv.appendChild(card);
        });
    }

    // ===== SEARCH FUNCTIONALITY =====
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    const searchResultsDiv = document.getElementById('searchResults');

    let coursesData = []; // Initialized empty, filled by Promise.all

    // Event Listeners for Search
    searchBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performSearch();
    });

    function performSearch() {
        if (!coursesData || coursesData.length === 0) {
            searchResultsDiv.innerHTML = '<p>Loading course data...</p>';
            return;
        }

        const query = searchInput.value.trim().toLowerCase();
        if (!query) {
            searchResultsDiv.innerHTML = '<p>Please enter a search term.</p>';
            return;
        }

        // Search by room number, course number, or course title
        const matches = coursesData.filter(course => {
            return course.room.toLowerCase().includes(query) ||
                course.course_no.toLowerCase().includes(query) ||
                course.course_title.toLowerCase().includes(query);
        });

        if (matches.length === 0) {
            searchResultsDiv.innerHTML = '<p>No matching courses found.</p>';
            return;
        }

        // Group by course_no + section to show unique courses
        const grouped = {};
        matches.forEach(m => {
            const key = `${m.course_no}-${m.section}`;
            if (!grouped[key]) {
                grouped[key] = {
                    course_no: m.course_no,
                    course_title: m.course_title,
                    instructor: m.instructor,
                    section: m.section,
                    entries: []
                };
            }
            grouped[key].entries.push({
                room: m.room,
                schedule: m.schedule,
                raw_time: m.raw_time
            });
        });

        searchResultsDiv.innerHTML = '';

        const dayNames = { M: 'Monday', T: 'Tuesday', W: 'Wednesday', Th: 'Thursday', F: 'Friday', S: 'Saturday' };

        // Create grid container for compact boxes
        const gridContainer = document.createElement('div');
        gridContainer.className = 'search-results-grid';

        Object.values(grouped).forEach(course => {
            // Get first room from entries
            const firstRoom = course.entries[0]?.room || 'N/A';

            // Create compact box
            const box = document.createElement('div');
            box.className = 'search-result-box';
            box.innerHTML = `
                <div class="box-room">${firstRoom}</div>
                <div class="box-course">${course.course_no}</div>
            `;

            // Create expandable details panel
            const detailsPanel = document.createElement('div');
            detailsPanel.className = 'details-panel';
            detailsPanel.style.display = 'none';

            // Build schedule table
            let scheduleHtml = '<table class="schedule-table"><thead><tr><th>Room</th><th>Day</th><th>Hours</th></tr></thead><tbody>';
            course.entries.forEach(entry => {
                for (const [day, hours] of Object.entries(entry.schedule)) {
                    const hoursFormatted = hours.map(h => {
                        const start = 7 + h;
                        const end = start + 1;
                        return `${formatHour(start)}-${formatHour(end)}`;
                    }).join(', ');
                    scheduleHtml += `<tr><td>${entry.room}</td><td>${dayNames[day] || day}</td><td>${hoursFormatted}</td></tr>`;
                }
            });
            scheduleHtml += '</tbody></table>';

            detailsPanel.innerHTML = `
                <h3>${course.course_no} - ${course.course_title}</h3>
                <div class="course-info">
                    <span class="label">Section:</span><span>${course.section || 'N/A'}</span>
                    <span class="label">Instructor:</span><span>${course.instructor || 'N/A'}</span>
                </div>
                ${scheduleHtml}
                <button class="close-btn">Close</button>
            `;

            // Click to expand
            box.addEventListener('click', () => {
                // Close any other open panels
                document.querySelectorAll('.details-panel').forEach(p => p.style.display = 'none');
                document.querySelectorAll('.search-result-box').forEach(b => b.classList.remove('active'));

                detailsPanel.style.display = 'block';
                box.classList.add('active');
            });

            // Close button
            detailsPanel.querySelector('.close-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                detailsPanel.style.display = 'none';
                box.classList.remove('active');
            });

            gridContainer.appendChild(box);
            gridContainer.appendChild(detailsPanel);
        });

        searchResultsDiv.appendChild(gridContainer);
    }
});
