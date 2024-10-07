// src/boot/theme.ts
import { boot } from 'quasar/wrappers';

export default boot(({ app }) => {
  const defaultTheme = 'freedom';

  const setTheme = (themeName: string) => {
    document.body.setAttribute('data-theme', themeName);
  };

  const savedTheme = localStorage.getItem('theme') || defaultTheme;
  setTheme(savedTheme);

  app.config.globalProperties.$setTheme = setTheme;
});
