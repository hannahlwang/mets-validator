"""
mets-validator
---

A Python validation tool for METS packages.

For information on usage and dependencies, see:
github.com/hannahlwang/mets-validator

"""

from lxml import etree
from io import StringIO, BytesIO
from urllib.request import urlopen
import sys
import os
import json
import csv
import itertools
from datetime import datetime

# validate XML against METS XSD schema
def validateXML(xmlschema, xmlin):

    # create report array
    validXmlArray = {
    'mets':xmlin,
    'value-ok':'',
    'io-ok':'',
    'well-formed':'',
    'valid':''
    }
        
    # # open and read schema file
    # xsdin = 'http://www.loc.gov/standards/mets/mets.xsd'
    # with urlopen(xsdin) as schema_file:
        # schema_to_check = schema_file.read()
        
    # open and read xml file
    with open(xmlin, 'r') as xml_file:
        xml_to_check = xml_file.read()
    
    # #parse schema and load into memory as xmlschema_doc
    # xmlschema_doc = etree.fromstring(schema_to_check)
    # xmlschema = etree.XMLSchema(xmlschema_doc)
    
    # parse xml
    
    try:
        # tree = etree.parse(StringIO(xml_to_check))
        # print(tree)
        utf8_parser = etree.XMLParser(encoding='utf-8')
        doc = etree.fromstring(xml_to_check.encode('utf-8'), parser=utf8_parser)
        # print(doc)
        validXmlArray['value-ok'] = True
        validXmlArray['io-ok'] = True
        validXmlArray['well-formed'] = True
        
    except ValueError as err:
        validXmlArray['value-ok'] = False
        validXmlArray['value-error'] = str(err)
        
    # check for file IO error
    except IOError as err:
        validXmlArray['io-ok'] = False
        validXmlArray['io-error'] = str(err.error_log)

    # check for XML syntax errors
    except etree.XMLSyntaxError as err:
        validXmlArray['well-formed'] = False
        validXmlArray['syntax-error'] = str(err.error_log)

    # check for any other unknown errors
    except:
        validXmlArray['other-parsing-error'] = str(sys.exc_info())
    
    # validate against schema
    try:
        xmlschema.assertValid(doc)
        validXmlArray['valid'] = True

    except etree.DocumentInvalid as err:
        validXmlArray['valid'] = False
        validXmlArray['validation-error'] = str(err.error_log)
        
    except:
        validXmlArray['other-validation-error'] = str(sys.exc_info())
    
    return validXmlArray
    
# open and parse METS xml, define XML namespaces
def parseMETS(xmlin):
    # open and read xml file
    with open(xmlin, 'r') as xml_file:
        xml_to_check = xml_file.read()
    
    # parse xml and get root
    utf8_parser = etree.XMLParser(encoding='utf-8')
    root = etree.fromstring(xml_to_check.encode('utf-8'), parser=utf8_parser)
    # tree = etree.parse(StringIO(xml_to_check))
    # root = tree.getroot()
    
    # define XML namespaces
    ns = {
    'mets': 'http://www.loc.gov/METS/',
    'xlink': 'http://www.w3.org/1999/xlink',
    'mods': 'http://www.loc.gov/mods/v3'
    }
    
    return root, ns

# build list of file paths based on fileSec paths in METS
def buildFilePathList(xmlin):
    
    # open and parse METS xml, define XML namespaces
    root, ns = parseMETS(xmlin)
    
    # create list of file paths in the file section which will be used as input for validation
    filePathArray = {}
    
    # locate all the mets:FLocat tags and add the href attributes to the file path list
    for metsFile in root.findall('./mets:fileSec/mets:fileGrp/mets:fileGrp/mets:file', ns):
        fileId = metsFile.attrib['ID']
        filePath = metsFile.find('./mets:FLocat',ns).attrib['{http://www.w3.org/1999/xlink}href']
        filePathArray[fileId] = filePath
    
    return filePathArray
    
def buildDirList(xmlin):
    
    rootDir = os.path.dirname(xmlin)
    
    dirList = []

    for root, dirs, files in os.walk(rootDir):
        for name in files:
            dirList.append(os.path.join(root,name).replace('\\','/').replace(rootDir,'.'))
    
    dirList.remove(xmlin.replace('\\','/').replace(rootDir,'.'))
    
    return dirList

# check whether file paths in METS (in filePathArray) exist in package or not, build array of paths and statuses (boolean)
def buildPathStatusArray(xmlin):
    
    filePathArray = buildFilePathList(xmlin)
    
    dirList = buildDirList(xmlin)
    
    # compare each file in pathlist against the contents of the system
    pathStatusArray = {}
    
    for filePath in filePathArray.values():
        pathStatusArray[filePath] = filePath in dirList
    
    return pathStatusArray

