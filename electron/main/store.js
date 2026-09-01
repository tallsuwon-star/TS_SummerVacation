const Store = require('electron-store');

const store = new Store({
  name: 'settings',
  defaults: {
    theme: 'light',
    windowBounds: { width: 1280, height: 840 },
    lastTutorList: '',
    checkedTutors: [],
    criteria: {
      consultationAfter: '2026-08-18',
      classAfter: '2026-08-20',
    },
  },
});

module.exports = store;
