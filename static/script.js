// script.js
function showSection(section) {
    const current = document.getElementById('current');
    const upcoming = document.getElementById('upcoming');
    const watchingTab = document.querySelector(".menu span:first-child");
    const premieringTab = document.querySelector(".menu span:last-child");

    if (section === 'current') {
        current.style.display = 'block';
        upcoming.style.display = 'none';
        watchingTab.classList.add('active');
        premieringTab.classList.remove('active');
    } else {
        current.style.display = 'none';
        upcoming.style.display = 'block';
        watchingTab.classList.remove('active');
        premieringTab.classList.add('active');
    }
}

