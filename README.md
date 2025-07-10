# oscar-nextgen-poc
Proof-of-concept regarding viability of EUMETNET/MeteoGate infrastructure for leveraging and hosting OSCAR nextGen

## Intro
MeteoGate APIs are built around the Attribute Convention for Data Discover (ACDD1.3) metadata model. OSCAR/Surface leverages the WIGOS Metadata Representation (WMDR1.0). ACDD1.3 is a flat structure serialized as JSON objects, while WMDR1.0 is a deeply nested XML format.

## In Scope
- WP1: Develop a minimal mapping of WMDR1.0 metadata records to ACDD1.3 (lead: Jörg, collaborators: Lucia, Anna, Timo)
  - The basic idea is to use one ACDD1.3 record per observed variable to describe an observation (=time series of measurements of a specific variable) at a station/platform, and to link this record to another ACDD1.3 record to describe the station/platform characteristics. Contacts can be referenced at both levels. A WIGOS ID can be assigned at the level of the station/platform (WSI, identifier series: 0). Conceptually and by design, WIGOS IDs can also be assigned at the level of an observation (WOI, Identifier series: 1), an instrument/equipment (WEI, identifier series: 3), and a contact (WCI, identifier series: 4). WOIs can be referenced in a link table to WSIs. With just one level of nesting, many of the important WIGOS metadata elements should thus be mappable.
  - While the current WMDR is station/platform-centric, isolating station/platform, observation, and equipment may facilitate the creation of WIGOS metadata records of different flavors, namely also an observation(=variable)-centric, or an equipment-centric representation. The latter has the advantage that many instruments allow the observation of multiple variables with shared method, sampling, aggregation, and reporting. These various views are called WMDR2.0-station, WMDR2.0-obs, WMDR2.0-inst for brevity. The various elements shall be modeled as individual ACDD1.3 records encoded as GEO-JSON and shall document aspects of WMDR1.0 that cannot be handled, as well as propose solutions for that (presumably, blobs as part of the comments).

  - Task 1: Revisit the existing 0th draft of WMDR2.0 and disaggregate into WMDR2.0-station, WMDR2.0-obs, WMDR2.0-inst FeatureTypes
      - WMDR2.0 was based on OGC OMS/ISO 19156:2020 and some concerns voiced about WMDR1.0 were alleviated. WMDR2.0 is largely (not completely) backward compatible with WMDR1.0 and uses more user-friendly terminology. A critical review is needed.
      - In the context of ACDD1.3, a disaggregation into ACDD1.3 compliant WMDR2.0-station, WMDR2.0-obs, WMDR2.0-inst will be needed, as well as an assessment of the limitations of this disaggregation. Explore what's possible, how elements not covered by ACDD1.3 can still be documented with some JSON stubs.

  - Task 2: Write a Python class transforming ACDD1.3 into GEO-JSON and vice-versa (if that is not yet available)

  - Task 3: Explore the relationships and cardinalities and propose full WMD representations (WMDR2.0-JSON) based on the building blocks WMDR2.0-station, WMDR2.0-obs, WMDR2.0-inst

- WP2: Implement a full transformation for WMDR1.0 (by way of WMDR2.0) to ACDD1.3-compliant JSON (lead: ?, collaborators: ?)
  - The PoC should test the concept for
    - a record of in situ temperature (a state variable, geometry: point) and ozone profile (composition, geometry: vertical profile) at a land station.
    - similarly for a mobile platform, e.g. ARGO float.
   
  - Task 1: Transformation of WMDR1.0 into WMDR2.0-JSON and vice-versa
    - Write a Python class to transform a WMDR1.0 into into WMDR2.0-station, WMDR2.0-obs, WMDR2.0-inst objects. Generate WOIs and WEIs on the way (use and map the existing gml-ids) and linkages of the WOIs and WEIs to the WSI.

  - Task 2: Transformation of a WMDR1.0 record into a JSON representation (WMDR2.0-JSON)
    - Write a Python class to expose WMDR1.0 and WMDR2.0-JSON (as composite of WMDR2.0-station, WMDR2.0-obs, WMDR2.0-inst objects) and to transform between the two.
      
  - Task 3: Transformation of WMDR2.0-station, WMDR2.0-obs, WMDR2.0-inst objects into ACDD1.3 objects
    - Write a Python class to convert WMDR2.0-station, WMDR2.0-obs, WMDR2.0-inst to ACDD1.3 objects and vice-versa, and expose these objects.
        
