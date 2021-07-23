# SPDX-FileCopyrightText: 2021 German Aerospace Center (DLR)
# SPDX-License-Identifier: MIT

import json
from json.decoder import JSONDecodeError

import click
from utils.export_models import Project as Project_model
from utils.export_models import Namespace as Namespace_model
from utils.export_models import Language as Language_model
from py2neo import Graph
from utils.helpers import Corpus, transform_language_dict


class Exporter:
    """This class provides a method to export a corpus in another format.

    Methods:
        __init__(self, verbose, corpus, format_str, from_file=False, file="-")
        export(self, out)
    """

    def __init__(self, config, corpus, format_str, from_file=False, file="-"):
        """Exporter class constructor to initialize the object.
        :param config: Configuration for neo4j and verbose mode
        :param corpus: Input corpus, which will be exported
        :param from_file: Specifies, if the input corpus should be read from a file [default: ``False``]
        :param file: Path to input corpus
        """
        self.verbose = config.verbose
        self.format = format_str
        self.corpus = Corpus()
        self.graph = None
        self.neo4j_config = config.neo4j_config
        if from_file:
            with open(file, 'r') as f:
                try:
                    self.corpus.data = json.load(f)
                except JSONDecodeError:
                    click.echo("The input file does not contain valid JSON-data.")
        else:
            self.corpus = corpus

    def export(self, out):
        """This method exports the corpus to another format.
        :param out: Path to output file
        """
        with open(out, "w") as output:
            click.echo("Exporting...")
            if self.format.lower() == "json":
                if self.verbose:
                    click.echo("Output written to {}".format(out))
                json.dump(self.corpus.data, output, indent=4)
            elif self.format.lower() == "console":
                if self.verbose:
                    click.echo("Output will be printed to console.")
                for category in self.corpus.data:
                    for element in self.corpus.data[category]:
                        click.echo(str(element) + "\n")
            elif self.format.lower() == "neo4j":
                if self.verbose:
                    click.echo("Output will be exported to the Neo4J database.")
                self.graph = Graph(f"{self.neo4j_config['NEO4J']['protocol']}://"
                                   f"{self.neo4j_config['NEO4J']['hostname']}:"
                                   f"{self.neo4j_config['NEO4J']['port']}",
                                   user=self.neo4j_config['NEO4J']['user'],
                                   password=self.neo4j_config['NEO4J']['password'])
                self.export_to_neo4j()

    def export_to_neo4j(self):
        for project in self.corpus.data["Projects"]:
            project_node = Project_model.create(self.graph, project)
            namespace_node = Namespace_model.create(self.graph, project["namespace"])
            namespace_node.belongs_to.update(project_node)
            languages = transform_language_dict(project["languages"])
            for language in list(languages):
                language_node = Language_model.get_or_create(self.graph, language["name"], language)
                language_node.is_contained_in.update(project_node)
                self.graph.push(language_node)
            self.graph.push(namespace_node)

