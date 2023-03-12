import { defineConfig } from 'astro/config';
import react from "@astrojs/react";
import image from "@astrojs/image";
import {settings} from "./src/utils/settings"
// import tailwind from "@astrojs/tailwind";

// https://astro.build/config
export default defineConfig({
  site: process.env.PUBLIC_SITE_URL || 'https://maastrichtu-ids.github.io',
  base: process.env.PUBLIC_BASE_URL || "",
  trailingSlash: 'ignore',
  integrations: [
    react(),
    image(),
    // tailwind({
    //   config: {
    //     applyBaseStyles: false,
    //   },
    // }),
  ],
  output: 'static'
});