- WP3: Use the MeteoGate Ingest API to register and persist a WMDR2.0-JSON record as linked ACDD1.3 records (lead: Vegar, collaborators: ?)
  - Task 1: Implement the chain of transformations from WMDR1.0 to WMDR2.0-JSON and disaggregation into linked ACDD1.3 records on MeteoGate and persist information in DB

- WP4: Use the MeteoGate Output API to retrieve a WMDR2.0-JSON record (lead: Vegar, collaborators: ?)
  - Task 1: Write a Python class to retrieve an ACDD1.3 record representing either one of, WMDR2.0-station, WMDR2.0-obs, WMDR2.0-inst
    - ACDD1.3 records are snapshots of a state in time. A call to the API thus must allow the user to specify a time or period.
  - Task 2: Based on the context, retrieve related ACDD1.3 records representing either WMDR2.0-station, WMDR2.0-obs, WMDR2.0-inst, and re-construct a full WMDR2.0 record, ideally with one of the perspectives station-centric, observation-centric or instrument-centric.
    - The hierarchy of JSON should make it relatively easy to represent a WMDR2.0-full record composed of WMDR2.0-station, WMDR2.0-obs, WMDR2.0-inst parts. 
 
- WP5: Edit a WMDR2.0 record (lead: Vegar, collaborators:)
  - The PoC should test the concept for
    - adding missing or correcting information, i.e. to retrieve an ACDD1.3 record, to add an element, and to persist it again as an updated record
    - adding or correcting history of an element, e.g., document a change of station location at a given point in time, correct erroneous coordinates of a station at a given point in time
   
- WP6: DAR and analytics, mapping, reporting (lead: Lucia, collaborators:)
  - Based on the current OSCAR/Surface search facility, explore the existing possibilities on MeteoGate / Data Explorer (Open GeoWeb?) and document the gaps
  - Propose a framework for the front-end
  - Propose framework for the geospatial stuff, including front-end mapping
  - Propose the API for DAR, specifically the potential and limitations of OGC EDR API
  - Contact management and interaction with WMO contacts database
  - Propose link to WIS2.0 metadata harvesting for OSCAR/Surface and vice-versa

- WP7: MVP at threshold/breakthrough/goal levels (lead: WMO/Michel Jean, collaborators: WMO Secretariat)
  - Describe requirements at threshold/breakthrough/goal levels (WMO Secretariat)
  
- WP8: Documentation/Proposal for STAC EUMETNET (lead: Andrea, collaborators:)
  - Propose final architecture and production technology stack (Vegar, MeteoSwiss/ITA)
  - Provide cost estimates for MVP including RFI within FEMDI consortium or external proviers (Vegar, MeteoSwiss/ITA)
  - First draft of OSCAR nextGen proposal including cost estimate for Joint-STAC/PFAC 28 (submission: 15 Sep 2025)
  - Final proposal, with input Joint-STAC/PFAC, for decision by EUMETNET Assembly 35 (submission: 15 Nov 2025)
   
## Out of Scope

- Implement front-end needed for OSCAR nextGen meatdata management
- Implement mapping services and mapping utility
- Implement search facility
- Implement advanced reporting services

## Resource availability

Enter the number of working days (or '--') you are likely to be able to invest in the following table.

name|07Jul-11Jul|14Jul-18Jul|21Jul-25Jul|28Jul-01Aug|04Aug-08Aug|11Aug-15Aug|18Aug-22Aug|25Aug-29Aug|01Sep-05Sep
--|--|--|--|--|--|--|--|--|--
Jörg|3|--|--|3|2|3|3|3|2
Lucia|--|--|--|--|--|--|--|--|--
Vegar|--|--|--|--|--|--|--|--|--
Anna|--|--|--|--|--|--|--|--|--
Timo|--|--|--|--|--|--|--|--|--
Jeremy|<1|<1|<1|<1|<1|<1|<1|<1
Andrea|--|--|--|--|--|--|--|--