# check whether file paths in package exist in METS or not, build array of paths and statuses (boolean)
def buildDirStatusArray(xmlin):
    
    filePathArray = buildFilePathList(xmlin)
    
    dirList = buildDirList(xmlin)
    
    # compare each file in system list against the METS pathlist
    dirStatusArray = {}
    
    for filePath in dirList:
        if filePath in filePathArray.values():
            dirStatusArray[filePath] = True
        else:
            dirStatusArray[filePath] = False
    
    return dirStatusArray

# create array for storing page IDs and fileIDs for each pdf, jpg, and alto file in scructMap - this will be used to verify whether each file has all 3 derivatives. Also count number of pages in structMap, to be included in final report.
def buildPageArray(xmlin):
    # open and parse METS xml, define XML namespaces
    root, ns = parseMETS(xmlin)
    
    pageArray = {}
    
    pageCounter = 0
    
    filePathArray = buildFilePathList(xmlin)
    
    # locate all the page tags in the structMap and create array with pdf, jpg, and alto files
    for physPage in root.findall('./mets:structMap/mets:div/mets:div', ns):
    
        pageCounter += 1
        
        attributes = physPage.attrib
        pageID = attributes['ID']
        
        pageArray[pageID] = {}
        
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

# create a list of filenames for missing files in structMap. 
def buildMissingFilenameArray(xmlin):
    
    pageArray, pageCounter = buildPageArray(xmlin)
    
    missingFilenameArray = {}
    
    for pageID in pageArray:

        missingFilenameArray[pageID] = {}
        
        pdfDeriv = pageArray[pageID].get('pdf')
        jpgDeriv = pageArray[pageID].get('jpg')
        altoDeriv = pageArray[pageID].get('alto')
        
        if pdfDeriv:
            if pdfDeriv['filename'] == None:
                if jpgDeriv:
                    pdfID = jpgDeriv['ID'].replace('JPG','PDF')
                    pdfName = jpgDeriv['filename'].replace('jpg','pdf')
                elif altoDeriv:
                    pdfID = altoDeriv['ID'].replace('ALTO','PDF')
                    pdfName = altoDeriv['filename'].replace('xml','pdf').replace('alto','images/pdf')
                else:
                    pdfID = 'unknown PDF ID'
                    pdfName = 'unknown PDF filename'
                missingFilenameArray[pageID][pdfID] = pdfName
        else:
            if jpgDeriv:
                pdfID = jpgDeriv['ID'].replace('JPG','PDF')
                pdfName = jpgDeriv['filename'].replace('jpg','pdf')
            elif altoDeriv:
                pdfID = altoDeriv['ID'].replace('ALTO','PDF')
                pdfName = altoDeriv['filename'].replace('xml','pdf').replace('alto','images/pdf')
            else:
                pdfID = 'unknown PDF ID'
                pdfName = 'unknown PDF filename'
            missingFilenameArray[pageID][pdfID] = pdfName
                
                
        if jpgDeriv:
            if jpgDeriv['filename'] == None:
                if pdfDeriv:
                    jpgID = pdfDeriv['ID'].replace('PDF','JPG')
                    jpgName = pdfDeriv['filename'].replace('pdf','jpg')
                elif altoDeriv:
                    jpgID = altoDeriv['ID'].replace('ALTO','JPG')
                    jpgName = altoDeriv['filename'].replace('xml','jpg').replace('alto','images/jpg')
                else:
                    jpgID = 'unknown JPG ID'
                    jpgName = 'unknown JPG filename'
                missingFilenameArray[pageID][jpgID] = jpgName
        else:
            if pdfDeriv:
                jpgID = pdfDeriv['ID'].replace('PDF','JPG')
                jpgName = pdfDeriv['filename'].replace('pdf','jpg')
            elif altoDeriv:
                jpgID = altoDeriv['ID'].replace('ALTO','JPG')
                jpgName = altoDeriv['filename'].replace('xml','jpg').replace('alto','images/jpg')
            else:
                jpgID = 'unknown JPG ID'
                jpgName = 'unknown JPG filename'
            missingFilenameArray[pageID][jpgID] = jpgName
        
        
        if altoDeriv:
            if altoDeriv['filename'] == None:
                if pdfDeriv:
                    altoID = pdfDeriv['ID'].replace('PDF','ALTO')
                    altoName = pdfDeriv['filename'].replace('.pdf','.xml').replace('images/pdf','alto')
                elif jpgDeriv:
                    altoID = jpgDeriv['ID'].replace('JPG','ALTO')
                    altoName = jpgDeriv['filename'].replace('.jpg','.xml').replace('images/jpg','alto')
                else:
                    altoID = 'unknown ALTO ID'
                    altoName = 'unknown ALTO filename'
                missingFilenameArray[pageID][altoID] = altoName
        else:
            if pdfDeriv:
                altoID = pdfDeriv['ID'].replace('PDF','ALTO')
                altoName = pdfDeriv['filename'].replace('.pdf','.xml').replace('images/pdf','alto')
            elif jpgDeriv:
                altoID = jpgDeriv['ID'].replace('JPG','ALTO')
                altoName = jpgDeriv['filename'].replace('.jpg','.xml').replace('images/jpg','alto')
            else:
                altoID = 'unknown ALTO ID'
                altoName = 'unknown ALTO filename'
            missingFilenameArray[pageID][altoID] = altoName
        
    return missingFilenameArray

