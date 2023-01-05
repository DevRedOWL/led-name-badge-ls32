export class Drawable {
  constructor(canvas, x = 8, y = 11) {
    // Default colors
    this.bgColor = "white";
    this.fgColor = "black";
    // Units
    this.width = x;
    this.height = y;
    this.cellSize = 20;
    this.buf = [];
    // Set canvas style and size depends on cells
    canvas.width = canvas.style.width = this.width * this.cellSize;
    canvas.height = canvas.style.height = this.height * this.cellSize;
    document.querySelector("body").style.height =
      this.height * this.cellSize + 40;
    // Work with canvas
    this.context = canvas.getContext("2d");
    canvas.addEventListener("mousemove", this.onClick.bind(this), false);
    canvas.addEventListener("click", this.onClick.bind(this), false);
  }

  onClick(e) {
    const { offsetX, offsetY } = e;
    const { cellSize } = this;
    if (e.which !== 1) return;
    const x = Math.floor(offsetX / cellSize),
      y = Math.floor(offsetY / cellSize);
    try {
      this.updateBuffer(x, y, !e.shiftKey);
      this.drawAt(x, y, e.shiftKey ? this.bgColor : this.fgColor);
    } catch (ex) {}
  }

  updateBuffer(x, y, enabled) {
    this.buf[y][x] = enabled ? 1 : 0;
    // Update binary
    document.querySelector("#bin").textContent = this.buf
      .map((c1) => {
        return `\n${c1.reduce((p2, c2) => `${p2}${c2}`, "0b")}`;
      }, "")
      .toString()
      .trim();
    // Update hex
    document.querySelector("#hex").textContent = this.buf
      .map((c1) => {
        return ` 0x${parseInt(
          c1.reduce((p2, c2) => `${p2}${c2}`),
          2
        ).toString(16)}`;
      }, "")
      .toString()
      .trim();
    // Display debug in console
    console.clear();
    console.table(this.buf);
  }

  drawAt(x, y, color = this.fgColor) {
    const { context, cellSize } = this;
    context.fillStyle = color;
    context.fillRect(
      x * cellSize + 1,
      y * cellSize + 1,
      cellSize - 2,
      cellSize - 2
    );
  }

  outline() {
    const { context, cellSize, height, width } = this;
    context.strokeStyle = "lightgrey";
    for (let x = 0; x < width; ++x) {
      context.strokeRect(x * cellSize, 0, x * cellSize, cellSize * height);
    }
    for (let y = 0; y < height; ++y) {
      context.strokeRect(0, y * cellSize, cellSize * width, y * cellSize);
    }
  }

  clear() {
    const { context, cellSize, height, width } = this;
    context.clearRect(0, 0, width * cellSize, height * cellSize);
    this.outline();
    this.buf = [];
    for (let y = 0; y < height; y++) {
      this.buf.push([]);
      for (let x = 0; x < width; x++) {
        this.buf[y].push(0);
      }
    }
    this.updateBuffer(0, 0, false);
  }
}
