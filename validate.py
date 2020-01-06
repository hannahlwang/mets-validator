#! /usr/bin/python

"""
mets-validator
---

A Python validation tool for METS packages.

For information on usage and dependencies, see:
github.com/hannahlwang/mets-validator

"""

from lxml import etree
from urllib.request import urlopen
import sys
import os
import json
import csv
import datetime

# validate XML against METS XSD schema
def validateXML(xmlschema, metsFile):

    # create report array
    validXmlArray = {
    'mets':metsFile,
    'value-ok':'',
    'io-ok':'',
    'well-formed':'',
    'valid':''
    }
        
    # open and read xml file
    with open(metsFile, 'r') as xml_file:
        xml_to_check = xml_file.read()

    # parse xml
    try:
        utf8_parser = etree.XMLParser(encoding='utf-8')
        doc = etree.fromstring(xml_to_check.encode('utf-8'), parser=utf8_parser)
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
def parseMETS(metsFile):
    # open and read xml file
    with open(metsFile, 'r') as xml_file:
        xml_to_check = xml_file.read()
    
    # parse xml and get root
    utf8_parser = etree.XMLParser(encoding='utf-8')
    root = etree.fromstring(xml_to_check.encode('utf-8'), parser=utf8_parser)
    
    # define XML namespaces
    ns = {
    'mets': 'http://www.loc.gov/METS/',
    'xlink': 'http://www.w3.org/1999/xlink',
    'mods': 'http://www.loc.gov/mods/v3'
    }
    
    return root, ns

# build list of file paths based on fileSec paths in METS
def buildFilePathList(metsFile):
    
    # open and parse METS xml, define XML namespaces
    root, ns = parseMETS(metsFile)
    
    # create list of file paths in the file section which will be used as input for validation
    filePathArray = {}
    
    # locate all the mets:FLocat tags and add the href attributes to the file path list
    for file in root.findall('./mets:fileSec/mets:fileGrp/mets:fileGrp/mets:file', ns):
        fileId = file.attrib['ID']
        filePath = file.find('./mets:FLocat',ns).attrib['{http://www.w3.org/1999/xlink}href']
        filePathArray[fileId] = filePath
    
    return filePathArray

# build list of actual file paths in the package (not including METS files) and a separate list of any METS files
def getMetsFiles(metsPackage):
    
    rootDir = os.path.dirname(metsPackage)

    dirList = []

    for root, dirs, files in os.walk(rootDir):
        for name in files:
            dirList.append(os.path.join(root,name).replace('\\','/').replace(rootDir,'.'))
    
    metsFileList = [path for path in dirList if '_mets.xml' in path]

    
    
    
    return dirList, metsFileList

def dirPathList(metsFile):
    
    dirList, metsFileList = getMetsFiles(metsPackage)
    
    
    pathList = [path for path in dirList if '_mets.xml' not in path]

# build arrays that give boolean status of files in package vs files in METS pathlist
def statusArrays(metsFile):

    filePathArray = buildFilePathList(metsFile)
    
    pathList, metsFileList = buildDirList(metsFile)
    
    # compare each file in pathlist against the contents of the system
    pathStatusArray = {}
    
    for filePath in filePathArray.values():
        pathStatusArray[filePath] = filePath in pathList
    
    # compare each file in system list against the METS pathlist
    dirStatusArray = {}
    
    for filePath in pathList:
        if filePath in filePathArray.values():
            dirStatusArray[filePath] = True
        else:
            dirStatusArray[filePath] = False
    
    return pathStatusArray, dirStatusArray

# create array for storing page IDs and fileIDs for each pdf, jpg, and alto file in scructMap - this will be used to verify whether each file has all 3 derivatives. Also count number of pages in structMap, to be included in final report.
def buildPageArray(metsFile):
    # open and parse METS xml, define XML namespaces
    root, ns = parseMETS(metsFile)
    
    pageArray = {}
    
    pageCounter = 0
    
    filePathArray = buildFilePathList(metsFile)
    
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
def buildMissingFilenameArray(metsFile):
    
    pageArray, pageCounter = buildPageArray(metsFile)
    
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
def validateTechMd(metsFile):
    
    # open and parse METS xml, define XML namespaces
    root, ns = parseMETS(metsFile)
    
    filePathArray = buildFilePathList(metsFile)
    
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
def logDescMd(metsFile):

    # open and parse METS xml, define XML namespaces
    root, ns = parseMETS(metsFile)
    
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
            
def writeToCuratorReport(reportname,reportarray):
    fields = ['METS filename','Valid METS','/mets:metsHdr/mets:agent[1]/mets:name', '/mets:metsHdr/mets:agent[2]/mets:name', '/mets:metsHdr/mets:agent[3]/mets:name', '/mods:mods/mods:titleInfo/mods:title', '/mods:mods/mods:typeOfResource', '/mods:mods/mods:genre', '/mods:mods/mods:originInfo/mods:dateIssued', '/mods:mods/mods:originInfo/mods:edition', '/mods:mods/mods:language/mods:languageTerm', '/mods:mods/mods:identifier[1]', '/mods:mods/mods:identifier[2]', '/mods:mods/mods:identifier[3]', '/mods:mods/mods:recordInfo/mods:recordContentSource', 'Number of pages', 'All files from METS present in package', 'All files in package present in METS', 'Each page has PDF, JPG, and Alto', 'Technical metadata for each JPG']
    
    # remove any empty elements (potentially caused by newlines in mets file)
    for metsFile in reportarray:
        for key in list(reportarray[metsFile]):
            if str(reportarray[metsFile][key]).strip() == '':
                reportarray[metsFile].pop(key)
    
    with open(reportname, 'a') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        for key,val in sorted(reportarray.items()):
            row = {'METS filename':key}
            row.update(val)
            w.writerow(row)