# create array of JPG files in fileSec and whether or not they have technical metadata in the amdSec
def validateTechMd(xmlin):
    
    # open and parse METS xml, define XML namespaces
    root, ns = parseMETS(xmlin)
    
    filePathArray = buildFilePathList(xmlin)
    
    techMdStatusArray = {}
    
    for jpgFile in root.findall('./mets:fileSec/mets:fileGrp[@ID="ImageJpgGroup"]/mets:fileGrp[@ID="JPGFiles"]/mets:file', ns):
        fileID = jpgFile.attrib['ID']
        admID = jpgFile.attrib['ADMID']
        jpgFilename = filePathArray[fileID]
        techMdStatusArray[fileID] = {}
        techMdStatusArray[fileID]['ADMID'] = admID
        techMdStatusArray[fileID]['JPG filename'] = jpgFilename
    
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

# create an array of descriptive metadata fields in mets:metsHdr and mets:dmdSec section
def logDescMd(xmlin):

    # open and parse METS xml, define XML namespaces
    root, ns = parseMETS(xmlin)
    
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
    
# def createCuratorReport(reportname):

    # fields = ['METS filename','Valid METS','/mets:metsHdr/mets:agent[1]/mets:name', '/mets:metsHdr/mets:agent[2]/mets:name', '/mets:metsHdr/mets:agent[3]/mets:name', '/mods:mods/mods:titleInfo/mods:title', '/mods:mods/mods:typeOfResource', '/mods:mods/mods:genre', '/mods:mods/mods:originInfo/mods:dateIssued', '/mods:mods/mods:originInfo/mods:edition', '/mods:mods/mods:language/mods:languageTerm', '/mods:mods/mods:identifier[1]', '/mods:mods/mods:identifier[2]', '/mods:mods/mods:identifier[3]', '/mods:mods/mods:recordInfo/mods:recordContentSource', 'Number of pages', 'All files from METS present in package', 'All files in package present in METS', 'Each page has PDF, JPG, and Alto', 'Technical metadata for each JPG']
    
    # with open(reportname, 'w') as f:
        # w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        # w.writeheader()
            
def writeToCuratorReport(reportname,reportarray):
    fields = ['METS filename','Valid METS','/mets:metsHdr/mets:agent[1]/mets:name', '/mets:metsHdr/mets:agent[2]/mets:name', '/mets:metsHdr/mets:agent[3]/mets:name', '/mods:mods/mods:titleInfo/mods:title', '/mods:mods/mods:typeOfResource', '/mods:mods/mods:genre', '/mods:mods/mods:originInfo/mods:dateIssued', '/mods:mods/mods:originInfo/mods:edition', '/mods:mods/mods:language/mods:languageTerm', '/mods:mods/mods:identifier[1]', '/mods:mods/mods:identifier[2]', '/mods:mods/mods:identifier[3]', '/mods:mods/mods:recordInfo/mods:recordContentSource', 'Number of pages', 'All files from METS present in package', 'All files in package present in METS', 'Each page has PDF, JPG, and Alto', 'Technical metadata for each JPG']
    
    with open(reportname, 'a') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        for key,val in sorted(reportarray.items()):
            row = {'METS filename':key}
            row.update(val)
            w.writerow(row)

def findMetsFiles(rootfolder):

    metsFileList = []
    
    for root, dirs, files in os.walk(rootfolder):
        for name in files:
            if '_mets.xml' in name:
                metsFileList.append(os.path.join(root,name).replace('\\','/'))
    
    return metsFileList

# startTime = datetime.now()

fields = ['METS filename','Valid METS','/mets:metsHdr/mets:agent[1]/mets:name', '/mets:metsHdr/mets:agent[2]/mets:name', '/mets:metsHdr/mets:agent[3]/mets:name', '/mods:mods/mods:titleInfo/mods:title', '/mods:mods/mods:typeOfResource', '/mods:mods/mods:genre', '/mods:mods/mods:originInfo/mods:dateIssued', '/mods:mods/mods:originInfo/mods:edition', '/mods:mods/mods:language/mods:languageTerm', '/mods:mods/mods:identifier[1]', '/mods:mods/mods:identifier[2]', '/mods:mods/mods:identifier[3]', '/mods:mods/mods:recordInfo/mods:recordContentSource', 'Number of pages', 'All files from METS present in package', 'All files in package present in METS', 'Each page has PDF, JPG, and Alto', 'Technical metadata for each JPG']

