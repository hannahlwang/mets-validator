from lxml import etree
from io import StringIO
from urllib.request import urlopen
import sys
import os
import json
import csv
import itertools

# validate XML against METS XSD schema
def validateXML(xmlin):

	# create report array
	validXmlArray = {
	'mets':xmlin,
	}
		
	# open and read schema file
	xsdin = 'http://www.loc.gov/standards/mets/mets.xsd'
	with urlopen(xsdin) as schema_file:
		schema_to_check = schema_file.read()
		
	# open and read xml file
	with open(xmlin, 'r') as xml_file:
		xml_to_check = xml_file.read()
	
	#parse schema and load into memory as xmlschema_doc
	xmlschema_doc = etree.fromstring(schema_to_check)
	xmlschema = etree.XMLSchema(xmlschema_doc)
	
	# parse xml
	try:
		doc = etree.parse(StringIO(xml_to_check))
		validXmlArray['io-ok'] = True
		validXmlArray['well-formed'] = True

	# check for file IO error
	except IOError as err:
		validXmlArray['io-ok'] = False
		validXmlArray['io-error'] = str(err.error_log)
		return validXmlArray
		quit()

	# check for XML syntax errors
	except etree.XMLSyntaxError as err:
		validXmlArray['well-formed'] = False
		validXmlArray['syntax-error'] = str(err.error_log)
		return validXmlArray
		quit()

	# check for any other unknown errors
	except:
		validXmlArray['other-parsing-error'] = str(sys.exc_info())
		return validXmlArray
		quit()
	
	# validate against schema
	try:
		xmlschema.assertValid(doc)
		validXmlArray['valid'] = True

	except etree.DocumentInvalid as err:
		validXmlArray['valid'] = False
		validXmlArray['validation-error'] = str(err.error_log)
		return validXmlArray
		quit()
		
	except:
		validXmlArray['other-validation-error'] = str(sys.exc_info())
		return validXmlArray
		quit()
	
	return validXmlArray
	
# open and parse METS xml, define XML namespaces
def parseMETS(xmlin):
	# open and read xml file
	with open(xmlin, 'r') as xml_file:
		xml_to_check = xml_file.read()
	
	# parse xml and get root
	tree = etree.parse(StringIO(xml_to_check))
	root = tree.getroot()
	
	# define XML namespaces
	ns = {
	'mets': 'http://www.loc.gov/METS/',
	'xlink': 'http://www.w3.org/1999/xlink',
	'mods': 'http://www.loc.gov/mods/v3'
	}
	
	return tree, root, ns

# build list of file paths based on fileSec paths in METS
def buildFilePathList(xmlin):
	
	# open and parse METS xml, define XML namespaces
	tree, root, ns = parseMETS(xmlin)
	
	# create list of file paths in the file section which will be used as input for validation
	filePathList = []
	
	# locate all the mets:FLocat tags and add the href attributes to the file path list
	for fileLoc in root.findall('./mets:fileSec/mets:fileGrp/mets:fileGrp/mets:file/mets:FLocat', ns):
		attributes = fileLoc.attrib
		filePath = attributes['{http://www.w3.org/1999/xlink}href']
		filePathList.append(filePath)
	
	return filePathList

# check whether file paths in METS (in filePathList) exist in package or not, build array of paths and statuses (boolean)
def buildPathStatusArray(xmlin):
	
	pathlist = buildFilePathList(xmlin)
	
	# compare each file in pathlist against the contents of the system
	pathStatusArray = {}
	
	for filePath in pathlist:
		pathStatusArray[filePath] = os.path.exists(filePath)
	
	return pathStatusArray

# check whether file paths in package exist in METS or not, build array of paths and statuses (boolean)
def buildDirStatusArray(xmlin):
	
	pathlist = buildFilePathList(xmlin) 
	
	# create list of files in system
	dirList = []

	for root, dirs, files in os.walk('.'):
		for name in files:
			dirList.append(os.path.join(root,name).replace('\\','/'))
	
	# compare each file in system list against the METS pathlist
	dirStatusArray = {}
	
	for filePath in dirList:
		if filePath in pathlist:
			dirStatusArray[filePath] = True
		else:
			dirStatusArray[filePath] = False
	
	return dirStatusArray

