# BetterLinuxCNC Web

当前维护的界面在 [`frontend/`](frontend/README.md)，采用 Vue 3 + TypeScript，按业务模块划分边界。原生 AXIS 的项目样式定制已撤回；现有 Web 原型独立保留，尚未接入机床控制。

入口：[架构规范](AGENT.md) · [Web 开发说明](frontend/README.md) · [Web CI](.github/ci/README.md) · [测试环境部署与迁移](.github/staging/README.md)。CI/CD 只检查、构建和部署静态 Web；下面保留 LinuxCNC 上游说明，供后续控制引擎开发参考。

[![Badge GPL2]][License]
[![Badge LGPL]][License]

<div align = center>

<br>
  
# LinuxCNC
  
*Controlling CNC Machines*

<br>
  
[![Badge Translation]][Translation]
  
<br>
  
---

[<kbd> <br> Ｗｅｂｓｉｔｅ <br> </kbd>][Website] 
[<kbd> <br> Ｉｎｓｔａｌｌ <br> </kbd>][Ｉｎｓｔａｌｌ] 
[<kbd> <br> Ｂｕｉｌｄ <br> </kbd>][Ｂｕｉｌｄ] 
[<kbd> <br> Ｄｏｃｕｍｅｎｔａｔｉｏｎ <br> </kbd>][Ｄｏｃｕｍｅｎｔａｔｉｏｎ]  
  
---

<br>
  
It can drive milling machines, lathes, 3D printers, laser <br>
cutters, plasma cutters, robot arms, hexapods, and more.

LinuxCNC was initiated 25 years ago and evolved into a very <br>
international project with contributions from all over the globe.
  
With release 2.9 of LinuxCNC we also transitioned the <br>
documentation to the use of the public crowd translation <br>
services [Weblate] and invite all our users to contribute.
  
The translations we expect to help attract practitioners <br>
to the project and also helps educating enthusiasts of <br>
all age groups on automated machining.

<br>

## DISCLAIMER
  
<br>

```
  
Ｔｈｅ ａｕｔｈｏｒｓ ｏｆ ｔｈｉｓ ｓｏｆｔｗａｒｅ ａｃｃｅｐｔ
ａｂｓｏｌｕｔｅｌｙ ｎｏ ｌｉａｂｉｌｉｔｙ ｆｏｒ ａｎｙ
ｈａｒｍ　ｏｒ ｌｏｓｓ ｒｅｓｕｌｔｉｎｇ ｆｒｏｍ ｉｔｓ ｕｓｅ．

Ｉｔ ｉｓ ＥＸＴＲＥＭＥＬＹ ｕｎｗｉｓｅ ｔｏ　ｒｅｌｙ
ｏｎ ｓｏｆｔｗａｒｅ ａｌｏｎｅ ｆｏｒ ｓａｆｅｔｙ．

Any machinery capable of harming persons must have
provisions for completely removing power from all
motors, etc., before persons enter any danger area.

All machinery must be designed to comply with local 
and national safety codes, and the authors of this 
software cannot and do not, take any responsibility 
for such compliance.
  
```

<br>
  
</div>

<!----------------------------------------------------------------------------->

[Badge Translation]: https://hosted.weblate.org/widgets/linuxcnc/-/svg-badge.svg
[Badge GPL2]: https://img.shields.io/badge/Most-LGPL_3-blue.svg?style=for-the-badge 'The license this software is under'
[Badge LGPL]: https://img.shields.io/badge/Some-GPL_2-blue.svg?style=for-the-badge 'Some parts are under this license'

[Translation]: https://hosted.weblate.org/engage/linuxcnc/
[Weblate]: https://hosted.weblate.org/projects/linuxcnc/
[Website]: https://linuxcnc.org/

[Ｄｏｃｕｍｅｎｔａｔｉｏｎ]: http://linuxcnc.org/docs/2.9/html/
[Ｉｎｓｔａｌｌ]: http://linuxcnc.org/docs/2.9/html/getting-started/getting-linuxcnc.html
[Ｂｕｉｌｄ]: http://linuxcnc.org/docs/2.9/html/code/building-linuxcnc.html
[License]: COPYING
