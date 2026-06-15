const majsoul_regex = /([a-z0-9]{6}-[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12})(_a\d+)?(_[0-3])?/;
const tenhou_regex = /(\d{10}gm-[0-9a-f]{4}-\d{4,}-[0-9a-f]{8})(&tw=\d+)?/;
const riichicity_regex = /([a-z0-9]{20})(@.*)?/;
const main_input = document.getElementById("main-input");
const main_button = document.getElementById("main-button");

if (main_input !== null) {
  function toggle_popouts() {
    const popouts = [...document.querySelectorAll(".input-popout")];
    if (main_input.value.match(majsoul_regex)) {
      popouts.forEach(elem => elem.classList.add("majsoul"));
      popouts.forEach(elem => elem.classList.remove("tenhou"));
      popouts.forEach(elem => elem.classList.remove("riichicity"));
    } else if (main_input.value.match(tenhou_regex)) {
      popouts.forEach(elem => elem.classList.remove("majsoul"));
      popouts.forEach(elem => elem.classList.add("tenhou"));
      popouts.forEach(elem => elem.classList.remove("riichicity"));
    } else if (main_input.value.match(riichicity_regex)) {
      popouts.forEach(elem => elem.classList.remove("majsoul"));
      popouts.forEach(elem => elem.classList.remove("tenhou"));
      popouts.forEach(elem => elem.classList.add("riichicity"));
    } else {
      popouts.forEach(elem => elem.classList.remove("majsoul"));
      popouts.forEach(elem => elem.classList.remove("tenhou"));
      popouts.forEach(elem => elem.classList.remove("riichicity"));
    }
  }

  main_input.addEventListener("keyup", toggle_popouts);
  toggle_popouts();
}
if (main_button !== null) {
  main_button.addEventListener("click", e => {main_button.innerText = "Loading...";});
}
