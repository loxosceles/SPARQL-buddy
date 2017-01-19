#!/usr/bin/env python

import rdflib, json, csv, sys, traceback, fnmatch
from SPARQLWrapper import SPARQLWrapper, JSON
from os import walk, listdir
import itertools

default_url = "http://dbpedia.org/sparql"
default_prefix_file = "./prefixes.csv"
default_query_path = "./queries/"


class SQObject:
    #newid = next(itertools.count())
    def __init__(self):
        self.id = id(self) 
        self.query = "" 
        self.response = dict()

    @property
    def query(self): 
        return self._query

    @query.setter
    def query(self, value):
        self._query = value

    @property
    def response(self): 
        return self._response

    @response.setter
    def response(self, value):
        self._response = value

    def print_query(self):
        print(self._query)

    def print_response(self):
        print(json.dumps(self._response, indent=4, sort_keys=True))

    def print_raw_response(self):
        print(self._response)

    def filter_types(self):
        for i in self.response['results']['bindings']:
            print(i['type']['value'])


class SQuery:
    """
    Objects of this class comprise a particular query environment, so that every
    instance will query with different query parameters:
        * url of SPARQL endpoint
        * prefix file where prefix abreviations are defined, can be used to group
          prefixes since not every query needs all of them
        * query path, path where queries can be stored
    If no parameters are given when instantiated, default values will be used.
    """
    
    def __init__(self, url=default_url, prefixes=default_prefix_file, dqp=default_query_path):
        self.url = url
        self.prefix_file = prefixes
        self.dqp = dqp                              # default query path
        #self.qres = dict() 
        self.g = SPARQLWrapper(self.url)
        self.prefixes_dict = dict() 
        self.generate_prefix_dict(self.prefix_file)
        self.query_list = []                        # list of recent query objects

    def run_query(self, inpt, r=""):
        """
        runs a query
        params: inpt, can be file or string
                r, 'raw' prints raw JSON format
        """
        obj = SQObject()
        obj.query = self.compose_query(inpt)
        self.g.setReturnFormat(JSON)
        self.g.setQuery(obj.query)
        obj.response = self.g.query().convert()
        self.query_list.append(obj)
        if r is "raw":
            obj.print_raw_response()
        else:
            obj.print_response()

    def compose_query(self, q):
        prefix_list = []
        prefix_sting = ""
        query = ""

        try:
            prefix_list = q.split("\n", 1)[0].split()
            query = q.split("\n", 1)[1] 
        except (IndexError, AttributeError) as e:
            try:
                if type(q) is int: q = list_queries()[q]

                q_relpath = self.dqp + q

                with open(q_relpath) as f:
                    prefix_list = f.readline().strip().split()
                    query = f.read()
            except FileNotFoundError:
                    sys.exit('File name wrong?')

        for item in prefix_list:
            prefix_sting + self.concat_prefix_string(item)
        return prefix_sting + query

    def keyword_search(self, kw):
        kwq = """
                SELECT DISTINCT ?searchterm ?type
                    WHERE {
                       ?searchterm rdf:type ?o  ;
                       #foaf:name ?name
                       rdfs:label ?name
                        FILTER REGEX(?name, '%(keyword)s') .
                        OPTIONAL {
                            ?searchterm rdf:type ?type
                            #FILTER REGEX(?type, "http://xmlns.com/foaf/0.1/Person") .
                            #FILTER REGEX(?type, "http://xmlns.com/foaf/0.1/Agent") .
                        } 
                    } LIMIT 10
                """ % {'keyword':kw}
        self.run_query(kwq)

    def clear_query_list(self):
        self.query_list.clear()

    def print_query_list(self):
        for o in self.query_list:
            print(o)

    def generate_prefix_dict(self, pf):
        with open(pf, mode='r') as infile:
            tmp = csv.reader(infile)
            try:
                self.prefixes_dict = {rows[0]:rows[1] for rows in tmp}
            except IndexError as e:
                sys.exit("Prefixes file should not contain blank lines")

    def set_url(self, url):
        self.url = url
        self.g = SPARQLWrapper(self.url)

    def concat_prefix_string(self, prefix):
        return "PREFIX " + prefix + ": " + self.prefixes_dict[prefix] + " "

    def print_prefixes():
        """
        TODO
        """
        pass


def list_queries(path=default_query_path):
    return dict(enumerate([f for f in listdir(path) 
        if not fnmatch.filter(f, '.*')]))

sq = SQuery()
