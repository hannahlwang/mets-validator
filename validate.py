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
		
def buildFilePathList(xmlin):

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
	
	# create list of file paths in the file section which will be used as input for validation
	filePathList = []
	
	# locate all the mets:FLocat tags and add the href attributes to the file path list
	for fileLoc in root.findall('./mets:fileSec/mets:fileGrp/mets:fileGrp/mets:file/mets:FLocat', ns):
		attributes = fileLoc.attrib
		filePath = attributes['{http://www.w3.org/1999/xlink}href']
		filePathList.append(filePath)
	
	print(filePathList)

def metsValidator(xmlin):
	validateXML(xmlin)
	buildFilePathList(xmlin)
	
metsValidator('wisconsinstatejournal_20190328_mets.xml')
