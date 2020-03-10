# Change Log

## [0.7.1](https://github.com/CellProfiling/cam_acq/tree/0.7.1) (2020-03-10)
[Full Changelog](https://github.com/CellProfiling/cam_acq/compare/0.7.0...0.7.1)

**Merged pull requests:**

- Fix release workflow jobs [\#181](https://github.com/CellProfiling/cam_acq/pull/181) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Bump version to 0.7.1.dev0 [\#180](https://github.com/CellProfiling/cam_acq/pull/180) ([MartinHjelmare](https://github.com/MartinHjelmare))

## [0.7.0](https://github.com/CellProfiling/cam_acq/tree/0.7.0) (2020-03-10)
[Full Changelog](https://github.com/CellProfiling/cam_acq/compare/0.6.0...0.7.0)

**Merged pull requests:**

- 0.7.0 [\#179](https://github.com/CellProfiling/cam_acq/pull/179) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Fix release deps [\#178](https://github.com/CellProfiling/cam_acq/pull/178) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add github actions CI [\#177](https://github.com/CellProfiling/cam_acq/pull/177) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Scheduled monthly dependency update for March [\#176](https://github.com/CellProfiling/cam_acq/pull/176) ([pyup-bot](https://github.com/pyup-bot))
- Update author email [\#175](https://github.com/CellProfiling/cam_acq/pull/175) ([MartinHjelmare](https://github.com/MartinHjelmare))

## [0.6.0](https://github.com/CellProfiling/cam_acq/tree/0.6.0) (2020-02-14)
[Full Changelog](https://github.com/CellProfiling/cam_acq/compare/0.5.0...0.6.0)

**Breaking Changes:**

- Replace os.path with pathlib [\#169](https://github.com/CellProfiling/cam_acq/pull/169) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Refactor sample [\#165](https://github.com/CellProfiling/cam_acq/pull/165) ([MartinHjelmare](https://github.com/MartinHjelmare))

**Closed issues:**

- Replace str.format with f-strings [\#168](https://github.com/CellProfiling/cam_acq/issues/168)

**Merged pull requests:**

- 0.6.0 [\#174](https://github.com/CellProfiling/cam_acq/pull/174) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Use leicaimage instead of leicaexperiment [\#173](https://github.com/CellProfiling/cam_acq/pull/173) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Scheduled monthly dependency update for February [\#172](https://github.com/CellProfiling/cam_acq/pull/172) ([pyup-bot](https://github.com/pyup-bot))
- Change license to Apache 2.0 [\#171](https://github.com/CellProfiling/cam_acq/pull/171) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Make toggle automation more robust [\#170](https://github.com/CellProfiling/cam_acq/pull/170) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Convert format strings to f-strings [\#167](https://github.com/CellProfiling/cam_acq/pull/167) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Order automations functions and classes logically [\#166](https://github.com/CellProfiling/cam_acq/pull/166) ([MartinHjelmare](https://github.com/MartinHjelmare))

## [0.5.0](https://github.com/CellProfiling/cam_acq/tree/0.5.0) (2019-12-12)
[Full Changelog](https://github.com/CellProfiling/cam_acq/compare/0.4.0...0.5.0)

**Breaking Changes:**

- Remove gain plugin [\#162](https://github.com/CellProfiling/cam_acq/pull/162) ([MartinHjelmare](https://github.com/MartinHjelmare))

**Merged pull requests:**

- 0.5.0 [\#164](https://github.com/CellProfiling/cam_acq/pull/164) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Fix make\_proj [\#163](https://github.com/CellProfiling/cam_acq/pull/163) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add lint to scripts [\#161](https://github.com/CellProfiling/cam_acq/pull/161) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Fix travis pypi deploy round 2 [\#160](https://github.com/CellProfiling/cam_acq/pull/160) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Fix travis pypi deploy [\#159](https://github.com/CellProfiling/cam_acq/pull/159) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Update manifest to exclude more files [\#158](https://github.com/CellProfiling/cam_acq/pull/158) ([MartinHjelmare](https://github.com/MartinHjelmare))

## [0.4.0](https://github.com/CellProfiling/cam_acq/tree/0.4.0) (2019-12-07)
[Full Changelog](https://github.com/CellProfiling/cam_acq/compare/0.3.1...0.4.0)

**Breaking Changes:**

- Refactor to use asyncio [\#91](https://github.com/CellProfiling/cam_acq/pull/91) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Replace gain plugin with automation [\#57](https://github.com/CellProfiling/cam_acq/pull/57) ([MartinHjelmare](https://github.com/MartinHjelmare))

**Closed issues:**

- Add config validation using voluptuous [\#145](https://github.com/CellProfiling/cam_acq/issues/145)
- Add entry\_point support for plugins [\#127](https://github.com/CellProfiling/cam_acq/issues/127)
- Only fire events after calculating gain [\#117](https://github.com/CellProfiling/cam_acq/issues/117)
- Update release procedure [\#108](https://github.com/CellProfiling/cam_acq/issues/108)
- Move to asyncio core with event loop [\#92](https://github.com/CellProfiling/cam_acq/issues/92)
- Bump leicacam version to 0.2.2 [\#86](https://github.com/CellProfiling/cam_acq/issues/86)
- Move job queue to center [\#84](https://github.com/CellProfiling/cam_acq/issues/84)
- Add delay action [\#82](https://github.com/CellProfiling/cam_acq/issues/82)
- Update readme [\#76](https://github.com/CellProfiling/cam_acq/issues/76)
- Add csv sample creator file support [\#73](https://github.com/CellProfiling/cam_acq/issues/73)
- Clean up sample behavior and signatures [\#71](https://github.com/CellProfiling/cam_acq/issues/71)
- Clean up logging format output [\#70](https://github.com/CellProfiling/cam_acq/issues/70)
- Clean up child threads at stop event [\#67](https://github.com/CellProfiling/cam_acq/issues/67)
- Fire both api image events and sample image events [\#66](https://github.com/CellProfiling/cam_acq/issues/66)
- Add event\_type attribute to all events [\#64](https://github.com/CellProfiling/cam_acq/issues/64)
- Abstract the directory structure of the sample away from the plugins [\#62](https://github.com/CellProfiling/cam_acq/issues/62)
- Abstract all microscope specifics from core and plugins [\#61](https://github.com/CellProfiling/cam_acq/issues/61)
- Replace gain plugin flow with yaml automation [\#59](https://github.com/CellProfiling/cam_acq/issues/59)
- Fix main module [\#58](https://github.com/CellProfiling/cam_acq/issues/58)

**Merged pull requests:**

- Update readme [\#156](https://github.com/CellProfiling/cam_acq/pull/156) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Clean up sample action schema container [\#155](https://github.com/CellProfiling/cam_acq/pull/155) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Round gain value to integer [\#154](https://github.com/CellProfiling/cam_acq/pull/154) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Filter duplicate consecutive image replies [\#153](https://github.com/CellProfiling/cam_acq/pull/153) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Fix cmd sent future done [\#152](https://github.com/CellProfiling/cam_acq/pull/152) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Clean yaml loading in tests [\#151](https://github.com/CellProfiling/cam_acq/pull/151) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add custom cli args [\#150](https://github.com/CellProfiling/cam_acq/pull/150) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add automation config validation schema [\#149](https://github.com/CellProfiling/cam_acq/pull/149) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add leica config validation schema [\#148](https://github.com/CellProfiling/cam_acq/pull/148) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Remove sample state loading [\#147](https://github.com/CellProfiling/cam_acq/pull/147) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add config validation [\#146](https://github.com/CellProfiling/cam_acq/pull/146) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add start and stop delay [\#144](https://github.com/CellProfiling/cam_acq/pull/144) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Fix receive reply [\#143](https://github.com/CellProfiling/cam_acq/pull/143) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Fix api send service schema [\#142](https://github.com/CellProfiling/cam_acq/pull/142) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Fix plugin action type names [\#141](https://github.com/CellProfiling/cam_acq/pull/141) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Use existing sample implicitly on next well check [\#140](https://github.com/CellProfiling/cam_acq/pull/140) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Create sample helper [\#139](https://github.com/CellProfiling/cam_acq/pull/139) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Extract event match helper [\#138](https://github.com/CellProfiling/cam_acq/pull/138) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Enhance actions interface [\#137](https://github.com/CellProfiling/cam_acq/pull/137) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add vscode to gitignore [\#136](https://github.com/CellProfiling/cam_acq/pull/136) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Load plugin from config [\#135](https://github.com/CellProfiling/cam_acq/pull/135) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add pypi release to makefile [\#134](https://github.com/CellProfiling/cam_acq/pull/134) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Make leica api more robust [\#133](https://github.com/CellProfiling/cam_acq/pull/133) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Bump leicacam to 0.4.0 [\#132](https://github.com/CellProfiling/cam_acq/pull/132) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Move tests to correct location [\#131](https://github.com/CellProfiling/cam_acq/pull/131) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Move sample to plugins [\#130](https://github.com/CellProfiling/cam_acq/pull/130) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Move automations to plugins [\#129](https://github.com/CellProfiling/cam_acq/pull/129) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Move api to plugins [\#128](https://github.com/CellProfiling/cam_acq/pull/128) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Enable external plugins via entry\_points [\#126](https://github.com/CellProfiling/cam_acq/pull/126) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add Python 3.8 travis and tox env [\#125](https://github.com/CellProfiling/cam_acq/pull/125) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Fix tox [\#124](https://github.com/CellProfiling/cam_acq/pull/124) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Scheduled monthly dependency update for November [\#123](https://github.com/CellProfiling/cam_acq/pull/123) ([pyup-bot](https://github.com/pyup-bot))
- Add travis pypi deploy [\#122](https://github.com/CellProfiling/cam_acq/pull/122) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Clean up sample return values [\#121](https://github.com/CellProfiling/cam_acq/pull/121) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add a complete workflow test [\#120](https://github.com/CellProfiling/cam_acq/pull/120) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add exceptions [\#119](https://github.com/CellProfiling/cam_acq/pull/119) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Fire gain event and remove sample overwrite [\#118](https://github.com/CellProfiling/cam_acq/pull/118) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Fix docs build [\#116](https://github.com/CellProfiling/cam_acq/pull/116) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Scheduled monthly dependency update for October [\#115](https://github.com/CellProfiling/cam_acq/pull/115) ([pyup-bot](https://github.com/pyup-bot))
- Scheduled monthly dependency update for September [\#114](https://github.com/CellProfiling/cam_acq/pull/114) ([pyup-bot](https://github.com/pyup-bot))
- Update black repo urls [\#113](https://github.com/CellProfiling/cam_acq/pull/113) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Fix empty sample config [\#112](https://github.com/CellProfiling/cam_acq/pull/112) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Convert readme to markdown [\#111](https://github.com/CellProfiling/cam_acq/pull/111) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add .readthedocs.yml config file [\#110](https://github.com/CellProfiling/cam_acq/pull/110) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Fix docs build [\#109](https://github.com/CellProfiling/cam_acq/pull/109) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Update release procedure [\#107](https://github.com/CellProfiling/cam_acq/pull/107) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Bump pydocstyle to 4.0.1 [\#106](https://github.com/CellProfiling/cam_acq/pull/106) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Fix image metadata [\#105](https://github.com/CellProfiling/cam_acq/pull/105) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add requirements\_dev.txt [\#104](https://github.com/CellProfiling/cam_acq/pull/104) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Clean requirements [\#103](https://github.com/CellProfiling/cam_acq/pull/103) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Bump scipy to 1.3.1 [\#102](https://github.com/CellProfiling/cam_acq/pull/102) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Bump ruamel.yaml to 0.16.5 [\#101](https://github.com/CellProfiling/cam_acq/pull/101) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Update changelog script [\#100](https://github.com/CellProfiling/cam_acq/pull/100) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Bump pylint to 2.3.1 [\#99](https://github.com/CellProfiling/cam_acq/pull/99) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Use VERSION file to single source version [\#98](https://github.com/CellProfiling/cam_acq/pull/98) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Bump min supported Python version to 3.6 [\#97](https://github.com/CellProfiling/cam_acq/pull/97) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Bump dependencies [\#96](https://github.com/CellProfiling/cam_acq/pull/96) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add pyup [\#95](https://github.com/CellProfiling/cam_acq/pull/95) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Bump pytest and pytest-asyncio [\#94](https://github.com/CellProfiling/cam_acq/pull/94) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add template functions [\#93](https://github.com/CellProfiling/cam_acq/pull/93) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add black code formatter [\#90](https://github.com/CellProfiling/cam_acq/pull/90) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Test dev 0.4.0 round 2 [\#88](https://github.com/CellProfiling/cam_acq/pull/88) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Upgrade leicacam to version 0.2.2 [\#87](https://github.com/CellProfiling/cam_acq/pull/87) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Move job queue and run and add job methods to center [\#85](https://github.com/CellProfiling/cam_acq/pull/85) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Test dev 0.4.0 round 1 [\#83](https://github.com/CellProfiling/cam_acq/pull/83) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Use standard yaml loader/dumper to preserve config [\#80](https://github.com/CellProfiling/cam_acq/pull/80) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add delay action option in automations [\#79](https://github.com/CellProfiling/cam_acq/pull/79) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Remove old code [\#78](https://github.com/CellProfiling/cam_acq/pull/78) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Update readme [\#77](https://github.com/CellProfiling/cam_acq/pull/77) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Clean up gain calculation [\#75](https://github.com/CellProfiling/cam_acq/pull/75) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add loading of sample state from csv file [\#74](https://github.com/CellProfiling/cam_acq/pull/74) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Clean up sample method and signatures [\#72](https://github.com/CellProfiling/cam_acq/pull/72) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Clean logging [\#69](https://github.com/CellProfiling/cam_acq/pull/69) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Clean up child thread upon stop event [\#68](https://github.com/CellProfiling/cam_acq/pull/68) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Fire sample image event when sample image changes [\#65](https://github.com/CellProfiling/cam_acq/pull/65) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Refactor events [\#63](https://github.com/CellProfiling/cam_acq/pull/63) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Simplify rename image plugin [\#60](https://github.com/CellProfiling/cam_acq/pull/60) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Use new leica interface libraries [\#56](https://github.com/CellProfiling/cam_acq/pull/56) ([MartinHjelmare](https://github.com/MartinHjelmare))

## [0.3.1](https://github.com/CellProfiling/cam_acq/tree/0.3.1) (2018-05-23)
[Full Changelog](https://github.com/CellProfiling/cam_acq/compare/0.3...0.3.1)

**Merged pull requests:**

- 0.3.1 [\#81](https://github.com/CellProfiling/cam_acq/pull/81) ([MartinHjelmare](https://github.com/MartinHjelmare))

## [0.3](https://github.com/CellProfiling/cam_acq/tree/0.3) (2017-08-18)
[Full Changelog](https://github.com/CellProfiling/cam_acq/compare/0.2...0.3)

**Breaking Changes:**

- Make settings configurable from config [\#31](https://github.com/CellProfiling/cam_acq/pull/31) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Allow DNS for host [\#29](https://github.com/CellProfiling/cam_acq/pull/29) ([MartinHjelmare](https://github.com/MartinHjelmare))

**Merged pull requests:**

- 0.3 [\#34](https://github.com/CellProfiling/cam_acq/pull/34) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Update readme with latest option changes [\#33](https://github.com/CellProfiling/cam_acq/pull/33) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Move version to const.py [\#32](https://github.com/CellProfiling/cam_acq/pull/32) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Fix setting log level via cmd line or config file [\#30](https://github.com/CellProfiling/cam_acq/pull/30) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Fix bugs [\#28](https://github.com/CellProfiling/cam_acq/pull/28) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add port option [\#27](https://github.com/CellProfiling/cam_acq/pull/27) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Fix rst nested bullet syntax in readme [\#26](https://github.com/CellProfiling/cam_acq/pull/26) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Update readme with install and run instructions [\#25](https://github.com/CellProfiling/cam_acq/pull/25) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Fix missing package data [\#24](https://github.com/CellProfiling/cam_acq/pull/24) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Fix logging [\#23](https://github.com/CellProfiling/cam_acq/pull/23) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Fix typo in contributing instruction [\#22](https://github.com/CellProfiling/cam_acq/pull/22) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add contributing instructions [\#21](https://github.com/CellProfiling/cam_acq/pull/21) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add entry\_points instead of scripts [\#20](https://github.com/CellProfiling/cam_acq/pull/20) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Fix template rendering [\#19](https://github.com/CellProfiling/cam_acq/pull/19) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Merge command line arguments into config dict [\#18](https://github.com/CellProfiling/cam_acq/pull/18) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Fix bugs [\#17](https://github.com/CellProfiling/cam_acq/pull/17) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Update tox travis section to not deprecated style [\#16](https://github.com/CellProfiling/cam_acq/pull/16) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add tests for command module [\#15](https://github.com/CellProfiling/cam_acq/pull/15) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Refactor/eventbus [\#14](https://github.com/CellProfiling/cam_acq/pull/14) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Fix rst syntax in readme [\#13](https://github.com/CellProfiling/cam_acq/pull/13) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add tox testing and linting [\#12](https://github.com/CellProfiling/cam_acq/pull/12) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add Well class and refactor to use the new class [\#11](https://github.com/CellProfiling/cam_acq/pull/11) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add template feature using jinja [\#10](https://github.com/CellProfiling/cam_acq/pull/10) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Refactor control method in Control class [\#9](https://github.com/CellProfiling/cam_acq/pull/9) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Refactor image module and handling [\#8](https://github.com/CellProfiling/cam_acq/pull/8) ([MartinHjelmare](https://github.com/MartinHjelmare))

## [0.2](https://github.com/CellProfiling/cam_acq/tree/0.2) (2017-01-19)
**Merged pull requests:**

- 0.2 [\#7](https://github.com/CellProfiling/cam_acq/pull/7) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Bug fixes [\#6](https://github.com/CellProfiling/cam_acq/pull/6) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Use matrixscreener package and api [\#5](https://github.com/CellProfiling/cam_acq/pull/5) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add Sphinx docs and version string [\#4](https://github.com/CellProfiling/cam_acq/pull/4) ([MartinHjelmare](https://github.com/MartinHjelmare))
- Add formatting function [\#2](https://github.com/CellProfiling/cam_acq/pull/2) ([cwinsnes](https://github.com/cwinsnes))
