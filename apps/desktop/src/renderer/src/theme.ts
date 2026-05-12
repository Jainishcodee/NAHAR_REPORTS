import { createTheme, type MantineColorsTuple } from '@mantine/core';

// A calm clinical blue.
const brand: MantineColorsTuple = [
  '#e7f3ff',
  '#cee3ff',
  '#9cc4fb',
  '#67a4f6',
  '#3d89f2',
  '#2478f0',
  '#0b6bcb',
  '#005db7',
  '#0052a3',
  '#00478f',
];

export const theme = createTheme({
  primaryColor: 'brand',
  colors: { brand },
  fontFamily: 'Segoe UI, Roboto, Helvetica, Arial, sans-serif',
  defaultRadius: 'md',
  cursorType: 'pointer',
});
