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
		validXmlArray['value-ok'] = True
		validXmlArray['io-ok'] = True
		validXmlArray['well-formed'] = True
		
	except ValueError as err:
		validXmlArray['value-ok'] = False
		validXmlArray['value-error'] = str(err)
		return validXmlArray
		quit()
		
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
	filePathArray = {}
	
	# locate all the mets:FLocat tags and add the href attributes to the file path list
	for metsFile in root.findall('./mets:fileSec/mets:fileGrp/mets:fileGrp/mets:file', ns):
		fileId = metsFile.attrib['ID']
		filePath = metsFile.find('./mets:FLocat',ns).attrib['{http://www.w3.org/1999/xlink}href']
		filePathArray[fileId] = filePath
	
	return filePathArray

# check whether file paths in METS (in filePathArray) exist in package or not, build array of paths and statuses (boolean)
def buildPathStatusArray(xmlin):
	
	filePathArray = buildFilePathList(xmlin)
	
	rootDir = os.path.dirname(xmlin)
	
	# compare each file in pathlist against the contents of the system
	pathStatusArray = {}
	
	for filePath in filePathArray.values():
		# fullFilePath = os.path.join
		pathStatusArray[filePath] = os.path.exists(os.path.join(rootDir,filePath))
	
	return pathStatusArray
	# print(pathStatusArray)

# check whether file paths in package exist in METS or not, build array of paths and statuses (boolean)
def buildDirStatusArray(xmlin):
	
	filePathArray = buildFilePathList(xmlin)
	
	rootDir = os.path.dirname(xmlin)
	
	# create list of files in system
	dirList = []

	for root, dirs, files in os.walk(rootDir):
		for name in files:
			dirList.append(os.path.join(root,name).replace('\\','/').replace(rootDir,'.'))
	
	dirList.remove(xmlin.replace('\\','/').replace(rootDir,'.'))
	
	# compare each file in system list against the METS pathlist
	dirStatusArray = {}
	
	for filePath in dirList:
		if filePath in filePathArray.values():
			dirStatusArray[filePath] = True
		else:
			dirStatusArray[filePath] = False
	
	return dirStatusArray
	# print(dirStatusArray)
	
def buildPageArray(xmlin):
	# open and parse METS xml, define XML namespaces
	tree, root, ns = parseMETS(xmlin)
	
	# create array for storing page IDs and fileIDs for each pdf, jpg, and alto file in scructMap - this will be used to verify whether each file has all 3 derivatives
	pageArray = {}
	
	# create array for reporting the presence of derivatives
	derivStatusArray = {}
	
	pageCounter = 0
	
	filePathArray = buildFilePathList(xmlin)
	
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
				pageArray[pageID]['pdf'] = {'ID' : fileID}
				pageArray[pageID]['pdf']['filename'] = filePathArray.get(fileID)
			elif 'JPG' in fileID:
				pageArray[pageID]['jpg'] = {'ID' : fileID}
				pageArray[pageID]['jpg']['filename'] = filePathArray.get(fileID)
			elif 'ALTO' in fileID:
				pageArray[pageID]['alto'] = {'ID' : fileID}
				pageArray[pageID]['alto']['filename'] = filePathArray.get(fileID)
	
	return pageArray, pageCounter
	
def buildMissingFilenameArray(xmlin):
	
	pageArray, pageCounter = buildPageArray(xmlin)
	
	missingFilenameArray = {}
	
	for pageID in pageArray:

		missingFilenameArray[pageID] = []
		
		pdfDeriv = pageArray[pageID].get('pdf')
		jpgDeriv = pageArray[pageID].get('jpg')
		altoDeriv = pageArray[pageID].get('alto')
		
		if pdfDeriv:
			if pageArray[pageID]['pdf']['filename'] == None:
				if jpgDeriv:
					pdfName = pageArray[pageID]['jpg']['filename'].replace('jpg','pdf')
				elif altoDeriv:
					pdfName = pageArray[pageID]['alto']['filename'].replace('xml','pdf').replace('alto','images/pdf')
				else:
					pdfName = 'unknown pdf'
				missingFilenameArray[pageID].append(pdfName)
		else:
			if jpgDeriv:
				pdfName = pageArray[pageID]['jpg']['filename'].replace('jpg','pdf')
			elif altoDeriv:
				pdfName = pageArray[pageID]['alto']['filename'].replace('xml','pdf').replace('alto','images/pdf')
			else:
				pdfName = 'unknown pdf'
			missingFilenameArray[pageID].append(pdfName)
				
				
		if jpgDeriv:
			if pageArray[pageID]['jpg']['filename'] == None:
				if pdfDeriv:
					jpgName = pageArray[pageID]['pdf']['filename'].replace('pdf','jpg')
				elif altoDeriv:
					jpgName = pageArray[pageID]['alto']['filename'].replace('xml','jpg').replace('alto','images/jpg')
				else:
					jpgName = 'unknown jpg'
				missingFilenameArray[pageID].append(jpgName)
		else:
			if pdfDeriv:
				jpgName = pageArray[pageID]['pdf']['filename'].replace('pdf','jpg')
			elif altoDeriv:
				jpgName = pageArray[pageID]['alto']['filename'].replace('xml','jpg').replace('alto','images/jpg')
			else:
				jpgName = 'unknown jpg'
			missingFilenameArray[pageID].append(jpgName)
		
		
		if altoDeriv:
			if pageArray[pageID]['alto']['filename'] == None:
				if pdfDeriv:
					altoName = pageArray[pageID]['pdf']['filename'].replace('.pdf','.xml').replace('images/pdf','alto')
				elif jpgDeriv:
					altoName = pageArray[pageID]['jpg']['filename'].replace('.jpg','.xml').replace('images/jpg','alto')
				else:
					altoName = 'unknown alto'
				missingFilenameArray[pageID].append(altoName)
		else:
			if pdfDeriv:
				altoName = pageArray[pageID]['pdf']['filename'].replace('.pdf','.xml').replace('images/pdf','alto')
			elif jpgDeriv:
				altoName = pageArray[pageID]['jpg']['filename'].replace('.jpg','.xml').replace('images/jpg','alto')
			else:
				altoName = 'unknown alto'
			missingFilenameArray[pageID].append(altoName)
		
	# print('\nmissingFilenameArray\n')
	# print(missingFilenameArray)
	return missingFilenameArray

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
	
	metsHdr = root.find('./mets:metsHdr', ns)
	
	for elem in metsHdr.iter():
		mhtree = etree.ElementTree(metsHdr)
		if elem.text:
			descMdArray[mhtree.getpath(elem)] = elem.text
	
	mods = root.find('./mets:dmdSec/mets:mdWrap/mets:xmlData/mods:mods', ns)
	
	for elem in mods.iter():
		mtree = etree.ElementTree(mods)
		if elem.text:
			descMdArray[mtree.getpath(elem)] = elem.text
		
	return descMdArray
	# print(descMdArray)

