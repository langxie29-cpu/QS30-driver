// QS30-9 REV.A9 — 三位显示模块（方案 B：独立金属管座支架 + 背置驱动 PCB）
// 参数化 OpenSCAD；所有尺寸来自 cad/QS30_parameters.json，H03 实测后改参数即可重建。
// 状态：PROVISIONAL，未在 CAD 中打开验证；不得据此加工。
tube_dia = 30.2;
tube_h = 34.0;
panel_t = 2.0;
pcb_t = 1.6;
standoff = 12.0;
pcb_w = 100.0;
pcb_h = 100.0;
socket_pitch = 38;   // TBD：H03 实测前用 38 mm 占位（禁止用于加工）
module_w = socket_pitch * 2 + tube_dia + 20;

module tube(i) {
  translate([i * socket_pitch, 0, panel_t + standoff])
    cylinder(d = tube_dia, h = tube_h, $fn = 64);
}
module metal_bracket() {
  // 金属承力支架（M1/M2 待定），仅示意：底部托板 + 两侧折边
  color("silver") difference() {
    union() {
      translate([-module_w/2, -40, 0]) cube([module_w, 80, 2]);
      translate([-module_w/2, -40, 0]) cube([2, 80, 40]);
      translate([module_w/2 - 2, -40, 0]) cube([2, 80, 40]);
    }
    for (i = [-1, 0, 1]) translate([i * socket_pitch, 0, -1])
      cylinder(d = tube_dia + 4, h = 60, $fn = 64);
  }
}
module pcb() {
  color("darkgreen") translate([-pcb_w/2, -pcb_h/2, -standoff - pcb_t])
    cube([pcb_w, pcb_h, pcb_t]);
}
module module_3tube() {
  metal_bracket();
  for (i = [-1, 0, 1]) tube(i);
  pcb();
}
module_3tube();
