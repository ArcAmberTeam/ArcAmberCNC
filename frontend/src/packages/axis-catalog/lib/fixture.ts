import program from './sample.ngc?raw';

export const sampleProgram = program.trimEnd().split('\n');
export const fixture = Object.freeze({
  fileName: 'axis.ngc',
  machine: 'LinuxCNC-HAL-SIM-AXIS',
  version: '2.9.10',
  taskState: '急停',
  tool: '未装刀',
  activeCodes: 'G0 G17 G21 G40 G49 G54 G64 G80 G90 G91.1 G94 G97 G98\nM5 M9 M48  F0.0 S0.0',
  history: Object.freeze(['G0 X0 Y0', 'G0 Z10', 'G54']),
});
