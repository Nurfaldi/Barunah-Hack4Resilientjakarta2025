# Unearthing Jakarta's Risk-Scape: A Participatory, Data-Driven Blueprint for an Inclusive Jakarta

## Problem Formulation

Jakarta, a city of over 10 million, faces urgent environmental risks and widening inequality. Land subsidence and frequent flooding hit coastal kampungs hardest, worsened by excessive groundwater use, limited infrastructure, and uneven development. However, urban planning often prioritizes large-scale reclamation and real estate projects, while the everyday realities of kampung residents remain absent from official data. Informal livelihoods, groundwater reliance, and mobility patterns are rarely reflected in spatial planning tools. Without these insights, policies risk deepening exclusion and shifting environmental burdens onto already vulnerable communities. To build a more inclusive vision for Jakarta, we must also recognize the hidden economic and social fabric that sustains millions and ensure it is seen, valued, and supported. This project proposes a platform that integrates spatial, environmental, and participatory data. Our vision is to invite all Jakarta residents to help shape the city's future; backed by data, grounded in science, and centered on community.

## Proposed Dataset

This project aims to integrate diverse, accessible datasets to reveal both environmental risk and social vulnerability. We will use publicly available data from government portals (e.g., Jakarta Satu, Pantau Banjir), academic studies, and open-source repositories. Key layers include land subsidence rates, flooding frequency, zoning maps, infrastructure networks, and socio-economic indicators. These layers will be complemented by participatory data collected from kampung communities, such as mobility patterns, water access, and informal economic activity, to build a richer, more grounded analysis.

## Proposed Analysis/Methods

This project follows a four-phase analytical process designed for rigor and feasibility within the hackathon timeline:

### Phase 1: Geospatial Data Harmonization
All datasets (physical, environmental, and socio-economic) will be aligned to the Rukun Warga (RW)/Kelurahan level. Raster data (e.g., land subsidence, flood risk) will be converted to zonal statistics using rasterstats, while vector layers (e.g., zoning, infrastructure) and tabular socio-economic indicators (from BPS) will be spatially joined. The output is a unified GeoDataFrame with harmonized attributes per RW/Kelurahan.

### Phase 2: Social Vulnerability Index (SVI)
We will construct an SVI using simplified, normalized indicators (e.g., Population density, income, housing type), adapted from CDC's SVI. A composite score will reflect each RW/kelurahan's susceptibility to harm and capacity to recover.

### Phase 3: Risk Hotspot Identification
By combining SVI with environmental hazard data (subsidence, flood depth), we will generate a Compounded Risk Score for each RW/Kelurahan. Using the risk hotspot analysis, we will analyze and identify hotspots—areas where high social and environmental risks intersect.

### Phase 4: Qualitative Data Integration
To center community voices, we will simulate citizen science inputs (e.g., eviction vulnerability, informal economies, daily mobility). We aim to engage kampung cooperatives, women, and youth—key caretakers and economic drivers—through gamified, incentivized data collection. Their insights will be tagged to hotspot areas, enriching the data with local knowledge. This approach will visualize risk as a layered, lived experience and targets Jakarta's core issue of excessive groundwater extraction, offering a basis for equitable, community-informed water infrastructure planning.

## Expected Output

The primary output of this project is the **Jakarta Risk & Resilience Dashboard**—an interactive, web-based platform that transforms complex spatial analysis into clear, actionable insights. Designed both as a data repository and a decision-support and storytelling tool, the dashboard allows users to explore Jakarta's compounded risks from city-wide trends down to community-level narratives. Built with a user-centric design, the dashboard guides policymakers, researchers, and community advocates through an intuitive exploration of urban risk, highlighting which areas are most vulnerable, and why. It bridges quantitative geospatial analysis with qualitative, community-based insights, helping users connect environmental hazards with the lived experiences of residents. Features such as the "Kampung Profile" make these stories visible and usable for advocacy.

Beyond the hackathon, the dashboard is designed as a prototype for long-term policy engagement. Agencies like Bappeda can use the dashboard to prioritize infrastructure investments in areas where risk and vulnerability intersect, such as recommended areas to expand piped water in subsiding zones or adjusting zoning in flood-prone kampungs. Local leaders and NGOs such as Jaringan Rakyat Miskin Kota (JRMK) and Urban Poor Consortium (UPC) can use the dashboard to present evidence-based proposals to support their existing community appeals with data-backed advocacy. The platform also lays the groundwork for future scalability. Real-time data integration (e.g., from Pantau Banjir), predictive models for land subsidence, and machine learning–based scenario planning are all feasible extensions. Built with open-source tools, the framework can be replicated in other coastal megacities facing similar challenges. The dashboard aims to democratize data, giving all Jakarta residents, from planners to kampung citizens, a say in shaping a more just, resilient city. A complementary zine will accompany the dashboard, serving as a printed background explainer, user guide, and advocacy tool to support broader understanding and action.

## Supporting Materials

*[To be added]*


