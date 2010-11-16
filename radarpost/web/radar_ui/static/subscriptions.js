var recolor_table = function() {
    mark_odd('table.subscription-list tbody tr', 'odd');
};

var edit_subscription_row = function(evt) {
    evt.preventDefault();
    
    var sub_url = $(evt.target).find('a').attr('href');
    var row = $(evt.target).closest('tr');
    var sub_name = row.find('.subscription-title').attr('title');

    var do_edit = function() {
        var dlg = $(this);
        $.ajax({
            type: 'POST',
            url: sub_url,
            data: $(this).find("form").first().serialize(),
            dataType: 'json',
            success: function(data, status, req) {
                if (req.status == 200) {
                    row.find('.subscription-title')
                        .attr('title', data.title)
                        .html(data.title);
                    dlg.dialog("close");
                }
                else {
                    show_form_error("sub_edit", "Failed to update subscription");
                }
            },
            error: function() {
                show_form_error("sub_edit", "An error occurred updating the subscription.");
            }
        });
    };

    var edit_html = '<form action="#" method="GET">' +
                    '<span class="form-error" id="sub_edit_error"></span>' +
                    '<label for="edit_sub_name">Title</label>' + 
                    '<input id="edit_sub_name" type="text" name="title" value="' + sub_name + '"/>' + 
                    '</form>';

    $('#edit_dialog').remove();
    $('<div id="edit_dialog"></div>')
        .html(edit_html)
        .submit(function(evt) {
            evt.preventDefault();
        })
        .dialog({
            modal: true,
            autoOpen: true, 
            title: 'Edit Subscription',
            width: 280,
            buttons: {
                'Ok': do_edit,
                'Cancel': function() {
                    $(this).dialog("close");
                }
            }
        });
};

var delete_subscription_row = function(evt) {
    evt.preventDefault();

    var sub_url = $(evt.target).find('a').attr('href');
    var row = $(evt.target).closest('tr');
    var sub_name = row.find('.subscription-title').attr('title');

    var handle_delete_response = function(req) {
        if (req.status == 200) {
            row.remove();
            recolor_table();
        }
        else {
            error_alert('Failed to delete subscription!');            
        }        
    };

    var do_delete = function() {
        $.ajax({
            type: 'DELETE',
            url: sub_url,
            complete: handle_delete_response
        });
    };
    
    var delete_dialog_html = "<p><span class=\"ui-icon ui-icon-alert dialog-icon\"></span>Delete subscription to <strong>" + sub_name + "</strong>?</p>";        
    $('#delete_dialog').remove();
    $('<div id="delete_dialog"></div>')
        .html(delete_dialog_html)
    	.dialog({
    		modal: true,
    		autoOpen: true,
    		title: 'Confirm Delete Subscription',
    		width: 400,
    		buttons: {
    			'Delete': function() {
    			    $(this).dialog("close");
    			    do_delete();
    			},
    			'Cancel': function() {
    			    $(this).dialog("close");
    			}
    		}
    	});
};

$(document).ready(function() {
    recolor_table();
    $('table.subscription-list .delete-button').live('click', delete_subscription_row);
    $('table.subscription-list .edit-button').live('click', edit_subscription_row);
});
