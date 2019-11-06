# mets-validator

## Requirements

* [Python 3](https://www.python.org/download/releases/3.0/)
* [lxml](https://lxml.de/installation.html)

## Steps

1. Validate XML against METS schema
2. Verify that all files in fileSec are present at paths
3. Verify that all files in package are present in METS fileSec
4. Verify that each page (mets:div) in mets:structMap has a pdf, jpg, and alto file
5. Verify that for each jpg file in the ImageJpgGroup, there is a mets:techMD section within mets:amdSec with an ID that corresponds to the ADMID for the jpg
6. If any of these things are false, report in log:
	* Validation errors
	* Files in METS not present in package
	* Files in package not present in METS
	* Pages with missing derivatives (PDFs, JPGs, ALTO)
	* JPGs without technical metadata 
	
## Final reporting output

For each issue, include line in report.csv with the following fields:

* METS filename
* Valid METS (Yes/No)
* Title
* Date issued (YYYY-MM-DD)
* Edition
* Language
* Catalogue Identifier
* lccn
* Number of pages
* All files from METS present in package (Yes/No)
* All files in package present in METS (Yes/No)
* Each page has PDF, JPG, and Alto	(Yes/No)
* Technical metadata for each JPG (Yes/No)