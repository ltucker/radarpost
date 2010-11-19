/*************************************************
*
*
* Javascript for the subscription management UI
*
*
**************************************************/

google.load("feeds", 1)

/*************************************
* Current subscriptions main table
**************************************/
var add_subscriptions = function(evt) {
    evt.preventDefault();
    $('#add_subscriptions').dialog("open");
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
            row.fadeOut("slow", function() {
                $(this).remove();
                mark_odd('table.subscription-list tbody tr', 'odd');
            });
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
    
    var delete_dialog_html = "<p><span class=\"warning\">Delete subscription to <strong>" + sub_name + "</strong>?</span></p>";        
    $('#delete_dialog').remove();
    $('<div id="delete_dialog"></div>')
        .html(delete_dialog_html)
    	.dialog({
    		modal: true,
    		autoOpen: true,
    		title: 'Confirm Delete Subscription',
    		width: 400,
    		buttons: {
    			'Cancel': function() {
    			    $(this).dialog("close");
    			},
    			'Delete': function() {
    			    $(this).dialog("close");
    			    do_delete();
    			},

    		}
    	});
};

var reload_subscriptions = function() {
    $('table.subscription-list').find('.edit-row').attr("disabled", "disabled");
    $('table.subscription-list').find('.delete-row').attr("disabled", "disabled");
    $('table.subscription-list').before('<span id="sub_table_spinner" class="spinner"></span>')

    var finished_reload = function() {
        mark_odd('table.subscription-list tbody tr', 'odd');
        $('#sub_table_spinner').remove();
    };

    $.ajax({
       type: 'GET',
       url: '#',
       dataType: 'html',
       success: function(data, status, result) {
           $('table.subscription-list').html(data);
           finished_reload();
       },
       error: finished_reload
    });
};

var setup_subscriptions_table = function() {
    mark_odd('table.subscription-list tbody tr', 'odd');
    $('table.subscription-list .delete-row').live('click', delete_subscription_row);
    $('table.subscription-list .edit-row').live('click', edit_subscription_row);
    $('.add-subscription').click(add_subscriptions);

};

/******************
* Feed Search
******************/

var gfeed_search_feed_url = function(query, callback) {
    /********
     * look for feeds directly at the URL specified 
     *********/
    var feed = new google.feeds.Feed(query);
    feed.setNumEntries(1);
    feed.load(function(result) {
        if (result.status.code == 200) {
            callback([{
                url: query,
                title: result.title,
                error: false
            }]);
        }
        else {
            /* oh well, just hand it back*/
            callback([{url: query, 
                       error: true
                      }]);
        }    
    });
};

var proxy_check_feed = function(query, callback) {
    $.ajax({
        type: 'GET',
        url: '/feedsearch/feed',
        data: {url: query},
        dataType: 'json',
        success: function(data, status, req) {
            if (req.status == 200) {
                callback(data);
            }
            else {
                callback({url: query,
                          error: true
                          });
            }
        },
        error: function() {
            callback({url: query, 
                      error: true
                      });        
        }});
};

var proxy_check_feed_list = function(links, callback) {
    /* check all feed links given with a chain of 
     * feed verificaitons accumulated into a list.
     */
    var i = 0; 
    var feeds = [];
    
    var get_results = function(result) {
        if (typeof result != "undefined") {
            feeds.push(result);
            i += 1;
        }

        if (i < links.length) {
            /* recurse to check next feed */
            proxy_check_feed(links[i], get_results);
        }
        else {
            /* done, hand it back */
            callback(feeds);
        }
    };
    get_results();    
};

var proxy_html_links = function(query, callback) {
    $.ajax({
        type: 'GET',
        url: '/feedsearch/html',
        data: {url: query},
        dataType: 'json',
        success: function(data, status, req) {
            if (req.status == 200) {
                callback(data);
            }
            else {
                callback([{links: [],
                           error: true
                          }]);
            }
        },
        error: function() {
            callback([{links: [],
                       error: true
                      }]);        
        }});
}

var proxy_feed_search_url = function(query, callback) {
    /*********************************************
     * use server as a proxy to search for feeds. 
     *********************************************/
     
     /* try looking for a feed */
     proxy_check_feed(query, function(results) {
         if (results.error == true) {
             /* try looking for html links */
            proxy_html_links(query, function(results) {
                if (results.error == true || results.links.length == 0) {
                    /* no dice */
                    callback([{url: query, error: true}]) 
                }
                else {
                    proxy_check_feed_list(results.links, callback);
                }
            })
         }
         else {
             callback([results]);
         }
     })
};

var feed_search_query = function(query, callback) {
    /*******************************
    * search for feeds with google
    ********************************/
    google.feeds.findFeeds(query, function(result) {
        if (result.error || result.entries.length == 0) {
            callback([{url: query, error: true}]);
        }
        else {
            var feeds = [];
            for (var i = 0; i < result.entries.length; i++) {
                var entry = result.entries[i];
                feeds.push({url: entry.url, title: entry.title});
            }
            callback(feeds);
        }
    });
};

