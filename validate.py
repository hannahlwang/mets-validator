# function - validateXML -> report array (boolean)
# function - validatefilesecpaths -> array of paths and status
    # pass XML
    # function buildfileseclist (input XML) -> array of paths
    # function validatefileseclist (input array of paths) -> array of paths and status
    # function validatedircontents (walk thru dir and see if it appears in fileseclist) -> array of paths and status
# function - validatederivs -> array of three file types and status (and what was missing) - JSON structure
# function - validatetechmd -> array of jpeg ids and status 

	
from lxml import etree
from io import StringIO
from urllib.request import urlopen
import sys
import os

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
	'xlink': 'http://www.w3.org/1999/xlink'
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

# check that all files in METS are present in package, and that all files in package are present in METS
# def validateFilePaths(xmlin):
	# buildPathStatusArray(xmlin)
	# buildDirStatusArray(xmlin)

def validateDerivs(xmlin):
	
	# open and parse METS xml, define XML namespaces
	tree, root, ns = parseMETS(xmlin)
	
	# create array for storing page IDs and fileIDs for each pdf, jpg, and alto file in scructMap - this will be used to verify whether each file has all 3 derivatives
	pageArray = {}
	
	# create array for reporting the presence of derivatives
	derivStatusArray = {}
	
	# locate all the page tags in the structMap and create array with pdf, jpg, and alto files
	for physPage in root.findall('./mets:structMap/mets:div/mets:div', ns):
		
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
	
	return derivStatusArray

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
		
	print(techMdStatusArray)	

def errorLogOutput(xmlin):
	errorArray = {}
	
	validXmlArray = validateXML(xmlin)
	metsFileName = validXmlArray['mets']
	
	
	errorArray[metsFileName] = {}
	
	if validXmlArray['io-ok'] == False:
		errorArray[metsFileName]['io-ok'] = False
	if validXmlArray['well-formed'] == False:
		errorArray[metsFileName]['well-formed'] = False
	if validXmlArray['valid'] == False:
		errorArray[metsFileName]['valid'] = False
	
	
	pathStatusArray = buildPathStatusArray(xmlin)
	
	for path in pathStatusArray:
		if pathStatusArray[path] == False:
			errorArray[metsFileName]['all-files-present-in-package'] = False
			
	dirStatusArray = buildDirStatusArray(xmlin)
	
	for path in dirStatusArray:
		if dirStatusArray[path] == False:
			errorArray[metsFileName]['all-files-present-in-mets'] = False
	
	derivStatusArray = validateDerivs(xmlin)
	
	for page in derivStatusArray:
		for deriv in derivStatusArray[page]:
			if derivStatusArray[page][deriv] == False:
				errorArray[metsFileName]['all-derivs-present'] = False
				
	
	
	print(errorArray)
	

def metsValidator(metsfile):
	validateDerivs(metsfile)
	validateTechMd(metsfile)
	errorLogOutput(metsfile)
	
metsValidator('wisconsinstatejournal_20190328_mets.xml')
