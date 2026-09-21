// @ts-check
// Keep interface privacy separate from the project-specific dependency layers.
const PACKAGES_ROOT = 'src/packages';
const R = PACKAGES_ROOT;
const PACKAGE_INTERNALS = `^${R}/[^/]+/[^/]+/`;

const packageDependencies = {
  'controller-session': [],
  'axis-catalog': [],
  'ui-system': [],
  'axis-presentation': ['axis-catalog'],
  'manual-control': ['axis-catalog', 'axis-presentation', 'ui-system'],
  'toolpath-view': ['axis-catalog', 'axis-presentation', 'ui-system'],
  'program-view': ['axis-catalog', 'axis-presentation', 'ui-system'],
  'axis-chrome': [
    'axis-catalog',
    'axis-presentation',
    'ui-system',
    'manual-control',
    'toolpath-view',
  ],
};

const registeredPackages = Object.keys(packageDependencies).join('|');
const unregisteredPackage = `^${R}/(?!(?:${registeredPackages})/)[^/]+/`;

/** @type {import('dependency-cruiser').IConfiguration} */
module.exports = {
  forbidden: [
    {
      name: 'tauri-control-api-is-private',
      comment: 'Only the control session may call the desktop control bridge.',
      severity: 'error',
      from: { path: '^src/', pathNot: `^${R}/controller-session/` },
      to: { path: 'node_modules/@tauri-apps/' },
    },
    {
      name: 'entrypoint-boundary-from-app',
      comment: 'App, pages and external tests may use package root entry points only.',
      severity: 'error',
      from: { pathNot: `^${R}/` },
      to: { path: PACKAGE_INTERNALS },
    },
    {
      name: 'entrypoint-boundary-across-packages',
      comment: 'Cross-package imports must target root entry points, including type imports.',
      severity: 'error',
      from: { path: `^${R}/([^/]+)/`, pathNot: `^${R}/[^/]+/tests/` },
      to: { path: PACKAGE_INTERNALS, pathNot: `^${R}/$1/` },
    },
    {
      name: 'tests-through-entrypoints',
      comment: 'Package tests may use public interfaces and only their own test fixtures.',
      severity: 'error',
      from: { path: `^${R}/([^/]+)/tests/` },
      to: { path: PACKAGE_INTERNALS, pathNot: `^${R}/$1/tests/` },
    },
    {
      name: 'tests-folder-is-private',
      comment: 'Production code must not import package tests or fixtures.',
      severity: 'error',
      from: { pathNot: `^${R}/[^/]+/tests/` },
      to: { path: `^${R}/[^/]+/tests/` },
    },
    {
      name: 'no-circular',
      comment: 'Dependencies, including type-only dependencies, must be acyclic.',
      severity: 'error',
      from: {},
      to: { circular: true },
    },
    {
      name: 'no-unresolvable-imports',
      comment: 'Unresolved imports must not bypass source path and package layer checks.',
      severity: 'error',
      from: {},
      to: { couldNotResolve: true },
    },
    {
      name: 'packages-must-not-depend-on-composition',
      comment: 'Packages own capabilities; app and pages compose them.',
      severity: 'error',
      from: { path: `^${R}/` },
      to: { path: '^src/', pathNot: `^${R}/` },
    },
    {
      name: 'pages-must-not-depend-on-app',
      severity: 'error',
      from: { path: '^src/pages/' },
      to: { path: '^src/app/' },
    },
    {
      name: 'no-global-type-buckets',
      comment: 'Components, stores and adapters belong to the capability that owns them.',
      severity: 'error',
      from: {},
      to: { path: '^src/(components|stores|api|utils|common|shared)/' },
    },
    {
      name: 'new-packages-require-a-declared-layer',
      comment: 'Declare a new capability and its allowed dependencies before importing it.',
      severity: 'error',
      from: {},
      to: { path: unregisteredPackage },
    },
    {
      name: 'unregistered-packages-cannot-import',
      severity: 'error',
      from: { path: unregisteredPackage },
      to: {},
    },
    ...Object.entries(packageDependencies).map(([name, dependencies]) => ({
      name: `layer-${name}`,
      comment: `${name} may only depend on its declared lower-level capabilities.`,
      severity: /** @type {const} */ ('error'),
      from: { path: `^${R}/${name}/` },
      to: {
        path: `^${R}/`,
        pathNot: `^${R}/(${[name, ...dependencies].join('|')})/`,
      },
    })),
    {
      name: 'chrome-uses-feature-presentation-interfaces',
      comment: 'Toolbar/menu composition may use focused feature presentation APIs only.',
      severity: 'error',
      from: { path: `^${R}/axis-chrome/` },
      to: {
        path: `^${R}/(manual-control|toolpath-view)/`,
        pathNot: `^${R}/(manual-control|toolpath-view)/presentation[.]ts$`,
      },
    },
  ],
  options: {
    doNotFollow: { path: 'node_modules' },
    tsConfig: { fileName: 'tsconfig.json' },
    // Preserve dependencies erased by TypeScript; Vue scripts use the installed compiler-sfc.
    tsPreCompilationDeps: true,
    enhancedResolveOptions: {
      exportsFields: ['exports'],
      conditionNames: ['import', 'browser', 'default', 'types'],
      extensions: ['.ts', '.tsx', '.js', '.jsx', '.json', '.vue'],
    },
  },
};