var feed_search = function(query, callback) {  
    /*************************************************
    * chains together many methods of feed searching
    **************************************************/

    /* support feed pseudo-scheme */
    if (query.match(/^feed\:\/\//)) {
        query = 'http://' + query.substr(7);
    }
    
    if (query.match(/^http\:\/\//)) {
        gfeed_search_feed_url(query, function(results) {
            /* if no feed was found, try html */
            if (results.length == 1 && results[0].error == true) {
                proxy_feed_search_url(query, callback);
            }
            else {
                callback(results);
            }
        });
    }
    /* try a google search if this is not url-ish */
    else {
        feed_search_query(query, callback);
    }
};

/***************
* Import Table
****************/
var empty_import_list_html = 
    '<thead><tr><th class="actions"></th><th class="title">Title</th><th class="url">URL</th></tr></thead>' +
    '<tbody></tbody>';
var make_feed_row = function(row) {
    var html = "<tr>";
    html += '<td class="actions">';
    /* html += '<button class="delete-row" title="Do not add">Cancel</button>'; */
    html += '<button class="add-row" title="Add this feed">Add</button>';
    html += '</td>'
    html += '<td class="title">';
    html += '<form action="#" method="GET">';
    html += '<input name="title" type="text" ';
    if (row.title) {
        html += 'value="'+ strip_tags(row.title) + '"';
    }
    html += ' />';
    html += '<input type="hidden" name="type" value="feed" />'
    html += '<input type="hidden" name="url" value="';
    html += row.url;
    html += '" />';
    html += '</form>';
    html += '</td>';
    html += '<td class="url">';
    if (row.error == true) {
        html += '<span class="error" title="A feed was not found at this URL."></span>';
    }
    html += '<a href="' + row.url +'" title="' + row.url + '" >' + row.url + "</a></td>";
    return html;
};
var import_row = function(evt) {
    var subs_url = $("#subscriptions_rest").attr('action');
    var sub_data = {};
    $(evt.target)
        .closest('tr')
        .find("form input")
        .each(function(index, el) {
            sub_data[$(el).attr('name')] = $(el).val();
        });
    $.ajax({
        type: 'POST',
        url: subs_url,
        data: JSON.stringify(sub_data),
        dataType: 'json',
        success: function(data, status, req) {
            if (req.status == 201) {
                var td = $(evt.target).closest('tr').find('td.actions');
                td.find('.add-row').remove(); 
                /* td.find('.delete-row').remove(); 
                  td.append('<span class="empty-icon"></span>');  
                */
                td.append('<span class="okay" title="import succeeded"></span>');
            }
            else {
                alert("Failed!");
            }
        },
        error: function() {
            alert("Failed!");
        }
    });
};
var remove_import_row = function(evt) {
    var table = $(evt.target).closest("table");
    $(evt.target).closest("tr").fadeOut('slow', function() {
        $(this).remove();
        mark_odd(table.find('tbody tr'), 'odd');
    });
};
var setup_import_list = function(el, results) {
    $(el).html(empty_import_list_html);
    var seen_feeds = {};
    var tbody = $(el).find('tbody');
    $.each(results, function(index, row) {
        if (row.url && !seen_feeds[row.url]) {
            seen_feeds[row.url] = true;
            tbody.append(make_feed_row(row));
        }
    });
    mark_odd($(el).find('tbody tr'), 'odd');
};

var setup_subscriptions_dialog = function() {
    $('#add_subscriptions').dialog({
		modal: true,
		autoOpen: false,
		title: 'Add Subscriptions',
		width: 600,
		height: 400,
		buttons: {
			'Done': function() {
			    $(this).dialog("close");
			    reload_subscriptions();
			}
		}
	});
    $('#add_subscriptions > div').tabs();

    $('.import-list .add-row').live("click", import_row);
    $('.import-list .delete-row').live("click", remove_import_row);


    var search_inactive = function() {
        $('#feed_search .spinner').remove();
        $('#feed_search button.cancel').remove();
        $("#feed_search button.search").removeAttr("disabled");
        $("#feed_query").removeAttr("disabled", "disabled");
    };
    var search_active = function() {
        $("#feed_search button.search").attr("disabled", "disabled");
        $("#feed_query").attr("disabled", "disabled");
        $('#add_subscriptions .help').remove();
        $('#add_subscriptions button.search').after('<button class="cancel">Cancel</button><span class="spinner"></span>');        
    };
    var search_sequence = 0;    
    var do_feed_search = function(evt) {
        evt.preventDefault();
        search_active();
        query = $('#feed_query').val();
        search_sequence += 1;
        var my_sequence = search_sequence;
        feed_search(query, function(results) {
            if (search_sequence == my_sequence) {
                setup_import_list('#feed_search .import-list', results);
                search_inactive();
            }
        });
    };
    var cancel_feed_search = function(evt) {
        /* signal that any pending search results should be 
         * discarded by changing the sequence number.
         */
        search_sequence += 1;
        search_inactive();
    };
    
    $('#feed_search button.search').click(do_feed_search);
    $('#feed_search form').submit(do_feed_search);
    $('#feed_search button.cancel').live('click', cancel_feed_search);
};


/*********************************************************/

$(document).ready(function() {
    setup_subscriptions_table();
    setup_subscriptions_dialog();
});