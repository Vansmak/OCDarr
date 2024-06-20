document.addEventListener('DOMContentLoaded', function() {
    var urlParams = new URLSearchParams(window.location.search);
    var section = urlParams.get('section');
    var message = urlParams.get('message');
    var rule = urlParams.get('rule');
    if (section) {
        showSection(section, rule);
    }
    if (message && section === 'settings') {
        var messageDiv = document.createElement('div');
        messageDiv.className = 'alert alert-success';
        messageDiv.textContent = message;
        document.getElementById(section).prepend(messageDiv);
    }

    document.getElementById('rule_name').addEventListener('change', function() {
        var newRuleNameGroup = document.getElementById('new_rule_name_group');
        if (this.value === 'add_new') {
            newRuleNameGroup.style.display = 'block';
        } else {
            newRuleNameGroup.style.display = 'none';
        }
        loadRule();
    });

    loadRule();
});

window.addEventListener('DOMContentLoaded', (event) => {
    if (window.location.search.indexOf('message=') >= 0) {
        let clean_uri = window.location.protocol + "//" + window.location.host + window.location.pathname;
        window.history.replaceState({}, document.title, clean_uri);
    }
});

function showSection(sectionId, ruleName) {
    document.querySelectorAll('.menu span, .menu img').forEach(element => {
        element.classList.remove('active');
    });

    document.querySelectorAll('div[id]').forEach(div => {
        div.style.display = 'none';
    });

    document.getElementById(sectionId).style.display = 'block';
    document.querySelector(`.menu span[onclick="showSection('${sectionId}')"]`)?.classList.add('active');
    document.querySelector(`.menu img[onclick="showSection('${sectionId}')"]`)?.classList.add('active');

    if (sectionId === 'assign_rules') {
        document.getElementById('series_list').style.display = 'block';
        if (ruleName) {
            document.getElementById('assign_rule_name').value = ruleName;
        }
        updateCheckboxes();
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
    document.getElementById('series_list').style.display = 'block';
}

function updateCheckboxes() {
    var selectedRule = document.getElementById('assign_rule_name').value;
    var checkboxes = document.querySelectorAll('.series-checkbox');
    checkboxes.forEach(function(checkbox) {
        checkbox.checked = checkbox.getAttribute('data-rule') === selectedRule;
    });
}

function confirmDeleteRule() {
    var ruleName = document.getElementById('rule_name').value;
    if (ruleName === 'default') {
        alert("The default rule cannot be deleted.");
        return false;
    }
    document.getElementById('delete_rule_name').value = ruleName;
    return confirm(`Are you sure you want to delete the rule "${ruleName}"?`);
}