currentTime = datetime.datetime.now().strftime('%Y%m%dT%H%M%S')
    
curatorReport = os.path.join(sys.argv[1],currentTime+'_report.csv')
outputLog = os.path.join(sys.argv[1], currentTime+'_output.log')

fields = ['METS filename','Valid METS','/mets:metsHdr/mets:agent[1]/mets:name', '/mets:metsHdr/mets:agent[2]/mets:name', '/mets:metsHdr/mets:agent[3]/mets:name', '/mods:mods/mods:titleInfo/mods:title', '/mods:mods/mods:typeOfResource', '/mods:mods/mods:genre', '/mods:mods/mods:originInfo/mods:dateIssued', '/mods:mods/mods:originInfo/mods:edition', '/mods:mods/mods:language/mods:languageTerm', '/mods:mods/mods:identifier[1]', '/mods:mods/mods:identifier[2]', '/mods:mods/mods:identifier[3]', '/mods:mods/mods:recordInfo/mods:recordContentSource', 'Number of pages', 'All files from METS present in package', 'All files in package present in METS', 'Each page has PDF, JPG, and Alto', 'Technical metadata for each JPG']

with open(curatorReport, 'w') as f:
    w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
    w.writeheader()

open(outputLog, 'w')

# open and read schema file
xsdin = 'http://www.loc.gov/standards/mets/mets.xsd'
with urlopen(xsdin) as schema_file:
    schema_to_check = schema_file.read()
    
#parse schema and load into memory as xmlschema_doc
xmlschema_doc = etree.fromstring(schema_to_check)
xmlschema = etree.XMLSchema(xmlschema_doc)

pathList, metsFileList = buildDirList(sys.argv[1])

# for each mets file found on disk, execute all functions and output to [datetime]_report.csv and [datetime]_output.log
for metsFile in metsFileList:   
    
    errorArray = {}
    curatorReportArray = {}
    
    validXmlArray = validateXML(xmlschema,metsFile)
    metsFileName = validXmlArray['mets']
    
    errorArray[metsFileName] = {}
    curatorReportArray[metsFileName] = {}

    if validXmlArray['value-ok'] == False or validXmlArray['io-ok'] == False or validXmlArray['well-formed'] == False or  validXmlArray['valid'] == False:
        
        errorArray[metsFileName] = {
            'validation errors' : validXmlArray
        }
        
        with open(outputLog, 'a') as f:
            f.write(json.dumps(errorArray, indent=4))
            
        curatorReportArray[metsFileName] = {
            'Valid METS' : 'No'
        }
        
        writeToCuratorReport(curatorReport,curatorReportArray)
        
        continue
        
    curatorReportArray[metsFileName] = {
        'Valid METS' : 'Yes'
    }
    
    descMdArray = logDescMd(metsFile)

    curatorReportArray[metsFileName].update(descMdArray)

    pathStatusArray, dirStatusArray = statusArrays(metsFile)
    errorArray[metsFileName]['files in mets not in package'] = []
    
    for path in pathStatusArray:
        if pathStatusArray[path] == False:
            errorArray[metsFileName]['files in mets not in package'].append(path)
    
    if errorArray[metsFileName]['files in mets not in package'] == []:
        errorArray[metsFileName].pop('files in mets not in package')
        curatorReportArray[metsFileName]['All files from METS present in package'] = 'Yes'
    else:
        curatorReportArray[metsFileName]['All files from METS present in package'] = 'No'
    
    errorArray[metsFileName]['files in package not in mets'] = []
    
    for path in dirStatusArray:
        if dirStatusArray[path] == False:
            errorArray[metsFileName]['files in package not in mets'].append(path)
            
    if errorArray[metsFileName]['files in package not in mets'] == []:
        errorArray[metsFileName].pop('files in package not in mets')
        curatorReportArray[metsFileName]['All files in package present in METS'] = 'Yes'
    else:
        curatorReportArray[metsFileName]['All files in package present in METS'] = 'No'
    
    pageArray, pageCounter = buildPageArray(metsFile)
    
    missingFilenameArray = buildMissingFilenameArray(metsFile)
    
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
    
    techMdStatusArray = validateTechMd(metsFile)
    errorArray[metsFileName]['missing technical metadata'] = {}
    
    for jpgFile in techMdStatusArray:
        if techMdStatusArray[jpgFile]['techMD'] == False:
            errorArray[metsFileName]['missing technical metadata'][jpgFile] = techMdStatusArray[jpgFile]['JPG filename']
            
    if errorArray[metsFileName]['missing technical metadata'] == {}:
        errorArray[metsFileName].pop('missing technical metadata')
        curatorReportArray[metsFileName]['Technical metadata for each JPG'] = 'Yes'
    else:
        curatorReportArray[metsFileName]['Technical metadata for each JPG'] = 'No'
    
    if errorArray[metsFile] != {}:
    
        with open(outputLog, 'a') as f:
            f.write(json.dumps(errorArray, indent=4))
    
    writeToCuratorReport(curatorReport,curatorReportArray)