def validateDerivs(xmlin):
	
	# open and parse METS xml, define XML namespaces
	tree, root, ns = parseMETS(xmlin)
	
	# create array for storing page IDs and fileIDs for each pdf, jpg, and alto file in scructMap - this will be used to verify whether each file has all 3 derivatives
	pageArray = {}
	
	# create array for reporting the presence of derivatives
	derivStatusArray = {}
	
	pageCounter = 0
	
	# locate all the page tags in the structMap and create array with pdf, jpg, and alto files
	for physPage in root.findall('./mets:structMap/mets:div/mets:div', ns):
	
		pageCounter += 1
		
		attributes = physPage.attrib
		pageID = attributes['ID']
		
		pageArray[pageID] = {}
		
		derivStatusArray[pageID] = {}
		
		for filePointer in physPage.findall('./mets:fptr', ns):
			fileID = filePointer.attrib['FILEID']
			if 'PDF' in fileID:
				pageArray[pageID]['pdf'] = fileID
			elif 'JPG' in fileID:
				pageArray[pageID]['jpg'] = fileID
			elif 'ALTO' in fileID:
				pageArray[pageID]['alto'] = fileID
	
		if 'pdf' in pageArray[pageID]:
			derivStatusArray[pageID]['pdf'] = True
		elif 'pdf' not in pageArray[pageID]:
			derivStatusArray[pageID]['pdf'] = False
			
		if 'jpg' in pageArray[pageID]:
			derivStatusArray[pageID]['jpg'] = True
		elif 'jpg' not in pageArray[pageID]:
			derivStatusArray[pageID]['jpg'] = False
			
		if 'alto' in pageArray[pageID]:
			derivStatusArray[pageID]['alto'] = True
		elif 'alto' not in pageArray[pageID]:
			derivStatusArray[pageID]['alto'] = False
	
	return derivStatusArray, pageCounter

def validateTechMd(xmlin):
	
	# open and parse METS xml, define XML namespaces
	tree, root, ns = parseMETS(xmlin)
	
	techMdStatusArray = {}
	
	for jpgFile in root.findall('./mets:fileSec/mets:fileGrp[@ID="ImageJpgGroup"]/mets:fileGrp[@ID="JPGFiles"]/mets:file', ns):
		fileID = jpgFile.attrib['ID']
		admID = jpgFile.attrib['ADMID']
		techMdStatusArray[fileID] = {}
		techMdStatusArray[fileID]['ADMID'] = admID
	
	techMdArray = []
	for techMdEntry in root.findall('./mets:amdSec[@ID="TECH_MD"]/mets:techMD', ns):
		admID = techMdEntry.attrib['ID']
		techMdArray.append(admID)
	
	for fileID in techMdStatusArray :
		if techMdStatusArray[fileID]['ADMID'] in techMdArray:
			techMdStatusArray[fileID]['techMD'] = True
		else:
			techMdStatusArray[fileID]['techMD'] = False
		
	return techMdStatusArray

def logDescMd(xmlin):

	# open and parse METS xml, define XML namespaces
	tree, root, ns = parseMETS(xmlin)
	
	descMdArray = {}
	
	mods = root.find('./mets:dmdSec/mets:mdWrap/mets:xmlData/mods:mods', ns)
	
	title = mods.find('./mods:titleInfo/mods:title', ns).text
	descMdArray['Title'] = title
	
	dateIssued = mods.find('./mods:originInfo/mods:dateIssued', ns).text
	descMdArray['Date issued'] = dateIssued
	
	edition = mods.find('./mods:originInfo/mods:edition', ns).text
	descMdArray['Edition'] = edition
	
	language = mods.find('./mods:language/mods:languageTerm', ns).text
	descMdArray['Language'] = language
	
	catalogueIdentifier = mods.find("./mods:identifier[@type='CatalogueIdentifier']", ns).text
	descMdArray['Catalogue identifier'] = catalogueIdentifier
	
	lccn = mods.find("./mods:identifier[@type='lccn']", ns).text
	descMdArray['lccn'] = lccn
		
	return descMdArray

