# oscar-nextgen-poc
Proof-of-concept regarding viability of EUMETNET/MeteoGate infrastructure for leveraging and hosting OSCAR nextGen

## Intro
MeteoGate APIs are built around the Attribute Convention for Data Discover (ACDD1.3) metadata model. OSCAR/Surface leverages the WIGOS Metadata Representation (WMDR1.0). ACDD1.3 is a flat structure serialized as JSON objects, while WMDR1.0 is a deeply nested XML format.

## Scope
- WP1: Develop a mapping of WMDR1.0 metadata records to ACDD1.3.
  - The basic idea is to use one ACDD1.3 record to describe an observation (=time series of measurements of a specific variable) at a station/platform, and to link this record to another ACDD1.3 record to describe the station/platform characteristics. Contacts can be referenced at both levels. A WIGOS ID can be assigned at the level of the station/platform (WSI, identifier series: 0). Conceptually and by design, WIGOS IDs can also be assigned at the level of an observation (WOI, Identifier series: 1), an instrument/equipment (WEI, identifier series: 3), and a contact (WCI, identifier series: 4). WOIs can be referenced in a link table to WSIs. With just one level of nesting, many of the important WIGOS metadata elements should thus be mappable.
  - While the current WMDR is station/platform-centric, isolating station/platform, observation, and equipment may facilitate the creation of WIGOS metadata records of different flavors, namely also an observation(=variable)-centric, or an equipment-centric representation. The latter has the advantage that many instruments allow the observation of multiple variables with shared method, sampling, aggregation, and reporting. These various views are called WMDR2.0-station, WMDR2.0-obs, WMDR2.0-inst for brevity. The various elements shall be modeled as individual ACDD1.3 records and shall document aspects of WMDR1.0 that cannot be handled.
    
- WP2: Implement a transformation for WMDR1.0 to ACDD1.3-compliant JSON
  - Task 1: This involves a transformation of a WMDR1.0 record into a JSON representation (WMDR1.0-JSON)
    - Establish a GEO-JSON schema (work in progress)
    - Write a Python class to expose WMDR1.0 and WMDR1.0-JSON and to transform between the two
  - Task 2: This involves transformation of  transformation into the JSON ACDD1.3 representation. It also involves generation of WOIs and WEIs and representation of the WOIs and WEIs in the station/platform ACDD1.3 record. Or alternatively, an extension of the current MeteoGate APIs may be required.
  - The PoC should test the concept for
    - a record of in situ temperature (a state variable, geometry: point), and ozone profile (composition, geometry: vertical profile) at a land station.
    - the same or similar for a mobile platform, e.g. ARGO float.
   
- WP3: Use the MeteoGate Ingest API to register and persist information

- WP4: Use the MeteoGate Output API to retrieve a WMDR2.0 record
