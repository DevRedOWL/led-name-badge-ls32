import { Drawable } from "./drawable.js";

const canvas = new Drawable(document.querySelector("#canvas-1 canvas"));
canvas.clear();

document.body.onkeyup = function (e) {
  if (
    (e.key === " " || e.code === "Space" || e.keyCode === 32) &&
    e.shiftKey === true
  ) {
    canvas.clear();
  }
};
