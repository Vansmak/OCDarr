function showSection(section) {
    const sections = {
        current: document.getElementById('current'),
        upcoming: document.getElementById('upcoming'),
        settings: document.getElementById('settings')
    };
    const tabs = document.querySelectorAll('.menu span');

    // Hide all sections and remove active class from all tabs
    Object.values(sections).forEach(sec => sec.style.display = 'none');
    tabs.forEach(tab => tab.classList.remove('active'));

    // Show the selected section and add active class to the clicked tab
    if (sections[section]) {
        sections[section].style.display = 'block';
        document.querySelector(`.menu span[onclick="showSection('${section}')"]`).classList.add('active');
    }
}

// Optionally, set default section to 'current' on page load if no URL parameters are used
document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const section = urlParams.get('section') || 'current';
    showSection(section);
});

