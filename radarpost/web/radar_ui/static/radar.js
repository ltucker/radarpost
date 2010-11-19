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

/*var inorder_traverse = function(els, visit) {
    if (typeof(els) == "undefined" || els.size() == 0) {
        return;
    }
    els.each(function() {
        var cur = $(this); 
        visit(cur);
        inorder_traverse(cur.children());
    });
};*/

var strip_tags = function(html) {
    return $('<div></div>').html(html).text();
};