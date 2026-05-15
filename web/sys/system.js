var socket;

function init_websocket(websocket_path) {
  var websocket_url = "";
  var loc = window.location;
  
  if(loc.protocol === "https:") {
    websocket_url = "wss:";
  } else {
    websocket_url = "ws:";
  }
  websocket_url += "//" + loc.host + websocket_path;

  socket = new RobustWebSocket(websocket_url);
  
  socket.on("open", () => {
    console.log("WS: Connected");
    setStatus("Connected", true);
    socket.send("getactive");  // get active image, if we missed somethin while disconnected
  });

  socket.on("close", () => {
    console.log("WS: Connection closed (reconnecting...)");
    setStatus("Disconnected", false);
  });

  socket.on("message", (msg) => {
    console.log("WS: Message: " + msg);

    if(msg.startsWith("content:")) {
      json_str = msg.replace(/^content:/, '');
      load_content(json_str);
    }
    
    if(msg.startsWith("active:")) {
      set_active_image(msg.replace(/^active:/, ''));
    }
    
    if(msg.startsWith("reload:")) {
      location.reload();
    }
  });

  socket.on("error", (err) => {
    console.log("WS Error: " + err);
  });
}

function setStatus(text, connected) {
    const statusEl = document.getElementById("status");
    statusEl.textContent = text;
    statusEl.className = "status " + (connected ? "connected" : "disconnected");
}

function load_content(json_str) {
  var json = 0;

  try {
    json = JSON.parse(json_str);
  } catch(e) {
    console.error(e);
    return;
  }
  console.log(json);

  var len = json.content.length;

  const imagecache = document.getElementById("imagelist");

  json.content.forEach((item) => {
    let g = "";
    
    try {
      g = JSON.parse(item);
    } catch(e) {
      //console.error(e);
      return;
    }

    let gallery = document.createElement("div");
    gallery.setAttribute("class", "gallery");
    gallery.setAttribute("autorun", g.autorun);
    gallery.setAttribute("loop", g.loop);
    gallery.setAttribute("delay", g.delay);

    g.images.forEach((img) => {
      //console.log(g.path + "/" + img);
      let elem = document.createElement("img");
      elem.setAttribute("src", g.path + "/" + img);
      elem.setAttribute("alt", img);
      gallery.appendChild(elem);
    })

    imagecache.appendChild(gallery);
  });
}

function update_active_image(src) {
  try {
    let active_images = document.querySelectorAll('.gallery img[active="true"]');
    if(active_images != null) {
      for(let i=0; i<active_images.length; i++) {
        active_images[i].removeAttribute("active");
      }
    }
    let target_image = document.querySelector('.gallery img[src="' + src + '"]');
    target_image.setAttribute("active", "true");
  } catch(e) {
    //console.error(e);
    return;
  }
}
