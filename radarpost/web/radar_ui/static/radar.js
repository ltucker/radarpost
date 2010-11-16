var gettext = function(str) {
    return str;
};

var show_form_error = function(elid, message) {
    $('#' + elid + '_error').html(message);
};

var error_alert = function(message) {
    $('<div></div>')
        .html(message)
        .dialog({
            modal: true,
            autoOpen: true,
            title: "Error",
            buttons: {
                'Ok': function() {$(this).dialog("close");}
            }
        });
};

var mark_odd = function(selector, classname) {
    $(selector).each(function(index, el) {
       if (index % 2 == 1) {
           $(el).addClass(classname);
       }
       else {
           $(el).removeClass(classname);
       }
    });
};

