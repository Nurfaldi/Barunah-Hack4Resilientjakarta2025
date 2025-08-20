# **Sinking City Vulnerability Index**

## **Background**
Jakarta faces overlapping threats from climate change and rapid urbanization. Critical decisions are often made using incomplete data that overlooks the everyday realities of its most vulnerable communities—the kampungs. This data gap can lead to policies that are ineffective or even harmful, leaving residents invisible in the planning process.

BaruJak bridges this gap. We are building a single source of truth by merging quantitative data with the rich, qualitative "lived experience" of residents. By geotagging community stories, photos, and survey results, we create a holistic and dynamic picture of risk and resilience that is accessible to everyone.

## **Goal**
Our goal is to empower residents, inform policymakers, and foster the collaboration needed to build a more just and resilient Jakarta for all. We aim to bridge dialogue and knowledge exchange across stakeholders and disciplines.

## **Methodology**
The **Sinking City Vulnerability Index** (SCVI) is a comprehensive tool developed to measure how vulnerable Jakarta's neighborhoods are to the dual threats of flooding and land subsidence. The index analyzes 21 key indicators across three core dimensions: Social Factors, Infrastructure & Environment, and Hazard Exposure. Our goal is to provide clear, actionable data for residents, researchers, government agencies, and community organizations to build a more resilient city.

Of course. Here is the methodology documentation for the Sinking City Vulnerability Index (SCVI) based on the provided R script.

### **SCVI Calculation**

This document outlines the step-by-step methodology used to calculate the Sinking City Vulnerability Index (SCVI) for Jakarta in 2024. The entire analysis is conducted using the R programming language.

### **Utilized Libraries**

The analysis leverages several key R packages for data manipulation, spatial analysis, and visualization:

* **`sf`**: For handling and processing geospatial vector data.
* **`tidyverse`**: A collection of packages for data science, including `dplyr` for data manipulation and `ggplot2` for plotting.
* **`janitor`**: For cleaning data frames and column names.
* **`here`**: For simplifying file path management.
* **`osmdata`**: For accessing OpenStreetMap data (though not used in the final index calculation steps shown).
* **`readxl`**: For reading Microsoft Excel files (`.xlsx`).
* **`classInt`**: For classifying numerical data into intervals, specifically using the Jenks Natural Breaks method.
* **`htmlwidgets`**: For creating interactive web visualizations.

---

### **Step-by-Step Analysis**

The calculation of the SCVI is performed through a multi-step process, from data preparation to final index classification.

#### **Step 1: Data Preprocessing and Indicator Derivation**

The initial step involves loading and processing various raw datasets to derive the specific indicators needed for the index. The primary unit of analysis is the `kelurahan` (village/sub-district) level.

* **Geospatial and Base Data**: Administrative boundaries for Jakarta's neighborhoods (`kelurahan`) are loaded to serve as the geometric base for the analysis.
* **Population Factors**:
    * **Vulnerable Age Groups**: The proportions of the young population (ages 0-9) and the old population (ages 65+) are calculated from detailed age-based population data.
    * **Female Population**: The proportion of the female population is calculated.
    * **Population Growth**: The annual population growth rate is computed by comparing the total population between 2023 and 2024.
    * **Vulnerable & Unemployed Population**: Data on occupations is processed to calculate the proportion of the population that is unemployed (defined as "belum/tidak bekerja" and "pensiunan") and the proportion in vulnerable employment sectors (e.g., "buruh harian lepas", "pembantu rumah tangga").
* **Infrastructure and Environment Capacity**:
    * **Informal Settlements**: Data on the number of residents living in informal settlements is loaded.
    * **Residential Area**: The total residential area within each `kelurahan` is calculated.
* **Risk Exposure**:
    * **Groundwater Usage**: Groundwater usage data, originally at the `kecamatan` (district) level, is disaggregated to the neighborhood level. This is done by calculating the proportion of a neighborhood's built area relative to the total built area of its parent `kecamatan` and allocating groundwater usage accordingly.

#### **Step 2: Indicator Integration**

All the processed indicators are merged into a single, comprehensive data frame. This master table links each indicator to its corresponding neighborhood `id_obj` and `id_kel`, creating a unified dataset for the index calculation.

#### **Step 3: Normalization and Directionality Adjustment**

To ensure all indicators are comparable and contribute appropriately to the index, they undergo a two-part process:

