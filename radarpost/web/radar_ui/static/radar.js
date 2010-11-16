var gettext = function(str) {
    return str;
};

var show_error = function(elid, message) {
    $('#' + elid + '_error').attr('innerHTML', message);
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



