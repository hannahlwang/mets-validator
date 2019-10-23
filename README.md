# mets-validator

## Steps
1. Validate XML against METS schema
2. Verify that all files in fileSec are present at paths
3. Verify that each page (mets:div) in mets:structMap has a pdf, jpg, and alto file
4. Verify that for each jpg file in the ImageJpgGroup, there is a mets:techMD section within mets:amdSec with an ID that corresponds to the ADMID for the jpg
5. If any of these things are false, report in logfile:
	- Invalid METS
	- Files not present at paths
	- Pages with missing PDFs
	- Pages with missing JPGs
	- Pages with missing Alto XML
	- JPGs without technical metadata 