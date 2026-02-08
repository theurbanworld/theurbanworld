# Product Mission

## Pitch

The Urban World is an interactive observatory for understanding cities. It uses data as a lens to teach mental models about how cities work - bridging the measurable (ville) and the lived (cité) - helping urbanists from professional planners to curious generalists see patterns, discover context, and develop intuition about urban form.

Hosted at: `theurban.world`

## Vision

This is not a dashboard. This is the interactive version of "How to Think About Cities" - a library of urban mental models that happen to use data. Each analytical lens we add teaches a way of seeing, not just a way of measuring.

The ultimate goal: someone looks at a radial profile, sees an unexpected pattern, asks "why does it look like this?", discovers an explanation, and gains a mental model they can apply to any city in the world.

## Conceptual Framework

### Cité vs Ville (Richard Sennett)

- **Ville:** The built environment - density, infrastructure, form (what we measure directly)
- **Cité:** The lived experience - how people move, work, live (what we infer and contextualize)

Most urban data platforms are stuck in ville. The Urban World bridges both - showing how physical form shapes and reflects human experience.

### Scales of Analysis

- **Building:** Individual structures, heights, typologies
- **Street:** Network patterns, walkability, public space
- **Neighborhood:** Local amenities, 15-minute access
- **City:** Overall form, radial profiles, growth patterns
- **Metropolitan:** Regional connections, polycentric structure

### Contexts That Shape Cities

- **Geography:** How terrain constrains and enables
- **Technology:** How infrastructure enables density
- **Law and Finance:** How regulation constrains form
- **Economics:** How markets allocate space
- **Culture and History:** How legacy shapes present

## Users

### Primary Customers

- **Urban Professionals:** City planners, researchers, journalists, and policy analysts who need trustworthy data with proper methodology - and mental frameworks to interpret it
- **Curious Generalists:** Data enthusiasts, travelers, and urbanophiles who want to understand how cities work, not just see pretty maps

### User Personas

**Maria** (35-50)
- **Role:** Urban Planner / Policy Researcher
- **Context:** Works at a city planning department or research institution
- **Pain Points:** GHSL data exists but lacks context; comparing cities requires manual work; hard to explain urban patterns to stakeholders
- **Goals:** Quick access to reliable metrics with interpretive frameworks; defensible data for reports; mental models she can teach others

**Alex** (25-40)
- **Role:** Data Enthusiast / Urbanophile
- **Context:** Follows urban development news; curious about how cities grow and change
- **Pain Points:** Most city data is either too technical or too simplistic; wants to understand "why" not just "what"
- **Goals:** Develop intuition about cities; discover interesting patterns; understand what shapes the places they visit

## The Problem

### Data Without Meaning

Global urban datasets like GHSL exist but are difficult to interpret. A density map shows patterns but does not explain them. Population numbers lack context. Users can see that Lagos has 15 million people but cannot easily understand what that means for urban form, how it compares to peer cities, or why it looks the way it does.

**Our Solution:** Layer mental models onto data. The Bertaud radial profile is not just a chart - it reveals monocentric vs polycentric structure, exposes regulatory boundaries, makes sprawl visible, and enables meaningful cross-city comparison. Each analytical lens we add teaches a way of seeing.

### Ville Without Cité

Most urban data platforms show built form without connecting to lived experience. They measure density but not what density means for housing access. They map transit lines but not what that means for opportunity.

**Our Solution:** Bridge ville and cité through interpretive content. A density cliff at a ring road is not just a measurement - it is evidence of regulatory policy shaping how people can live.

## Differentiators

### Mental Models, Not Just Metrics

Unlike dashboards that show raw data, we apply established urban analysis frameworks - starting with Bertaud's radial profiles, expanding to connectivity analysis, accessibility modeling, growth pattern classification. Each model teaches users to see cities differently.

### Context That Creates Understanding

Unlike tools that let users draw their own conclusions from ambiguous data, we provide interpretive scaffolding. What does a flat density curve mean? Why does this city have two peaks? Articles and comparisons help users develop intuition.

