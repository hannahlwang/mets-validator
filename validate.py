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
		print(validXmlArray)

	# check for XML syntax errors
	except etree.XMLSyntaxError as err:
		validXmlArray['well-formed'] = False
		validXmlArray['syntax-error'] = str(err.error_log)
		print(validXmlArray)
		quit()

	# check for any other unknown errors
	except:
		validXmlArray['other-parsing-error'] = str(sys.exc_info())
		print(validXmlArray)
		quit()
	
	# validate against schema
	try:
		xmlschema.assertValid(doc)
		validXmlArray['valid'] = True

	except etree.DocumentInvalid as err:
		validXmlArray['valid'] = False
		validXmlArray['validation-error'] = str(err.error_log)
		print(validXmlArray)
		quit()
		
	except:
		validXmlArray['other-validation-error'] = str(sys.exc_info())
		print(validXmlArray)
		quit()
	
	print(validXmlArray)
	
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

# check whether file paths in METS exist in package or not, build array of paths and statuses (boolean)
def buildPathStatusArray(pathlist):
	
	pathStatusArray = {}

	for filePath in pathlist:
		pathStatusArray[filePath] = os.path.exists(filePath)
	
	print(pathStatusArray)


# check whether file paths in package exist in METS or not, build array of paths and statuses (boolean)
def buildDirStatusArray(pathlist):

	dirList = []
	
	for root, dirs, files in os.walk('.'):
		for name in files:
			dirList.append(os.path.join(root,name).replace('\\','/'))
	
	dirStatusArray = {}
	
	for filePath in dirList:
		if filePath in pathlist:
			dirStatusArray[filePath] = True
		else:
			dirStatusArray[filePath] = False
	
	print(dirStatusArray)

def validateFilePaths(xmlin):
	buildPathStatusArray(buildFilePathList(xmlin))
	buildDirStatusArray(buildFilePathList(xmlin))

def validateDerivs(xmlin):
	
	# open and parse METS xml, define XML namespaces
	tree, root, ns = parseMETS(xmlin)
	
	pageArray = {}
	
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
	
	print(derivStatusArray)

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
	

def metsValidator(metsfile):
	validateXML(metsfile)
	validateFilePaths(metsfile)
	validateDerivs(metsfile)
	validateTechMd(metsfile)
	
metsValidator('wisconsinstatejournal_20190328_mets.xml')
