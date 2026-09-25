/// <reference types="vite/client" />

declare module '*.css' {
  const content: { [className: string]: string };
  default content;
}