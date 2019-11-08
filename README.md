# mets-validator

## Requirements

* [Python 3](https://www.python.org/download/releases/3.0/)
* [lxml](https://lxml.de/installation.html)

## Usage

`python validate.py "[root directory path]"`

Directory separator in `[root directory path]` can be either `/` or `\`. Double quotes must be used around `[root directory path]`.

`report.csv` and `output.log` will be created in same location as `validate.py` script.

## csv report output

For each issue, include line in report.csv with the following fields:

* METS filename
* Valid METS (Yes/No)
* /mets:metsHdr/mets:agent[1]/mets:name
* /mets:metsHdr/mets:agent[2]/mets:name
* /mets:metsHdr/mets:agent[3]/mets:name
* /mods:mods/mods:titleInfo/mods:title
* /mods:mods/mods:typeOfResource
* /mods:mods/mods:genre
* /mods:mods/mods:originInfo/mods:dateIssued
* /mods:mods/mods:originInfo/mods:edition
* /mods:mods/mods:language/mods:languageTerm
* /mods:mods/mods:identifier[1]
* /mods:mods/mods:identifier[2]
* /mods:mods/mods:identifier[3]
* /mods:mods/mods:recordInfo/mods:recordContentSource
* Number of pages
* All files from METS present in package (Yes/No)
* All files in package present in METS (Yes/No)
* Each page has PDF, JPG, and Alto	(Yes/No)
* Technical metadata for each JPG (Yes/No)

## log ouput

Output is only created if errors are raised. For each xml file that raises an error, log output may include: 

```
{
    mets-filename.xml: {
        "validation errors": {
            "mets": "mets-filename.xml",
            "value-ok": "",
            "value-error": "",
            "io-ok": "",
            "io-error": "",
            "well-formed": "",
            "syntax-error": "",
            "valid": "",
            "validation-error": "",
        },
        "files in mets not in package": [
            filename-array
        ],
        
        "files in package not in mets": [
            filename-array
        ],
        "missing derivatives in structMap": {
            pageID: {
                fileID: filename
            }
        },
        "missing technical metadata": {
            fileID: filename
        }
    }
}
```

## performance testing

Requires: snakeviz (`pip install snakeviz`)

```
python -m cProfile -o out.dat validate.py "[root directory path]"
snakeviz out.dat
```