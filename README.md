# oscar-nextgen-poc
Proof-of-concept regarding viability of EUMETNET/MeteoGate infrastructure for leveraging and hosting OSCAR nextGen

## Intro
MeteoGate APIs are built around the Attribute Convention for Data Discover (ACDD1.3) metadata model. OSCAR/Surface leverages the WIGOS Metadata Representation (WMDR1.0). ACDD1.3 is a flat structure serialized as JSON objects, while WMDR1.0 is a deeply nested XML format.

## Scope
- WP1: Develop a mapping of WMDR1.0 metadata records to ACDD1.3.
  - The basic idea is to use one ACDD1.3 record to describe an observation (=time series of measurements of a specific variable) at a station/platform, and to link this record to another ACDD1.3 record to describe the station/platform characteristics. Contacts can be referenced at both levels. A WIGOS ID can be assigned at the level of the station/platform (WSI, identifier series: 0). Conceptually and by design, WIGOS IDs can also be assigned at the level of an observation (WOI, Identifier series: 1), an instrument/equipment (WEI, identifier series: 3), and a contact (WCI, identifier series: 4). WOIs can be referenced in a link table to WSIs. With just one level of nesting, many of the important WIGOS metadata elements should thus be mappable.
  - While the current WMDR is station/platform-centric, isolating station/platform, observation, and equipment may facilitate the creation of WIGOS metadata records of different flavors, namely also an observation(=variable)-centric, or an equipment-centric representation. The latter has the advantage that many instruments allow the observation of multiple variables with shared method, sampling, aggregation, and reporting. These various views are called WMDR2.0-station, WMDR2.0-obs, WMDR2.0-inst for brevity. The various elements shall be modeled as individual ACDD1.3 records and shall document aspects of WMDR1.0 that cannot be handled, as well as propose solutions for that (presumably, blobs as part of the comments).
    
- WP2: Implement a transformation for WMDR1.0 to ACDD1.3-compliant JSON

  - The PoC should test the concept for
    - a record of in situ temperature (a state variable, geometry: point), and ozone profile (composition, geometry: vertical profile) at a land station.
    - the same or similar for a mobile platform, e.g. ARGO float.
   
  - Task 1: Transformation of a WMDR1.0 record into a JSON representation (WMDR1.0-JSON)
    - Establish a GEO-JSON schema (work in progress)
    - Write a Python class to expose WMDR1.0 and WMDR1.0-JSON and to transform between the two.
      
  - Task 2: Transformation of WMDR1.0-JSON into WMDR2.0-station, WMDR2.0-obs, WMDR2.0-inst objects
    - Write a Python class to transform a WMDR1.0-JSON into into WMDR2.0-station, WMDR2.0-obs, WMDR2.0-inst objects. Generate WOIs and WEIs on the way (use and map the existing gml-ids) and linkages of the WOIs and WEIs to the WSI.

  - Task 3: Transformation of WMDR2.0-station, WMDR2.0-obs, WMDR2.0-inst objects into ACDD1.3 objects
    - Write a Python class to convert WMDR2.0-station, WMDR2.0-obs, WMDR2.0-inst to ACDD1.3 objects and vice-versa, and expose these objects.
        
- WP3: Use the MeteoGate Ingest API to register and persist a WMDR1.0 record as (linked) ACDD1.3 records
  - Task 1: Implement the chain of transformations on MeteoGate and persist information in DB

- WP4: Use the MeteoGate Output API to retrieve a WMDR2.0 record
  - Task 1: Write a Python class to retrieve an ACDD1.3 record representing either one of, WMDR2.0-station, WMDR2.0-obs, WMDR2.0-inst
    - ACDD1.3 records are snapshots of a state in time. A call to the API thus must allow the user to specify a time or period.
  - Task 2: Based on the context, transform to either WMDR2.0-station, WMDR2.0-obs, WMDR2.0-inst.
  - Task 3: Based on the context, retrieve related ACDD1.3 records, transform to either WMDR2.0-station, WMDR2.0-obs, WMDR2.0-inst, and re-construct a full WMDR2.0 record.
    - The hierarchy of JSON should make it relatively easy to represent a WMDR2.0-full record composed of WMDR2.0-station, WMDR2.0-obs, WMDR2.0-inst parts. 
 
- WP5: Edit a WMDR2.0 record
  - The PoC should test the concept for
    - adding missing or correcting information, i.e. to retrieve an ACDD1.3 record, to add an element, and to persist it again as an updated record
    - adding or correcting history of an element, e.g., document a change of station location at a given point in time, correct erroneous coordinates of a station at a given point in time

   - Task 1 
