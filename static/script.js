function showSection(section) {
    const sections = ['current', 'upcoming', 'settings'];
    const tabs = document.querySelectorAll('.menu span');

    sections.forEach(sec => {
        document.getElementById(sec).style.display = 'none';
    });
    tabs.forEach(tab => {
        tab.classList.remove('active');
    });

    document.getElementById(section).style.display = 'block';
    document.querySelector(`.menu span[onclick="showSection('${section}')"]`).classList.add('active');
}

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

    if (!sonarrAvailable) {
        triggerWake();
    }
});

function triggerWake() {
    fetch('/trigger-wake', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert('Wake command sent successfully. Please wait a moment and refresh the page.');
        } else {
            alert('Failed to send wake command.');
        }
    })
    .catch(error => {
        alert('Failed to send wake command.');
    });
}

function refreshPlex() {
    fetch('/refresh-plex', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert('Plex refresh command sent successfully.');
        } else {
            alert('Failed to send Plex refresh command.');
        }
    })
    .catch(error => {
        alert('Failed to send Plex refresh command.');
    });
}
