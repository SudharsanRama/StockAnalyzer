// Empty JS for your own code to be here
$(function() {
  $('#uploadButton').click(function() {
      var form_data = new FormData($('#upload-file')[0]);
      $.ajax({
          type: 'POST',
          url: '/upload',
          data: form_data,
          contentType: false,
          cache: false,
          processData: false,
          success: function(data) {
              displayList(data);
          },
      });
  });
});

function displayList(list){
    $('#stockList').empty();
    list.forEach(l => {
        var item = $('#templates').find(".nav-item").clone();
        item.find(".nav-link").html(l);
        $('#stockList').append(item);
    });
}