document.addEventListener('DOMContentLoaded', function() {
    var urlParams = new URLSearchParams(window.location.search);
    var section = urlParams.get('section');
    var message = urlParams.get('message');
    if (section) {
        showSection(section);
    }
    if (message && section === 'settings') {
        var messageDiv = document.createElement('div');
        messageDiv.className = 'alert alert-success';
        messageDiv.textContent = message;
        document.getElementById(section).prepend(messageDiv);
    }

    // Add event listener to rule_name select to handle new rule input visibility
    document.getElementById('rule_name').addEventListener('change', function() {
        var newRuleNameGroup = document.getElementById('new_rule_name_group');
        if (this.value === 'add_new') {
            newRuleNameGroup.style.display = 'block';
        } else {
            newRuleNameGroup.style.display = 'none';
        }
        loadRule();
    });

    // Ensure series list is displayed correctly when "Assign Rules" section is shown
    document.getElementById('series_list').style.display = 'block';

    // Call loadRule to initialize form fields based on selected rule
    loadRule();
});

window.addEventListener('DOMContentLoaded', (event) => {
    if (window.location.search.indexOf('message=') >= 0) {
        let clean_uri = window.location.protocol + "//" + window.location.host + window.location.pathname;
        window.history.replaceState({}, document.title, clean_uri);
    }
});

function showSection(sectionId) {
    document.querySelectorAll('.menu span, .menu img').forEach(element => {
        element.classList.remove('active');
    });

    document.querySelectorAll('div[id]').forEach(div => {
        div.style.display = 'none';
    });

    document.getElementById(sectionId).style.display = 'block';
    document.querySelector(`.menu span[onclick="showSection('${sectionId}')"]`)?.classList.add('active');
    document.querySelector(`.menu img[onclick="showSection('${sectionId}')"]`)?.classList.add('active');

    // Ensure series list is displayed correctly when "Assign Rules" section is shown
    if (sectionId === 'assign_rules') {
        document.getElementById('series_list').style.display = 'block';
    }
}

function loadRule() {
    var ruleName = document.getElementById('rule_name').value;
    var config = JSON.parse(document.getElementById('config-data').textContent);
    var rule = config.rules[ruleName];

    document.getElementById('get_option').value = rule ? rule.get_option : '';
    document.getElementById('action_option').value = rule ? rule.action_option : '';
    document.getElementById('keep_watched').value = rule ? rule.keep_watched : '';
    document.getElementById('monitor_watched').value = rule ? rule.monitor_watched.toString() : 'false';
}
