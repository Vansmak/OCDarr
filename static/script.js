function showSection(section) {
    const sections = ['current', 'prime', 'upcoming', 'settings'];
    const tabs = document.querySelectorAll('.menu span');

    // Hide all sections and remove the active class from all tabs
    sections.forEach(sec => {
        document.getElementById(sec).style.display = 'none';
    });
    tabs.forEach(tab => {
        tab.classList.remove('active');
    });

    // Show the selected section and add active class to the corresponding tab
    document.getElementById(section).style.display = 'block';
    document.querySelector(`.menu span[onclick="showSection('${section}')"]`).classList.add('active');
}

// Set default section on page load based on URL parameters
document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const section = urlParams.get('section') || 'current';
    const message = urlParams.get('message');

    showSection(section);

    if (message && section === 'settings') {
        var messageDiv = document.createElement('div');
        messageDiv.className = 'alert alert-success';
        messageDiv.textContent = message;
        document.getElementById(section).prepend(messageDiv);
    }

    if (window.location.search.indexOf('message=') >= 0) {
        let clean_uri = window.location.protocol + "//" + window.location.host + window.location.pathname;
        window.history.replaceState({}, document.title, clean_uri);
    }
});

function markAsWatched(seriesId, episodeId) {
    fetch(`/mark-watched/${seriesId}/${episodeId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Episode marked as watched!');
        } else {
            alert('Failed to update episode status.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to update episode status.');
    });
}

function fetchLogs(logType) {
    fetch(`/logs?type=${logType}`)
        .then(response => response.json())
        .then(data => {
            document.getElementById('logContent').textContent = data.logs;
            showLogs(); // Show the logs after fetching them
        })
        .catch(error => {
            console.error('Error fetching logs:', error);
            document.getElementById('logContent').textContent = 'Failed to load logs.';
        });
}

function showLogs() {
    document.getElementById('logContent').style.display = 'block';
}

function hideLogs() {
    document.getElementById('logContent').style.display = 'none';
}


function triggerWake() {
    fetch('http://192.168.254.64:8123/api/webhook/wakeoffice', {
        method: 'POST'
    })
    .then(response => {
        if (response.ok) {
            alert('Wake command sent successfully.');
        } else {
            throw new Error('Failed to send wake command.');
        }
    })
    .catch(error => {
        alert('Error sending wake command: ' + error.message);
    });
}
