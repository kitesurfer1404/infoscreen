const websocket_path = "/ws";

var last_active_img = "";
var slideshow_interval;

function set_active_image(img) {
  if(last_active_img != img) {
    update_active_image(img);
    update_display(img);
    last_active_img = img;
    slideshow_setup();
  }
}

function update_display(src) {
    let current_image = document.querySelector("#display img:not(.hidden)");
    let hidden_image = document.querySelector("#display img.hidden");
    let current_src = current_image.getAttribute("src");

    if(current_src != src) {
      hidden_image.setAttribute("src", src);
      current_image.classList.toggle('hidden');
      hidden_image.classList.toggle('hidden');
    }
}

function slideshow_setup() {
  window.clearInterval(slideshow_interval);
  
  let active_image = document.querySelector('.gallery img[active="true"]');
  if(active_image != null) {
    active_gallery = active_image.parentElement;
    let autorun = active_gallery.getAttribute("autorun");
    if(autorun == "true") {
      let delay = parseInt(active_gallery.getAttribute("delay")) * 1000;
      slideshow_interval = window.setInterval(slideshow_run, delay);
    }
  }
}

function slideshow_run() {
  let active_image = document.querySelector('.gallery img[active="true"]');
  
  if(active_image != null) {
    active_gallery = active_image.parentElement;

    let loop = active_gallery.getAttribute("loop");
    let images = active_gallery.children;
    let active_index = 0;
  
    for(var i=0; i<images.length; i++) {
      let img = images[i];
      if(img.hasAttribute("active")) {
        active_index = i;
        break;
      }
    }
  
    images[active_index].removeAttribute("active");

    if(active_index == images.length - 1) {
      if(loop == "true" ) {
        active_index = 0;
      }
    } else {
      active_index++;
    }

    images[active_index].setAttribute("active", "true");
    update_active_image(images[active_index].getAttribute("src"));
    update_display(images[active_index].getAttribute("src"));
  }
}

document.addEventListener("DOMContentLoaded", () => {
  init_websocket(websocket_path);
  
  socket.send("getcontent");
  socket.send("getactive");
});
