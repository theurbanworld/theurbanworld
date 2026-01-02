# Product Roadmap

## Phase 1: MVP Launch (72 Hours)

Goal: Ship a functional observatory that demonstrates the core value proposition - data as a lens for understanding cities, starting with Bertaud's radial density model.

1. [ ] Map Foundation — Implement deck.gl H3HexagonLayer displaying global population density from GeoParquet on R2, with MapLibre basemap using Protomaps PMTiles `M`
2. [ ] City Selection — Click or tap a city on the map to select it; highlight selected city boundary; pan/zoom to city extent `S`
3. [ ] City Info Panel — Display selected city's name, country, population, area, and density with clean typography and layout `S`
4. [ ] City Search — Implement Fuse.js client-side search over city index; show results dropdown; select to navigate to city `S`
5. [ ] Population Time Series Chart — Chart.js line chart showing 1975-2030 population for selected city with proper axis labels and tooltips `S`
6. [ ] Radial Density Profile Chart — Chart.js line chart showing Bertaud-style density vs distance profile; include log-scale toggle `S`
7. [ ] Context Rankings — Show city's global rank, percentile, and regional rank for population and density alongside raw numbers `XS`
8. [ ] Mobile Responsive Layout — Ensure map and panel work on mobile; collapsible panel; touch-friendly controls `S`
9. [ ] Deploy to Production — Configure Cloudflare Workers deployment; verify R2 data access; set up theurban.world domain `S`

> Notes
> - Items 1-2 are foundational and should be completed first
> - Items 3-7 can be developed in parallel once map works
> - Item 8 should be ongoing throughout development
> - Item 9 is the final step before launch
> - Keep explanatory text minimal - let data speak, observe what questions users ask

---

## Phase 2: Context and Comparison (2-4 Weeks)

Goal: Deepen the contextual value; enable meaningful city comparisons; learn from user behavior.

10. [ ] Density Peer Comparison — Show 3-5 cities with similar density profiles; enable one-click navigation to compare `S`
11. [ ] Growth Context — Classify city growth pattern (rapid growth, stable, declining); show comparison to regional average `S`
12. [ ] Improved Tooltips — Rich hover states on map showing city name and key stats before full selection `XS`
13. [ ] Shareable City URLs — Deep links to specific cities (theurban.world/city/lagos-nigeria) with OG meta tags for social sharing `S`
14. [ ] Methodology Page — Document data sources, what GHSL measures and does not measure, processing approach, limitations `M`
15. [ ] About Page — Project story, vision for understanding cities, GHSL attribution, open source acknowledgments `XS`
16. [ ] Performance Optimization — Lazy load charts; optimize initial bundle; target sub-2s time-to-interactive `M`
17. [ ] Analytics Integration — Privacy-respecting analytics to understand which cities users explore and which features resonate `XS`

---

## Phase 3: Content System - Teaching Mental Models (1-2 Months)

Goal: Add the narrative layer that transforms data visualization into urban education. Articles should be powered by the tool, not separate from it.

18. [ ] MDC Content Infrastructure — Set up Nuxt Content with MDC for rich articles that embed interactive charts and map views `L`
19. [ ] Methodology Articles — "Reading Radial Profiles: A Guide", "What GHSL Measures", "Why Population-Weighted Centroids Matter" `M`
20. [ ] City Deep-Dives — Template for applying mental models to specific places: "The Geography of Lagos: Three Cities in One" `M`
21. [ ] Comparative Analysis Articles — "The World's Most Monocentric Cities", "Where Density Meets Geography: Coastal Megacities" `L`
22. [ ] Thematic City Collections — Curated sets teaching forces that shape cities: geography-constrained, transit-shaped, regulation-bounded `M`

---

## Phase 4: Bridging Ville and Cité (2-3 Months)

Goal: Connect measurable form (ville) to lived experience (cité). Help users understand what cities feel like, not just how they measure.

23. [ ] Geographic Context Layer — Visualize natural constraints (water, elevation, agricultural land) that shape urban form `M`
24. [ ] Climate Context — Show climate classification; enable comparison of cities with similar density but different climates `M`
25. [ ] Regulatory Archaeology — Where available, show administrative boundaries and how they create visible density patterns `L`
26. [ ] Historical Growth Animation — Visualize how cities expanded epoch by epoch from 1975-2025 `L`
27. [ ] Street-Level Connection — Link to or embed representative street-level imagery for visual context `M`
28. [ ] Comparative Mode — Side-by-side city comparison with synchronized charts, metrics, and map views `L`

---

## Phase 5: Additional Mental Models (3-6 Months)

Goal: Expand the library of analytical lenses. Each new model should teach a way of seeing, not just show more data.

29. [ ] Connectivity Analysis — Street network patterns (grid vs organic), intersection density, block sizes `L`
30. [ ] Accessibility Modeling — Isochrone analysis from city centers; 15-minute city metrics where data permits `L`
31. [ ] Urban Primacy — Zipf's law analysis for country/regional urban systems `M`
32. [ ] Growth Pattern Classification — Expansion vs densification; greenfield vs infill patterns over time `L`
33. [ ] Land Use Entropy — Where data available, measure mixing vs segregation of uses `L`

---

## Phase 6: Sustainability and Professional Features (6+ Months)

Goal: Build sustainable model for ongoing development while maintaining accessibility.

34. [ ] Data Export — Download city data as CSV/JSON for research and journalism use `M`
35. [ ] Embed Widgets — Embeddable charts and maps for blogs, articles, reports `M`
36. [ ] API Access — Public API for programmatic access to city metrics `L`
37. [ ] Supporter Model — Optional tier for advanced features, early access, higher API limits `L`
38. [ ] Custom Analysis — User-defined peer groups, saved comparisons, personal collections `L`

---

## Effort Scale

- `XS`: Less than 1 day
- `S`: 2-3 days
- `M`: 1 week
- `L`: 2 weeks
- `XL`: 3+ weeks

## Principles

- **Mental models over metrics:** Each feature should teach a way of seeing, not just display more data
- **Show first, explain later:** Let curious users discover patterns; add explanatory content based on real questions
- **Ville and cité together:** Connect measurable form to lived experience wherever possible
- **Objective to interpretive, not normative:** Teach how to see, not what to conclude
- **Ship incrementally:** Each item should be independently deployable and valuable
- **Mobile-first:** Urban exploration happens on phones
- **Performance matters:** Fast loads build trust and enable exploration