### Trustworthy for Professionals, Accessible for Everyone

Unlike academic tools that sacrifice usability or consumer apps that sacrifice rigor, we aim for both. Clear methodology, proper provenance, professional design. Citable in reports, shareable on social media.

### Ville and Cité Together

Unlike platforms stuck in built form metrics, we connect physical patterns to lived experience through contextual information - geography, regulation, history - that explains why cities look the way they do.

## Key Features

### Core Observatory (MVP)

- **Global Population Map:** Interactive H3 hexagonal grid showing population density for ~13,000 cities
- **City Explorer:** Select any city to see population, area, density with global context
- **Radial Density Profiles:** Bertaud-style analysis revealing urban structure
- **Population Time Series:** 1975-2030 historical trends and projections
- **City Search:** Fast client-side search across all urban centers

### Context Layer

- **Relative Rankings:** Global rank, percentile, regional position
- **Density Peers:** Cities with similar profiles for meaningful comparison
- **Growth Classification:** Rapid growth, stable, declining - compared to peers

### Content System (Post-MVP)

- **Methodology Articles:** Teaching the mental models ("Reading Radial Profiles: A Guide")
- **City Deep-Dives:** Applying models to specific places ("The Geography of Lagos: Three Cities in One")
- **Comparative Analysis:** Revealing patterns across cities ("The World's Most Monocentric Cities")
- **Thematic Collections:** Cities grouped by shaping forces (geography-constrained, transit-shaped, regulation-bounded)

### Experiential Context (Future)

- **Geographic Context:** Natural constraints that shape form
- **Regulatory Archaeology:** How policy boundaries become visible in data
- **Historical Layers:** How cities grew epoch by epoch
- **Street-Level Connection:** Visual context for what density feels like

## Content Philosophy

### Objective to Interpretive, Not Normative

- **Objective:** "Paris has a sharp density decline at the Peripherique"
- **Interpretive:** "This reflects building height restrictions at the historic boundary"
- **Normative:** (We avoid) "This restriction limits housing supply and raises prices"

We teach people how to see, not what to conclude. Urban planning is inherently political - density, regulation, sprawl are contested concepts. We provide frameworks for understanding, not advocacy for particular positions.

### Show First, Explain Later

- V1: Let the data speak. Users who know Bertaud recognize it; curious users wonder what they are looking at
- V1.1+: Articles answer the questions users actually ask, informed by real usage patterns
- Articles are powered by the tool, not separate from it - embedded charts, deep links, interactive examples

## Data Foundation

- **Source:** European Commission's Global Human Settlement Layer (GHSL) R2023A/R2024A
- **Coverage:** ~13,000 urban centers globally (>50k population, >1500/km2 density)
- **Temporal:** 1975-2030 at 5-year intervals
- **Spatial:** H3 hexagonal grid at resolution 8-9
- **Updates:** Pipeline designed for easy reprocessing when GHSL releases new epochs

## Success Metrics

### Engagement

- Beyond-homepage engagement rate
- Time spent with analytical features (radial profiles, comparisons)
- Cities explored per session
- Return visitor rate

### Understanding (Qualitative)

- Do users discover patterns on their own?
- Do radial profiles generate "aha moments"?
- Are users developing urban intuition?

### Resonance

- Social shares and organic mentions
- Academic citations
- Requests for specific cities or features

## Future Mental Models

As the platform matures, additional analytical lenses to consider:

**Urban Form and Structure:**
- Connectivity analysis (street network patterns)
- Land use entropy (mixing vs segregation)
- Fractal dimension (measuring urban complexity)

**Growth and Economics:**
- Urban primacy (Zipf's law analysis)
- Density gradients over time (Clark's model)
- Built-up intensity patterns

**Constraints and Opportunities:**
- Geographic constraints visualization
- Climate exposure analysis
- Infrastructure capacity indicators

**Social Patterns:**
- Segregation indices
- 15-minute city accessibility
- Public space allocation

Each model added should work like Bertaud - not just showing data, but teaching a way of seeing.
