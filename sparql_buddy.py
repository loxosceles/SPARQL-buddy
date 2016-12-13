#!/usr/bin/env python

import rdflib, json, csv, sys, traceback, fnmatch
from SPARQLWrapper import SPARQLWrapper, JSON
from os import walk, listdir


default_url = "http://dbpedia.org/sparql"
default_prefix_file = "./prefixes.csv"
default_query_path = "./queries/"

class SQuery:
    
    def __init__(self, url=default_url, prefixes=default_prefix_file, dqp=default_query_path):
        self.url = url
        self.prefix_file = prefixes
        self.dqp = dqp
        self.qres = dict() 
        self.g = SPARQLWrapper(self.url)
        self.prefixes_dict = dict() 
        self.generate_prefix_dict(self.prefix_file)

    def generate_prefix_dict(self, pf):
        with open(pf, mode='r') as infile:
            tmp = csv.reader(infile)
            self.prefixes_dict = {rows[0]:rows[1] for rows in tmp}

    def set_url(self, url):
        self.url = url
        self.g = SPARQLWrapper(self.url)

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


    def run_query(self, inpt):
        q = self.compose_query(inpt)
        self.g.setReturnFormat(JSON)
        self.g.setQuery(q)
        self.qres = self.g.query().convert()
        self.print_query()

    def print_query(self):
        #print(json.dumps(self.qres["results"]["bindings"], indent=4, sort_keys=True))
        print(json.dumps(self.qres, indent=4, sort_keys=True))

    def print_raw_query(self):
        print(self.qres)

    def concat_prefix_string(self, prefix):
        return "PREFIX " + prefix + ": " + self.prefixes_dict[prefix] + " "


def list_queries(path=default_query_path):
    return dict(enumerate([f for f in listdir(path) 
        if not fnmatch.filter(f, '.*')]))

    
sq = SQuery()
