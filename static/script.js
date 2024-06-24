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
    
    var checkboxes = Array.from(document.querySelectorAll('.series-checkbox'));
    
    var seriesContainer = document.getElementById('series_list');
    
    // Clear the series container
    seriesContainer.innerHTML = '';

    // Group series by rules
    var groupedSeries = {};
    checkboxes.forEach(function(checkbox) {
        var rule = checkbox.getAttribute('data-rule') || 'None';
        if (!groupedSeries[rule]) {
            groupedSeries[rule] = [];
        }
        groupedSeries[rule].push(checkbox);
    });

    // Sort each group alphabetically
    for (var rule in groupedSeries) {
        groupedSeries[rule].sort((a, b) => {
            var titleA = a.nextElementSibling ? a.nextElementSibling.textContent.toLowerCase() : '';
            var titleB = b.nextElementSibling ? b.nextElementSibling.textContent.toLowerCase() : '';
            return titleA.localeCompare(titleB);
        });
    }

    // Create and append checkboxes grouped by rules
    var rules = Object.keys(groupedSeries);

    // Prioritize the selected rule
    if (rules.includes(selectedRule)) {
        rules.splice(rules.indexOf(selectedRule), 1); // Remove selected rule from its current position
        rules.unshift(selectedRule); // Add selected rule to the top
    }

    // Move the 'None' group to the end
    if (rules.includes('None')) {
        rules.splice(rules.indexOf('None'), 1); // Remove 'None' from its current position
        rules.push('None'); // Add 'None' to the end
    }

    // Fetch the config data
    var config = JSON.parse(document.getElementById('config-data').textContent);

    rules.forEach(function(rule) {
        var ruleHeader = document.createElement('h5');
        ruleHeader.classList.add('rule-header');

        // Create a span to hold the rule details
        var ruleDetails = '';
        if (config.rules[rule]) {
            ruleDetails = ` (Get: ${config.rules[rule].get_option}, Action: ${config.rules[rule].action_option}, Keep: ${config.rules[rule].keep_watched}, Monitor Watched: ${config.rules[rule].monitor_watched})`;
        }

        ruleHeader.textContent = rule + ruleDetails;

        // Add Check/Uncheck All checkbox
        var checkUncheckAllLabel = document.createElement('label');
        checkUncheckAllLabel.textContent = ' Check/Uncheck All ';
        
        var checkUncheckAll = document.createElement('input');
        checkUncheckAll.type = 'checkbox';
        checkUncheckAll.classList.add('check-uncheck-all');
        checkUncheckAll.setAttribute('data-rule', rule);
        checkUncheckAll.addEventListener('change', function() {
            var checkboxes = groupedSeries[rule];
            checkboxes.forEach(function(checkbox) {
                checkbox.checked = checkUncheckAll.checked;
            });
        });

        var disclaimer = document.createElement('span');
        disclaimer.classList.add('disclaimer');
        disclaimer.textContent = ' (assigning will override current assignments)';

        checkUncheckAllLabel.appendChild(checkUncheckAll);
        ruleHeader.appendChild(checkUncheckAllLabel);
        ruleHeader.appendChild(disclaimer);
        seriesContainer.appendChild(ruleHeader);

        var rowDiv = document.createElement('div');
        rowDiv.classList.add('row');

        groupedSeries[rule].forEach(function(checkbox) {
            var colDiv = document.createElement('div');
            colDiv.classList.add('col-md-4', 'checkbox-item');

            // Ensure we correctly get the label element
            var label = checkbox.nextElementSibling;
            if (label && label.tagName === 'LABEL') {
                colDiv.appendChild(checkbox);
                colDiv.appendChild(label);
            }

            rowDiv.appendChild(colDiv);
        });

        seriesContainer.appendChild(rowDiv);
    });

    // Ensure the selected rule is carried over to the unassign form
    var unassignForm = document.getElementById('unassign-rules-form');
    unassignForm.querySelector('input[name="assign_rule_name"]').value = selectedRule;
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

function triggerWake() {
    fetch('/trigger-wake', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert('Wake command sent successfully.');
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
