from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdftypes import resolve1
from xmp import xmp_to_dict

fp = open('c:/Users/mihal/OneDrive/Documents/pyprj/pdf-metadata-master/example/docs/methods_of_web_philology.pdf', 'rb')
parser = PDFParser(fp)
doc = PDFDocument(parser)
parser.set_document(doc)

print(doc.info)        # The "Info" metadata

if 'Metadata' in doc.catalog:
    metadata = resolve1(doc.catalog['Metadata']).get_data()
    print(metadata)  # The raw XMP metadata
    print(xmp_to_dict(metadata))


"""
c:/Users/mihal/OneDrive/Documents/pyprj/pdf-metadata-master/example/docs/Haltermanpythonbook.pdf
c:/Users/mihal/OneDrive/Documents/pyprj/pdf-metadata-master/example/docs/methods_of_web_philology.pdf
c:/Users/mihal/OneDrive/Documents/pyprj/pdf-metadata-master/example/docs/pdf_wiki.pdf
"""