1.  **Normalization**: Each numeric indicator is normalized by calculating its **z-score**. This standardizes the variables, giving them a mean of 0 and a standard deviation of 1, preventing indicators with larger value ranges from dominating the index.
2.  **Directionality Adjustment**: The z-scores of certain indicators are inverted (multiplied by -1). This is a critical step to ensure that for every indicator, a **higher score consistently means higher vulnerability**. For example, a high value for `veg_cov24` (vegetation cover) or `dist_rv` (distance to river) indicates lower vulnerability; therefore, their scores are inverted.

    *Indicators inverted*: `drn_sys`, `dist_rv`, `dist_coast`, `n_pump`, `topo`, `veg_cov24`.

#### **Step 4: Dimensional Index Calculation**

The normalized and adjusted indicators are grouped into three distinct dimensions of vulnerability based on a predefined list:

1.  **Population Factors**
2.  **Infrastructure and Environment Capacity**
3.  **Risk Exposure**

An unweighted index is calculated for each dimension by summing the z-scores of all indicators within that group. This results in three separate index scores for each neighborhood.

#### **Step 5: Final SCVI Calculation and Classification**

The final, unweighted SCVI score for each neighborhood is calculated by **summing the three dimensional indices** (Population, Infrastructure/Environment, and Risk).

To make the resulting index scores more interpretable, they are classified into five categories ("Very Low" to "Very High") using the **Jenks Natural Breaks** classification method. This statistical method identifies the best arrangement of values into different classes by seeking to minimize the variance within each class and maximize the variance between classes.

#### **Step 6: Data Export and Visualization**

The final output is generated in multiple formats for analysis and dissemination:

* **Geospatial File**: A GeoJSON file containing the `kelurahan` boundaries along with their final SCVI scores, categories, and key indicator data.
* **CSV File**: A non-spatial CSV table of the results.
* **Static and Interactive Maps**: A map of Jakarta is generated, color-coding each `kelurahan` by its SCVI score, and saved as a PNG image. An interactive version of this map is also created and saved as an HTML file, allowing users to hover over areas to see detailed information.

## **Results and Analysis**

Our analysis reveals critical hotspots across the capital. Out of all neighborhoods (kelurahan), **100 face a high level of vulnerability**, with **21 of those falling into the 'Very High' risk category**.

* **Most Vulnerable Neighborhood:** **Kelurahan Penjaringan** in North Jakarta is the single most vulnerable neighborhood, with the highest SCVI score of **10.17**.
* **Most Vulnerable Municipality:** On average, **North Jakarta (Jakarta Utara)** is the most vulnerable administrative city, with an average SCVI score of **1.88**.

Different parts of Jakarta face unique challenges. Here’s a breakdown of the most vulnerable administrative cities by each dimension:

* **🧍 Social Vulnerability: North Jakarta (Jakarta Utara)**
    This area faces the greatest risk due to its population characteristics. The vulnerability is largely driven by a high concentration of residents in precarious employment sectors, such as fisheries and manual labor, who may have fewer resources to prepare for and recover from disasters.

* **🏙️ Infrastructure & Environment: West Jakarta (Jakarta Barat)**
    This municipality is most vulnerable in terms of its physical capacity. Key contributing factors include a **lack of green spaces**, a high density of built-up areas, and an insufficient drainage system capacity, making the area less able to absorb rainfall and manage floodwater.

* **💧 Hazard & Sinking Risk: South Jakarta (Jakarta Selatan)**
    Surprisingly, South Jakarta registers the highest direct exposure to sinking and flooding hazards. Despite its inland location, this is due to a combination of **excessive groundwater extraction** leading to land subsidence and the **severe flood depths** recorded in the area during major events.

## **References**
- B.I. Nasution et al., Revisiting social vulnerability analysis in Indonesia: An optimized spatial fuzzy clustering approach. International Journal of Disaster Risk Reduction 51
- Fitton, J.M., O’Dwyer, B. & Maher, B. (2021) Developing a social vulnerability to environmental hazards index to inform climate action in Ireland. Irish Geography 54(2)
- Kim, Kangmin, et al., (2025) Identifying Indicators Contributing to the Social Vulnerability Index via a Scoping Review. Land 14:263-291
- McCullagh, D., et al., (2025) Development of a social vulnerability index: Enhancing approaches to support climate justice. MethodsX 14
- Siagian, T.H., et al., (2014) Social vulnerability to natural hazards in Indonesia: driving factors and policy implications. Nat Hazards 70:1603-1617

