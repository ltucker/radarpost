var gettext = function(str) {
    return str;
};

var show_error = function(elid, message) {
    $('#' + elid + '_error').attr('innerHTML', message);
};
