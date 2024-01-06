from lxml import etree
import sys



def add_chaps(filepath):
    tei_ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
    out_path = filepath.replace(".xml", ".numbered.xml")

    tree = etree.parse(filepath)
    books = tree.xpath("//tei:div[@type='livre'][@n]", namespaces=tei_ns)
    for book_n, book in enumerate(books):
        parts = book.xpath("descendant::tei:div[@type='partie'][@n]", namespaces=tei_ns)
        for part_n, part in enumerate(parts):
            chapters = part.xpath("descendant::tei:div[@type='chapitre']", namespaces=tei_ns)
            for index, chapitre in enumerate(chapters):
                chapitre.set("n", str(index + 1))
                chapitre.set("{http://www.w3.org/XML/1998/namespace}id", f"{filepath.split('.xml')[0].split('/')[-1]}_{book_n + 1}_{part_n + 1}_{index + 1}")

    with open(out_path, "w") as output_file:
        output_file.write(etree.tostring(tree, encoding="utf8").decode("utf8"))



if __name__ == '__main__':
    filepath = sys.argv[1]
    add_chaps(filepath)