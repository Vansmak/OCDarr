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
    var ruleNameElement = document.getElementById('rule_name');
    if (ruleNameElement) {
        ruleNameElement.addEventListener('change', function() {
            var newRuleNameGroup = document.getElementById('new_rule_name_group');
            if (this.value === 'add_new') {
                newRuleNameGroup.style.display = 'block';
            } else {
                newRuleNameGroup.style.display = 'none';
            }
            loadRule();
        });
    }

    // Add event listener to delete rule button
    var deleteRuleButton = document.getElementById('delete_rule');
    if (deleteRuleButton) {
        deleteRuleButton.addEventListener('click', function(event) {
            event.preventDefault();
            var ruleName = document.getElementById('rule_name').value;
            if (ruleName === 'default') {
                alert("Default rule cannot be deleted.");
                return;
            }
            document.getElementById('delete_rule_name').value = ruleName;
            document.getElementById('delete-rule-form').submit();
        });
    }

    // Call loadRule to initialize form fields based on selected rule
    loadRule();
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
}

function loadRule() {
    console.log("loadRule function called");
    var ruleName = document.getElementById('rule_name').value;
    var config = JSON.parse(document.getElementById('config-data').textContent);
    console.log("Selected rule:", ruleName);
    console.log("Config:", config);
    var rule = config.rules[ruleName];
    console.log("Rule:", rule);

    if (rule) {
        document.getElementById('get_option').value = rule.get_option;
        document.getElementById('action_option').value = rule.action_option;
        document.getElementById('keep_watched').value = rule.keep_watched;
        document.getElementById('monitor_watched').value = rule.monitor_watched.toString();
    } else {
        console.error("Rule '" + ruleName + "' not found.");
    }
}