def createCuratorReport(reportname):

	fields = ['METS filename','Valid METS','/mets:metsHdr/mets:agent[1]/mets:name', '/mets:metsHdr/mets:agent[2]/mets:name', '/mets:metsHdr/mets:agent[3]/mets:name', '/mods:mods/mods:titleInfo/mods:title', '/mods:mods/mods:typeOfResource', '/mods:mods/mods:genre', '/mods:mods/mods:originInfo/mods:dateIssued', '/mods:mods/mods:originInfo/mods:edition', '/mods:mods/mods:language/mods:languageTerm', '/mods:mods/mods:identifier[1]', '/mods:mods/mods:identifier[2]', '/mods:mods/mods:identifier[3]', '/mods:mods/mods:recordInfo/mods:recordContentSource', 'Number of pages', 'All files from METS present in package', 'All files in package present in METS', 'Each page has PDF, JPG, and Alto', 'Technical metadata for each JPG']
	
	with open(reportname, 'w') as f:
		w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
		w.writeheader()
			
def writeToCuratorReport(reportname,reportarray):
	fields = ['METS filename','Valid METS','/mets:metsHdr/mets:agent[1]/mets:name', '/mets:metsHdr/mets:agent[2]/mets:name', '/mets:metsHdr/mets:agent[3]/mets:name', '/mods:mods/mods:titleInfo/mods:title', '/mods:mods/mods:typeOfResource', '/mods:mods/mods:genre', '/mods:mods/mods:originInfo/mods:dateIssued', '/mods:mods/mods:originInfo/mods:edition', '/mods:mods/mods:language/mods:languageTerm', '/mods:mods/mods:identifier[1]', '/mods:mods/mods:identifier[2]', '/mods:mods/mods:identifier[3]', '/mods:mods/mods:recordInfo/mods:recordContentSource', 'Number of pages', 'All files from METS present in package', 'All files in package present in METS', 'Each page has PDF, JPG, and Alto', 'Technical metadata for each JPG']
	
	with open(reportname, 'a') as f:
		w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
		for key,val in sorted(reportarray.items()):
			row = {'METS filename':key}
			row.update(val)
			w.writerow(row)


def loggingOutput(xmlin,reportname):
	
	errorArray = {}
	curatorReportArray = {}
	
	validXmlArray = validateXML(xmlin)
	metsFileName = validXmlArray['mets']
	
	errorArray[metsFileName] = {}
	curatorReportArray[metsFileName] = {}
	
	if validXmlArray['value-ok'] == False or validXmlArray['io-ok'] == False or validXmlArray['well-formed'] == False or  validXmlArray['valid'] == False:
		errorArray[metsFileName] = {
			'validation errors' : validXmlArray
		}
		print(json.dumps(errorArray, indent=4))
		
		curatorReportArray[metsFileName] = {
			'Valid METS' : 'No'
		}
		
		writeToCuratorReport(reportname,curatorReportArray)
		
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
		
	pageArray, pageCounter = buildPageArray(xmlin)
	
	missingFilenameArray = buildMissingFilenameArray(xmlin)
	
	curatorReportArray[metsFileName]['Number of pages'] = pageCounter
	errorArray[metsFileName]['missing derivatives in structMap'] = {}
	
	for page in missingFilenameArray:
		errorArray[metsFileName]['missing derivatives in structMap'][page] = []
		if missingFilenameArray[page] != []:
			errorArray[metsFileName]['missing derivatives in structMap'][page].append(missingFilenameArray[page])
		
		if errorArray[metsFileName]['missing derivatives in structMap'][page] == []:
			errorArray[metsFileName]['missing derivatives in structMap'].pop(page)
			
	if errorArray[metsFileName]['missing derivatives in structMap'] == {}:
		errorArray[metsFileName].pop('missing derivatives in structMap')
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
	
	if errorArray[metsFileName] != {}:
		print(json.dumps(errorArray, indent=4))
	
	writeToCuratorReport(reportname,curatorReportArray)

def findMetsFiles(rootfolder):

	metsFileList = []
	
	for root, dirs, files in os.walk(rootfolder):
		for name in files:
			if '_mets.xml' in name:
				metsFileList.append(os.path.join(root,name).replace('\\','/'))
	
	return metsFileList

createCuratorReport('report.csv')

for metsFile in findMetsFiles('M:\mets-data'):
	loggingOutput(metsFile,'report.csv')
	

