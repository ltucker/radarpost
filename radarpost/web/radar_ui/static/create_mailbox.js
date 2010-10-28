var title_to_slug = function(title) {
    var slug = title.toLowerCase();
    slug = slug.replace(/\s/g, '_');
    slug = slug.replace(/[^a-z0-9_]/g, '');
    if (slug.length > 128) {
        slug = slug.substring(0, 128);
    }
    return slug;
};
var valid_slug_re = new RegExp('^[a-z0-9_]{1,128}$');

$(document).ready(function() {  
    var slug_customized = false;
    $('#mailbox_name').keyup(function(ev) {
        if (slug_customized) {
            return;
        }
        $('#mailbox_slug').attr('value', title_to_slug(this.value));
    });

    $('#mailbox_slug').keyup(function(ev) {
        if (this.value) {
            slug_customized = true;
        }
        else {
            slug_customized = false;
        }
    });

    var try_create = function() {
        // go ahead and try to create it.
        var slug = $('#mailbox_slug').attr('value');
        var mb_info = {
            title: $('#mailbox_name').attr('value')
        };

        $.ajax({
            type: 'PUT',
            url: '/' + slug,
            contentType: 'application/json',
            data: JSON.stringify(mb_info),
            complete: function(req) {
                if (req.status == '201') {
                    /* created */
                    window.location.pathname = '/' + slug
                }
                else if (req.status == '409') {
                    show_error('mailbox_slug', 'This url is already in use.');
                }
                else if (req.status == '400') {
                    show_error('mailbox_name', 'Invalid name.')
                }
                else {
                    show_error('mailbox_slug', 'Could not create a mailbox at the specified location.')
                }
            }
        });
    };

    var do_create = function() {
        var slug = $('#mailbox_slug').attr('value');
        if (slug.length < 1) {
            return show_error('mailbox_slug', 'please provide a url.');
        }
        if (slug.length > 128) {
            return show_error('mailbox_slug', 'maximum length is 128 characters.');
        }
        if (valid_slug_re.exec(slug) == null) {
            return show_error('mailbox_slug', 'invalid url, must contain only lowercase letters, numbers and _');
        }

        $.ajax({
            type: 'HEAD',
            url: '/' + slug,
            complete: function(req) {
                if (req.status != 404) {
                    return show_error("mailbox_slug", 'This url is reserved or already in use.');
                }
                else {
                    try_create();
                }
            }
        });
    };

    $('#create_form').submit(function(ev) {
        ev.preventDefault();
        do_create();
    });
    $('#create_mailbox').click(function(ev) {
        ev.preventDefault();
        do_create();
    });
});