def loggingOutput(xmlin):
	errorArray = {}
	curatorReportArray = {}
	
	validXmlArray = validateXML(xmlin)
	metsFileName = validXmlArray['mets']
	
	errorArray[metsFileName] = {}
	curatorReportArray[metsFileName] = {}
	
	if validXmlArray['well-formed'] == False or  validXmlArray['valid'] == False:
		errorArray[metsFileName] = {
			'validation errors' : validXmlArray
		}
		print(json.dumps(errorArray, indent=4))
		
		curatorReportArray[metsFileName] = {
			'Valid METS' : 'No'
		}
		print(json.dumps(curatorReportArray, indent=4))
		quit()
	
	else:
		curatorReportArray[metsFileName] = {
			'Valid METS' : 'Yes'
		}
	
	descMdArray = logDescMd(xmlin)
	
	curatorReportArray[metsFileName].update(descMdArray)
	
	pathStatusArray = buildPathStatusArray(xmlin)
	errorArray[metsFileName]['files in mets not in package'] = []
	
	for path in pathStatusArray:
		if pathStatusArray[path] == False:
			errorArray[metsFileName]['files in mets not in package'].append(path)
	
	if errorArray[metsFileName]['files in mets not in package'] == []:
		errorArray[metsFileName].pop('files in mets not in package')
		curatorReportArray[metsFileName]['All files from METS present in package'] = 'Yes'
	else:
		curatorReportArray[metsFileName]['All files from METS present in package'] = 'No'
	
	dirStatusArray = buildDirStatusArray(xmlin)
	errorArray[metsFileName]['files in package not in mets'] = []
	
	for path in dirStatusArray:
		if dirStatusArray[path] == False:
			errorArray[metsFileName]['files in package not in mets'].append(path)
			
	if errorArray[metsFileName]['files in package not in mets'] == []:
		errorArray[metsFileName].pop('files in package not in mets')
		curatorReportArray[metsFileName]['All files in package present in METS'] = 'Yes'
	else:
		curatorReportArray[metsFileName]['All files in package present in METS'] = 'No'
	
	derivStatusArray, pageCounter = validateDerivs(xmlin)
	
	curatorReportArray[metsFileName]['Number of pages'] = pageCounter
	errorArray[metsFileName]['missing derivatives'] = {}
	
	for page in derivStatusArray:
		errorArray[metsFileName]['missing derivatives'][page] = []
		for deriv in derivStatusArray[page]:
			if derivStatusArray[page][deriv] == False:
				errorArray[metsFileName]['missing derivatives'][page].append(deriv)
		
		if errorArray[metsFileName]['missing derivatives'][page] == []:
			errorArray[metsFileName]['missing derivatives'].pop(page)
			
	if errorArray[metsFileName]['missing derivatives'] == {}:
		errorArray[metsFileName].pop('missing derivatives')
		curatorReportArray[metsFileName]['Each page has PDF, JPG, and Alto'] = 'Yes'
	else:
		curatorReportArray[metsFileName]['Each page has PDF, JPG, and Alto'] = 'No'
				
	techMdStatusArray = validateTechMd(xmlin)
	errorArray[metsFileName]['missing technical metadata'] = []
	
	for jpgFile in techMdStatusArray:
		if techMdStatusArray[jpgFile]['techMD'] == False:
			errorArray[metsFileName]['missing technical metadata'].append(jpgFile)
			
	if errorArray[metsFileName]['missing technical metadata'] == []:
		errorArray[metsFileName].pop('missing technical metadata')
		curatorReportArray[metsFileName]['Technical metadata for each JPG'] = 'Yes'
	else:
		curatorReportArray[metsFileName]['Technical metadata for each JPG'] = 'False'
	
	print(json.dumps(errorArray, indent=4))
	# print(json.dumps(curatorReportArray, indent=4))
	
	fields = ['METS filename','Valid METS','Title','Date issued', 'Edition', 'Language', 'Catalogue identifier', 'lccn', 'Number of pages', 'All files from METS present in package', 'All files in package present in METS', 'Each page has PDF, JPG, and Alto', 'Technical metadata for each JPG']
	
	with open('report.csv', 'w') as f:
		w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
		w.writeheader()
		for key,val in sorted(curatorReportArray.items()):
			row = {'METS filename':key}
			row.update(val)
			w.writerow(row)
	

def metsValidator(metsfile):
	loggingOutput(metsfile)
	
metsValidator('wisconsinstatejournal_20190328_mets.xml')