with open('report.csv', 'w') as f:
    w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
    w.writeheader()

open('output.log', 'w')

# openTime = datetime.now()
# print('openTime ' + str(openTime - startTime))

# open and read schema file
xsdin = 'http://www.loc.gov/standards/mets/mets.xsd'
with urlopen(xsdin) as schema_file:
    schema_to_check = schema_file.read()
    
#parse schema and load into memory as xmlschema_doc
xmlschema_doc = etree.fromstring(schema_to_check)
xmlschema = etree.XMLSchema(xmlschema_doc)

for xmlin in findMetsFiles(sys.argv[1]):
    
    # startLoopTime = datetime.now()
    
    errorArray = {}
    curatorReportArray = {}
    
    validXmlArray = validateXML(xmlschema,xmlin)
    metsFileName = validXmlArray['mets']
    
    errorArray[metsFileName] = {}
    curatorReportArray[metsFileName] = {}
    
    # print(metsFileName)

    if validXmlArray['value-ok'] == False or validXmlArray['io-ok'] == False or validXmlArray['well-formed'] == False or  validXmlArray['valid'] == False:
        
        errorArray[metsFileName] = {
            'validation errors' : validXmlArray
        }
        
        with open('output.log', 'a') as f:
            f.write(json.dumps(errorArray, indent=4))
            
        curatorReportArray[metsFileName] = {
            'Valid METS' : 'No'
        }
        
        writeToCuratorReport('report.csv',curatorReportArray)
        
        # invalidTime = datetime.now()
        # print('invalidTime ' + str(invalidTime - startLoopTime))
        
        continue
        
    curatorReportArray[metsFileName] = {
        'Valid METS' : 'Yes'
    }
    
    descMdArray = logDescMd(xmlin)

    curatorReportArray[metsFileName].update(descMdArray)
    
    # descMdTime = datetime.now()
    # print('descMdTime ' + str(descMdTime - startLoopTime))
    
    # THIS IS TAKING THE LONGEST
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
    
    # pathStatusTime = datetime.now()
    # print('pathStatusTime ' + str(pathStatusTime - descMdTime))
    
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
    
    # dirStatusTime = datetime.now()
    # print('dirStatusTime ' + str(dirStatusTime - pathStatusTime))
    
    pageArray, pageCounter = buildPageArray(xmlin)
    
    missingFilenameArray = buildMissingFilenameArray(xmlin)
    
    curatorReportArray[metsFileName]['Number of pages'] = pageCounter
    errorArray[metsFileName]['missing derivatives in structMap'] = {}
    
    for page in missingFilenameArray:
        errorArray[metsFileName]['missing derivatives in structMap'][page] = {}
        if missingFilenameArray[page] != {}:
            errorArray[metsFileName]['missing derivatives in structMap'][page]= missingFilenameArray[page]
        
        if errorArray[metsFileName]['missing derivatives in structMap'][page] == {}:
            errorArray[metsFileName]['missing derivatives in structMap'].pop(page)
            
    if errorArray[metsFileName]['missing derivatives in structMap'] == {}:
        errorArray[metsFileName].pop('missing derivatives in structMap')
        curatorReportArray[metsFileName]['Each page has PDF, JPG, and Alto'] = 'Yes'
    else:
        curatorReportArray[metsFileName]['Each page has PDF, JPG, and Alto'] = 'No'
    
    # derivTime = datetime.now()
    # print('derivTime ' + str(derivTime - dirStatusTime))
    
    techMdStatusArray = validateTechMd(xmlin)
    errorArray[metsFileName]['missing technical metadata'] = {}
    
    for jpgFile in techMdStatusArray:
        if techMdStatusArray[jpgFile]['techMD'] == False:
            errorArray[metsFileName]['missing technical metadata'][jpgFile] = techMdStatusArray[jpgFile]['JPG filename']
            
    if errorArray[metsFileName]['missing technical metadata'] == {}:
        errorArray[metsFileName].pop('missing technical metadata')
        curatorReportArray[metsFileName]['Technical metadata for each JPG'] = 'Yes'
    else:
        curatorReportArray[metsFileName]['Technical metadata for each JPG'] = 'No'
    
    # techTime = datetime.now()
    # print('techTime ' + str(techTime - derivTime))
    
    if errorArray[xmlin] != {}:
    
        with open('output.log', 'a') as f:
            f.write(json.dumps(errorArray, indent=4))
    
    writeToCuratorReport('report.csv',curatorReportArray)
    
# print('totalTime ' + str(datetime.now() - startTime))
