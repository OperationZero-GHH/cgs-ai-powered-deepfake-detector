# Redesign notes

- Replaced the anchor-based public navbar with separate Home, Solutions, Technology, Pricing, About, and Contact routes, plus a categorized full-width Explore mega menu and a Testimonials link to the Solutions section.
- Reduced the home route to a hero with layered, tilted report-interface cards; moved pricing, technology, about, and contact content into dedicated pages.
- Added three pricing tiers with Pro highlighted; Pro/Business pricing and features are labeled illustrative because checkout and team plans are not configured.
- Added a Solutions testimonial carousel with sample copy explicitly marked illustrative, and a split Contact page that identifies unavailable contact channels and form delivery.
- Rebuilt the footer as a Product, Company, Resources, and Legal sitemap, and gave sign-in/sign-up a responsive split-screen branded report panel without changing auth behavior.
- Verified the web app with production build, ESLint, and TypeScript checks.
- Added a consent banner with browser-local accept/reject preference, a themed global 404 page, and a root shimmer skeleton with the shared header/footer.
- Added a measured animated caret input to text fields, center-origin circle theme transitions, animated utility tooltips, and edge-fade scroll areas for section and workspace navigation.
