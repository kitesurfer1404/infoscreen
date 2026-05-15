const websocket_path = "/ctrl/ws";
var last_active_img = "";

function set_active_image(img) {
  if(last_active_img != img) {
    update_active_image(img);
    last_active_img = img;
    scroll_to_active_image();
  }
}

const register_image_click = (mutationList, observer) => {
  for(const mutation of mutationList) {
    if(mutation.type === "childList") {
      let gallery = mutation.addedNodes[0];
      let images = gallery.children;
      if(images != null) {
        for(var i=0; i<images.length; i++) {
          images[i].addEventListener("click", image_clicked);
          if(i>0) {
            //console.log(images[i]);
            images[i].classList.add("hidden");
          }
        }
      }
    }
  }
};

function register_button_click() {
  var buttons = document.getElementsByTagName("button");
  for(var i=0; i<buttons.length; i++) {
    buttons[i].addEventListener("click", button_clicked);
  }
}

function scroll_to_top() {
  document.body.scrollTop = 0; // For Safari
  document.documentElement.scrollTop = 0; // For Chrome, Firefox, IE and Opera
}

function scroll_to_active_image() {
  let active_image = document.querySelector('.gallery img[active="true"]');
  if(active_image != null) {
    active_image.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

function show_all_galleries() {
  document.getElementsByTagName("header")[0].classList.add("hidden");
  document.getElementsByTagName("footer")[0].classList.add("hidden");

  let galleries = document.getElementsByClassName("gallery");
  for(let i=0; i < galleries.length; i++) {
    let images = galleries[i].children;
    for(let j=1; j<images.length; j++) {
      images[j].classList.add("hidden");
    }
    galleries[i].classList.remove("hidden");
  }
  scroll_to_top();
}

function hide_all_galleries() {
  let galleries = document.getElementsByClassName("gallery");
  for(let i=0; i < galleries.length; i++) {
    galleries[i].classList.add("hidden");
  }
}

function open_gallery(src) {
  document.getElementsByTagName("header")[0].classList.remove("hidden");
  document.getElementsByTagName("footer")[0].classList.remove("hidden");

  let target_image = document.querySelector('.gallery img[src="' + src + '"]');
  if(target_image != null) {
    let active_gallery = target_image.parentElement;
    active_gallery.classList.toggle("hidden");
    images = active_gallery.children;
    for(let i=1; i<images.length; i++) {
      images[i].classList.remove("hidden");
    }
  }
}

function send_active_image(src) {
  socket.send("setactive:" + src);
}

function next_prev_image(direction) {
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
    
    active_index = active_index + direction;

    if(active_index == images.length || active_index == -1) {
      if(loop == "true" ) {
        active_index = (images.length + (active_index % images.length)) % images.length;
      } else {
        active_index = active_index - direction;
      }
    }

    images[active_index].setAttribute("active", "true");
    
    let src = images[active_index].getAttribute("src");
    send_active_image(src);
    update_active_image(src);
  }
}

function image_clicked(e) {
  var src = e.target.getAttribute("src");

  var hidden_galleries = document.getElementsByClassName("gallery hidden");
  if(hidden_galleries.length == 0) {
    hide_all_galleries();
    open_gallery(src);
  } else {
    update_active_image(src);
    send_active_image(src);
    scroll_to_active_image();
  }
}

function button_back_clicked() {
  show_all_galleries();
}

function button_prev_clicked() {
  next_prev_image(-1);
  scroll_to_active_image();
}

function button_next_clicked() {
  next_prev_image(1);
  scroll_to_active_image();
}

function button_clicked(e) {
  switch(e.target.id) {
    case "back":
      button_back_clicked();
      break;
    case "prev":
      button_prev_clicked();
      break;
    case "next":
      button_next_clicked();
      break;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const imagelist = document.getElementById("imagelist");
  const observer_config = { childList: true };
  const observer = new MutationObserver(register_image_click);
  observer.observe(imagelist, observer_config);
  
  register_button_click();  
  
  init_websocket(websocket_path);
  
  socket.send("getcontent");
  socket.send("getactive");
});
