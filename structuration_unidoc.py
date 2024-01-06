import os
import subprocess
from itertools import groupby
from operator import itemgetter
from tkinter import *
from lxml import etree
import tqdm
import Levenshtein


class StructureChecker:
    def __init__(self):
        self.tei_ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
        self.tei_namespace_url = 'http://www.tei-c.org/ns/1.0'
        self.tei_namespace = '{%s}' % self.tei_namespace_url
        self.filepath = sys.argv[1]
        self.root = etree.parse(self.filepath)

    def structure(self):
        self.produce_headings_and_pars()
        self.save_tree()

    def save_tree(self):
        output_path = self.filepath.replace(".xml", ".structured.xml")
        print(f"Writing file to {output_path}")
        with open(output_path, "w") as output_file:
            output_file.write(etree.tostring(self.root, pretty_print=True, encoding='utf8').decode('utf8'))

    def produce_headings_and_pars(self):
        print("Starting structuration")

        non_lines_nodes = self.root.xpath("//tei:text/tei:body/tei:div/descendant::node()[not(self::text()) and not("
                                          "self::tei:lb)]", namespaces=self.tei_ns)
        nodes_anchors = []
        for node in non_lines_nodes:
            try:
                anchor_lb = node.xpath("following-sibling::tei:lb[1]/@xml:id", namespaces=self.tei_ns)[0]
            except IndexError:
                anchor_lb = node.xpath("preceding-sibling::tei:lb[1]/@xml:id", namespaces=self.tei_ns)[0]
            nodes_anchors.append([node, anchor_lb])
        all_lines = self.root.xpath("//tei:lb[not(parent::tei:fw)]", namespaces=self.tei_ns)
        livre = self.root.xpath("//tei:text/tei:body/tei:div", namespaces=self.tei_ns)[0]
        livre.set("type", "livre")
        all_nodes = livre.xpath("node()", namespaces=self.tei_ns)
        partie = etree.Element("{" + self.tei_namespace_url + "}" + "div")
        partie.set("type", "partie")
        livre.append(partie)
        for index, node in enumerate(all_nodes):
            element = all_nodes[index]
            try:
                partie.append(element)
            except TypeError:
                all_nodes[index - 1].tail = element
            except ValueError:
                continue
        all_nodes_and_id = [(node, node.xpath("@n") if type(node) != etree._ElementUnicodeResult else []) for node in
                            all_nodes]
        all_rubricated_lines = list()
        gloss_headings = list()
        for index, line in enumerate(all_lines):
            try:
                line.xpath('@rend')[0] == 'rubric'
                # On calcule une distance entre la chaîne 'glosa' et la ligne rubriquée
                # Cela n'étant pas suffisant (ça matcherait aussi avec les lignes rubriquées courtes)
                # On va comparer les caractères des 2 chaînes avec une intersection de sets.
                # Il faut que les 2 chaînes partagent au moins 3 caractères en commun.
                if Levenshtein.distance(line.tail, 'glosa') < 4 and len(set(line.tail).intersection(set('glosa'))) >= 3:
                    print("Found gloss")
                    print(line.tail)
                    gloss_headings.append(index)
                else:
                    all_rubricated_lines.append(index)
            except IndexError:
                pass

        # https://stackoverflow.com/a/2154437
        ranges = []
        for k, g in groupby(enumerate(all_rubricated_lines), lambda x: x[0] - x[1]):
            group = (map(itemgetter(1), g))
            group = list(map(int, group))
            ranges.append([group[0], group[-1] + 1])

        divs_dictionnary = dict()
        for index, (min_range, max_range) in enumerate(ranges):
            # On rétablit la structure du texte
            try:
                range = (min_range, ranges[index + 1][0] - 1)
            except IndexError:
                range = (min_range, len(all_lines) - 1)
            info = {"headings": (min_range, max_range),
                    "range": range}
            for gloss_heading in gloss_headings:
                if max_range < gloss_heading < ranges[index + 1][0]:
                    info["translation"] = (max_range + 1, gloss_heading - 1)
                    info["gloss"] = (gloss_heading, range[1])
                    info["gloss_heading"] = (gloss_heading,)
                else:
                    info["translation"] = (max_range + 1, range[1])

            divs_dictionnary[f"chap_{index + 1}"] = info

        for chapter, values in tqdm.tqdm(divs_dictionnary.items()):
            # On va du plus précis au plus général
            heading_to_insert = etree.Element("{" + self.tei_namespace_url + "}" + "head")
            division_to_insert = etree.Element("{" + self.tei_namespace_url + "}" + "div")
            division_to_insert.set("type", "chapitre")
            corresponding_heading_lines = all_lines[values['headings'][0]:values['headings'][1]]
            for line in corresponding_heading_lines:
                heading_to_insert.append(line)

            translation_to_insert = etree.Element("{" + self.tei_namespace_url + "}" + "div")
            translation_to_insert.set("type", "traduction")
            translation_p_to_insert = etree.Element("{" + self.tei_namespace_url + "}" + "p")
            corresponding_translation_lines = all_lines[values['translation'][0] - 1:values['translation'][1] + 1]
            for line in corresponding_translation_lines:
                translation_p_to_insert.append(line)

            translation_to_insert.append(translation_p_to_insert)
            partie.append(division_to_insert)
            division_to_insert.append(heading_to_insert)
            division_to_insert.append(translation_to_insert)

            if values.__contains__('gloss'):
                gloss_to_insert = etree.Element("{" + self.tei_namespace_url + "}" + "div")
                gloss_to_insert.set("type", "glose")
                gloss_heading_to_insert = etree.Element("{" + self.tei_namespace_url + "}" + "head")
                corresponding_gloss_heading_lines = all_lines[values['gloss_heading'][0]]
                gloss_heading_to_insert.append(corresponding_gloss_heading_lines)
                gloss_p_to_insert = etree.Element("{" + self.tei_namespace_url + "}" + "p")
                corresponding_gloss_lines = all_lines[values['gloss_heading'][0] + 1:values['gloss'][1] + 1]
                for line in corresponding_gloss_lines:
                    gloss_p_to_insert.append(line)
                gloss_to_insert.append(gloss_heading_to_insert)
                gloss_to_insert.append(gloss_p_to_insert)
                division_to_insert.append(gloss_to_insert)
        # On réinjecte les noeuds laissés pour compte:
        print("Nodes reinjection")

        all_lines = self.root.xpath("//tei:lb", namespaces=self.tei_ns)
        all_ids = self.root.xpath("//tei:lb/@xml:id", namespaces=self.tei_ns)
        all_lines_and_ids = {id: line for line, id in zip(all_lines, all_ids)}
        for node, anchor in nodes_anchors:
            corresponding_lb = all_lines_and_ids[anchor]
            corresponding_lb.addprevious(node)

        print("Done!")


# Copy to the clipboard


if __name__ == '__main__':
    structurer = StructureChecker()
    structurer.structure()
